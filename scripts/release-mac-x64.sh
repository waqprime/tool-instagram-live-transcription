#!/bin/bash
# Intel Mac (x64) 手動ビルド & リリースアップロード
# PostToolUse hook から呼び出される
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# タグ名を引数から取得
TAG="$1"
if [ -z "$TAG" ]; then
  echo '{"stopReason": "タグ名が指定されていません"}'
  exit 1
fi

VERSION="${TAG#v}"

# .envから認証情報を読み込み
if [ -f "$REPO_ROOT/.env" ]; then
  # コメント行を除外して読み込み
  export APPLE_ID=$(grep -m1 'Apple ID' "$REPO_ROOT/.env" | sed 's/.*: *//')
  export APPLE_APP_SPECIFIC_PASSWORD=$(grep -m1 'パスワード' "$REPO_ROOT/.env" | sed 's/.*: *//')
  export APPLE_TEAM_ID=$(grep -m1 'Team ID' "$REPO_ROOT/.env" | sed 's/.*: *//')
fi

if [ -z "$APPLE_ID" ] || [ -z "$APPLE_APP_SPECIFIC_PASSWORD" ] || [ -z "$APPLE_TEAM_ID" ]; then
  echo '{"stopReason": "Apple認証情報が.envに見つかりません"}'
  exit 1
fi

echo "=== Intel Mac (x64) ビルド開始: $TAG ==="

# ビルド
cd electron-app
npm version "$VERSION" --no-git-tag-version --allow-same-version 2>/dev/null || true

echo "=== ビルド実行中... ==="
if ! npm run build:mac-x64 2>&1; then
  echo "WARNING: npm run build:mac-x64 が非ゼロで終了（DMG作成失敗の可能性）"
  echo "ZIPが生成されていれば続行します"
fi

# ZIPが生成されたか確認
ZIP="dist/TranscriptionTool-${VERSION}-x64.zip"
DMG="dist/TranscriptionTool-${VERSION}-x64.dmg"

if [ ! -f "$ZIP" ]; then
  echo "ERROR: ZIPが生成されませんでした"
  exit 1
fi

# DMGが生成されなかった場合（hdiutil日本語ボリューム名バグ）、手動作成
if [ ! -f "$DMG" ]; then
  echo "DMG未生成 - ASCIIボリューム名で手動作成..."
  APP_PATH="dist/mac/文字起こしツール.app"
  if [ -d "$APP_PATH" ]; then
    # 権限エラー回避: tmpにコピーしてからDMG作成
    TMP_DMG_DIR=$(mktemp -d)
    cp -R "$APP_PATH" "$TMP_DMG_DIR/TranscriptionTool.app"
    # set -e で即死してZIPアップロードまで消えるのを防ぐため、if文で保護し
    # 失敗時は警告のみでDMGなしで続行する（TMP_DMG_DIRの掃除は成否に関わらず実行）
    if hdiutil create -srcfolder "$TMP_DMG_DIR" \
      -volname "TranscriptionTool" -anyowners -nospotlight \
      -format UDZO -fs APFS "$DMG"; then
      echo "DMG手動作成完了"
    else
      echo "WARNING: hdiutilによるDMG作成に失敗。DMGなしで続行します"
    fi
    rm -rf "$TMP_DMG_DIR"
  else
    echo "WARNING: .appが見つかりません。DMGはスキップ"
  fi
fi

# CIのreleaseジョブ完了を待機してからアップロードする。
# release.yml は「既存リリースを削除→再作成」するため（electron-builder直publishとの
# 422競合対策）、CI完了前にx64をアップロードすると削除に巻き込まれて消える。
# CIがリリースを作り終えた後に --clobber で足せば、x64成果物が安全に共存できる。
echo "=== CI(Build and Release)の完了を待機: $TAG ==="
MAX_WAIT=2400   # 最大40分
WAITED=0
# 新しい実行がGitHubに登録されるまで少し待つ（古い同名タグ実行への誤ロック回避）
sleep 60
WAITED=$((WAITED+60))
while true; do
  STATUS=$(gh run list --workflow="Build and Release" --limit 20 \
    --json headBranch,status --jq "[.[] | select(.headBranch==\"$TAG\")][0].status" 2>/dev/null || echo "")
  if [ "$STATUS" = "completed" ]; then
    CONCLUSION=$(gh run list --workflow="Build and Release" --limit 20 \
      --json headBranch,conclusion --jq "[.[] | select(.headBranch==\"$TAG\")][0].conclusion" 2>/dev/null || echo "")
    echo "CIワークフロー完了 (conclusion=$CONCLUSION)"
    break
  fi
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "WARNING: CI完了待ちがタイムアウト($MAX_WAIT秒)。リリース存在を確認して続行します"
    break
  fi
  echo "CI実行中... (status=${STATUS:-未登録}, ${WAITED}秒経過)"
  sleep 30
  WAITED=$((WAITED+30))
done

# リリース本体が作成済みになるまで念のため確認（最大2.5分）
for i in $(seq 1 10); do
  if gh release view "$TAG" >/dev/null 2>&1; then
    echo "リリース確認OK: $TAG"
    break
  fi
  echo "リリース未作成、待機中... ($i/10)"
  sleep 15
done

# リリースにアップロード
echo "=== リリースにアップロード: $TAG ==="
UPLOAD_FILES=""
[ -f "$ZIP" ] && UPLOAD_FILES="$UPLOAD_FILES $ZIP"
[ -f "$DMG" ] && UPLOAD_FILES="$UPLOAD_FILES $DMG"

if [ -n "$UPLOAD_FILES" ]; then
  gh release upload "$TAG" $UPLOAD_FILES --clobber
  echo "アップロード完了"
fi

cd "$REPO_ROOT"

# 成果物をJSON出力
echo "{\"systemMessage\": \"Intel Mac (x64) ビルド&アップロード完了: $TAG\"}"
