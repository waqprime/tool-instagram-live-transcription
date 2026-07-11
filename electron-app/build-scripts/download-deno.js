const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const unzipper = require('unzipper');

// yt-dlp 2026.7.4+ のEJSソルバーは deno >= 2.3.0 必須（DenoJsRuntime.MIN_SUPPORTED_VERSION）。
// 古いdenoだとn-challenge解決が "no solutions" で失敗し「Requested format is not available」になる。
const DENO_VERSION = '2.9.2';
const ROOT_DIR = path.join(__dirname, '..', '..');
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const DENO_DIR = path.join(RESOURCES_DIR, 'deno');
const HASH_FILE = path.join(DENO_DIR, '.deno_hash');

// Known good hashes (verified binaries).
// When a new version is released, run the build once to get the hash,
// verify the binary manually, then add the hash here.
const KNOWN_HASHES = {
  'win32-x64': 'a5270c2bb75a2ec12fef53185730327267d9e9fe6be6a962c5d1d5a050f93c88',
  'darwin-arm64': '218ab752ae8f64f0a7822af710886488f15169fdae153a3aada4861f9635b266',
  'darwin-x64': '201651c6e72bd0df2dbe994b4f8ca0f935631e08c27290a3a92342e02ad0e865',
  'linux-x64': '5bc8a7a4a628360b391ddeac2efac7dec9e670b33156d831bf1e899070655173',
};

// Platform-specific download URLs (GitHub releases)
function getDenoUrl(platform, arch) {
  const base = `https://github.com/denoland/deno/releases/download/v${DENO_VERSION}`;
  const targets = {
    'win32-x64': `${base}/deno-x86_64-pc-windows-msvc.zip`,
    'darwin-arm64': `${base}/deno-aarch64-apple-darwin.zip`,
    'darwin-x64': `${base}/deno-x86_64-apple-darwin.zip`,
    'linux-x64': `${base}/deno-x86_64-unknown-linux-gnu.zip`,
  };
  return targets[`${platform}-${arch}`];
}

function computeFileHash(filePath) {
  const data = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(data).digest('hex');
}

function verifyHash(filePath, expectedHash) {
  const actualHash = computeFileHash(filePath);
  if (actualHash !== expectedHash) {
    throw new Error(
      `Hash mismatch for ${path.basename(filePath)}!\n` +
      `  Expected: ${expectedHash}\n` +
      `  Got:      ${actualHash}\n` +
      `The downloaded file may have been tampered with.`
    );
  }
  console.log(`  Hash verified: ${actualHash.substring(0, 16)}...`);
}

async function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    console.log(`Downloading from: ${url}`);

    const download = (downloadUrl, redirectCount = 0) => {
      if (redirectCount > 10) {
        reject(new Error('Too many redirects'));
        return;
      }

      const parsedUrl = new URL(downloadUrl);
      const protocol = parsedUrl.protocol === 'https:' ? https : require('http');

      protocol.get(downloadUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (response) => {
        if ([301, 302, 303, 307, 308].includes(response.statusCode)) {
          response.resume();
          const redirectLocation = response.headers.location;
          const redirectUrl = redirectLocation.startsWith('http')
            ? redirectLocation
            : new URL(redirectLocation, downloadUrl).href;
          download(redirectUrl, redirectCount + 1);
          return;
        }

        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode}: ${response.statusMessage}`));
          return;
        }

        const file = fs.createWriteStream(destPath);
        response.pipe(file);

        file.on('finish', () => {
          file.close(() => {
            console.log(`Downloaded to: ${destPath}`);
            resolve();
          });
        });

        file.on('error', (err) => {
          fs.unlink(destPath, () => {});
          reject(err);
        });
      }).on('error', (err) => {
        fs.unlink(destPath, () => {});
        reject(err);
      });
    };

    download(url);
  });
}

async function downloadDeno(platform, arch) {
  if (!fs.existsSync(RESOURCES_DIR)) {
    fs.mkdirSync(RESOURCES_DIR, { recursive: true });
  }
  if (!fs.existsSync(DENO_DIR)) {
    fs.mkdirSync(DENO_DIR, { recursive: true });
  }

  const binaryName = platform === 'win32' ? 'deno.exe' : 'deno';
  const denoBinaryPath = path.join(DENO_DIR, binaryName);

  const knownKey = `${platform}-${arch}`;
  const knownHash = KNOWN_HASHES[knownKey];

  // Check existing binary
  if (fs.existsSync(denoBinaryPath)) {
    const expectedHash = knownHash
      || (fs.existsSync(HASH_FILE) ? fs.readFileSync(HASH_FILE, 'utf-8').trim() : null);

    if (expectedHash) {
      try {
        verifyHash(denoBinaryPath, expectedHash);
        console.log('  deno binary verified, skipping download');
        return;
      } catch (e) {
        console.warn(`  ${e.message}`);
        console.log('Re-downloading deno...');
        fs.unlinkSync(denoBinaryPath);
        if (fs.existsSync(HASH_FILE)) fs.unlinkSync(HASH_FILE);
      }
    } else {
      console.warn('  No known hash for existing deno binary. Re-downloading...');
      fs.unlinkSync(denoBinaryPath);
    }
  }

  const downloadUrl = getDenoUrl(platform, arch);
  if (!downloadUrl) {
    throw new Error(`Unsupported platform/arch: ${platform}-${arch}`);
  }

  const archivePath = path.join(RESOURCES_DIR, 'deno.zip');

  console.log(`Downloading deno v${DENO_VERSION} for ${platform} ${arch}...`);
  await downloadFile(downloadUrl, archivePath);

  // Extract zip
  console.log('Extracting deno...');
  await fs.createReadStream(archivePath)
    .pipe(unzipper.Extract({ path: DENO_DIR }))
    .promise();

  if (!fs.existsSync(denoBinaryPath)) {
    throw new Error(`deno binary not found after extraction: ${denoBinaryPath}`);
  }

  // Make executable on Unix
  if (platform !== 'win32') {
    fs.chmodSync(denoBinaryPath, 0o755);
  }

  // Hash verification
  const hash = computeFileHash(denoBinaryPath);
  if (knownHash) {
    if (hash !== knownHash) {
      throw new Error(
        `deno hash mismatch for ${platform}-${arch}!\n` +
        `  Expected: ${knownHash}\n` +
        `  Got:      ${hash}\n` +
        `The downloaded binary may have been tampered with.`
      );
    }
    console.log('  deno hash verified against known good hash');
  } else {
    // No known hash - delete the binary and abort build (same policy as ffmpeg).
    fs.unlinkSync(denoBinaryPath);
    console.error(`\n${'!'.repeat(60)}`);
    console.error(`deno downloaded for ${platform}-${arch} but no known hash registered.`);
    console.error(`Downloaded binary hash: '${hash}'`);
    console.error(`\nTo proceed, verify this binary is legitimate, then add to KNOWN_HASHES in download-deno.js:`);
    console.error(`  '${knownKey}': '${hash}'`);
    console.error(`${'!'.repeat(60)}\n`);
    throw new Error(
      `Build aborted: deno hash for ${platform}-${arch} is not in KNOWN_HASHES.\n` +
      `Add the hash above after manual verification.`
    );
  }

  fs.writeFileSync(HASH_FILE, hash);
  console.log(`  deno hash recorded: ${hash.substring(0, 16)}...`);

  // Cleanup archive
  fs.unlinkSync(archivePath);

  const sizeMB = (fs.statSync(denoBinaryPath).size / 1024 / 1024).toFixed(2);
  console.log(`  deno binary ready (${sizeMB} MB)`);
}

// requirements.txt は yt-dlp をバージョン固定していないため、ビルドごとに入る最新yt-dlpの
// deno要求バージョンが DENO_VERSION を追い越すことがある。追い越されると実行時に
// n-challenge解決が「no solutions」で黙って壊れるため、ビルド時に照合して先に落とす。
function checkYtDlpDenoRequirement() {
  const { execFileSync } = require('child_process');
  const platform = process.platform;
  const isCrossCompileX64 = platform === 'darwin' && process.env.TARGET_ARCH === 'x64' && process.arch === 'arm64';

  // build-backend.js と同じ優先順位で「PyInstallerが凍結するyt-dlp」の環境を選ぶ
  const candidates = [];
  if (isCrossCompileX64) candidates.push(path.join(ROOT_DIR, 'venv-x64', 'bin', 'python'));
  if (platform !== 'win32') candidates.push(path.join(ROOT_DIR, 'venv', 'bin', 'python'));
  candidates.push(platform === 'win32' ? 'python' : 'python3');

  const probe = 'from yt_dlp.utils._jsruntime import DenoJsRuntime; print(".".join(map(str, DenoJsRuntime.MIN_SUPPORTED_VERSION)))';
  let required = null;
  for (const py of candidates) {
    if (py.includes(path.sep) && !fs.existsSync(py)) continue;
    try {
      required = execFileSync(py, ['-c', probe], { stdio: 'pipe' }).toString().trim();
      break;
    } catch (_) { /* 次の候補へ */ }
  }

  if (!required || !/^\d+(\.\d+)*$/.test(required)) {
    console.warn('  [warn] yt-dlpのdeno要求バージョンを取得できませんでした（チェックをスキップ）');
    return;
  }

  const toTuple = (v) => v.split('.').map(Number);
  const cmp = (a, b) => {
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      const d = (a[i] || 0) - (b[i] || 0);
      if (d !== 0) return d;
    }
    return 0;
  };

  if (cmp(toTuple(DENO_VERSION), toTuple(required)) < 0) {
    console.error(`\n${'!'.repeat(60)}`);
    console.error(`同梱deno v${DENO_VERSION} は yt-dlp の要求 (>= ${required}) を満たしません。`);
    console.error('このままビルドするとYouTubeのn-challenge解決が "no solutions" で失敗します。');
    console.error('対処: download-deno.js の DENO_VERSION を上げ、4プラットフォームの');
    console.error('KNOWN_HASHES を更新してください（zipではなく展開後のdenoバイナリのsha256）。');
    console.error(`${'!'.repeat(60)}\n`);
    throw new Error(`Build aborted: bundled deno v${DENO_VERSION} < yt-dlp required v${required}`);
  }
  console.log(`  yt-dlp deno requirement OK (bundled ${DENO_VERSION} >= required ${required})`);
}

// Main
const platform = process.platform;
const arch = process.env.TARGET_ARCH || process.arch;

console.log(`Platform: ${platform} ${arch}`);

try {
  checkYtDlpDenoRequirement();
} catch (error) {
  console.error('  Error:', error.message);
  process.exit(1);
}

downloadDeno(platform, arch)
  .then(() => {
    console.log('  Download complete');
    process.exit(0);
  })
  .catch((error) => {
    console.error('  Error:', error.message);
    process.exit(1);
  });
