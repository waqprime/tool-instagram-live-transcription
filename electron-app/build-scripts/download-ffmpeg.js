const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');
const unzipper = require('unzipper');

const FFMPEG_VERSION = '8.0.1';
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const FFMPEG_DIR = path.join(RESOURCES_DIR, 'ffmpeg');
const HASH_FILE = path.join(FFMPEG_DIR, '.ffmpeg_hash');

// 既知の正当なハッシュ値（検証済みバイナリから記録）
// evermeet.cx / gyan.dev がリビルドするとハッシュが変わるため、
// ビルドが失敗した場合は新バイナリを手動で検証し、ここを更新すること。
// ハッシュ未登録のプラットフォームは初回ダウンロード時に記録・表示される。
const KNOWN_HASHES = {
  // evermeet.cx ffmpeg 8.0.1 — darwin arm64/x64 は同一URLのため同一バイナリ
  'darwin-arm64': '430d60fbf419dab28daee9b679e7929a31ee9bae53f6e42e8ae26b725584290f',
  'darwin-x64': '430d60fbf419dab28daee9b679e7929a31ee9bae53f6e42e8ae26b725584290f',
  // gyan.dev ffmpeg 8.0.1 essentials
  'win32-x64': '5af82a0d4fe2b9eae211b967332ea97edfc51c6b328ca35b827e73eac560dc0d',
};

// Platform-specific download URLs
// バージョン固定URLが404になる場合があるため、最新リリースURLを使用。
// 真正性はKNOWN_HASHESで担保する。
const FFMPEG_URLS = {
  darwin: {
    arm64: `https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip`,
    x64: `https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip`
  },
  win32: {
    x64: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`
  },
  linux: {
    x64: `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz`
  }
};

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
  console.log(`✓ Hash verified: ${actualHash.substring(0, 16)}...`);
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
        if (response.statusCode === 301 || response.statusCode === 302 || response.statusCode === 303 || response.statusCode === 307 || response.statusCode === 308) {
          response.resume();
          const redirectLocation = response.headers.location;
          const redirectUrl = redirectLocation.startsWith('http')
            ? redirectLocation
            : new URL(redirectLocation, downloadUrl).href;
          console.log(`Redirecting to: ${redirectUrl}`);
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

async function extractArchive(archivePath, destDir) {
  const ext = path.extname(archivePath);

  console.log(`Extracting ${archivePath}...`);

  try {
    if (ext === '.zip') {
      await fs.createReadStream(archivePath)
        .pipe(unzipper.Extract({ path: destDir }))
        .promise();
    } else if (ext === '.xz') {
      execSync(`tar -xJf "${archivePath}" -C "${destDir}"`, { stdio: 'inherit' });
    }

    console.log('Extraction complete');
  } catch (error) {
    throw new Error(`Failed to extract archive: ${error.message}`);
  }
}

function findAndMoveBinary(searchDir, destPath, binaryName) {
  console.log(`Searching for ${binaryName} in ${searchDir}...`);

  const findBinary = (dir) => {
    const items = fs.readdirSync(dir);

    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        const found = findBinary(fullPath);
        if (found) return found;
      } else if (item === binaryName || item === `${binaryName}.exe`) {
        return fullPath;
      }
    }

    return null;
  };

  const binaryPath = findBinary(searchDir);

  if (!binaryPath) {
    throw new Error(`Could not find ${binaryName} binary`);
  }

  console.log(`Found binary: ${binaryPath}`);
  console.log(`Moving to: ${destPath}`);

  fs.copyFileSync(binaryPath, destPath);

  if (process.platform !== 'win32') {
    fs.chmodSync(destPath, 0o755);
  }
}

async function downloadFFmpeg(platform, arch) {
  if (!fs.existsSync(RESOURCES_DIR)) {
    fs.mkdirSync(RESOURCES_DIR, { recursive: true });
  }

  if (!fs.existsSync(FFMPEG_DIR)) {
    fs.mkdirSync(FFMPEG_DIR, { recursive: true });
  }

  const binaryName = platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
  const ffmpegBinaryPath = path.join(FFMPEG_DIR, binaryName);

  const knownKey = `${platform}-${arch}`;
  const knownHash = KNOWN_HASHES[knownKey];

  if (fs.existsSync(ffmpegBinaryPath)) {
    // 既存バイナリのハッシュ検証（KNOWN_HASHES優先、なければHASH_FILE）
    const expectedHash = knownHash
      || (fs.existsSync(HASH_FILE) ? fs.readFileSync(HASH_FILE, 'utf-8').trim() : null);

    if (expectedHash) {
      try {
        verifyHash(ffmpegBinaryPath, expectedHash);
        console.log('✓ ffmpeg binary verified, skipping download');
        return;
      } catch (e) {
        console.warn(`⚠ ${e.message}`);
        console.log('Re-downloading ffmpeg...');
        fs.unlinkSync(ffmpegBinaryPath);
        if (fs.existsSync(HASH_FILE)) fs.unlinkSync(HASH_FILE);
      }
    } else {
      // ハッシュが一切ない場合は再ダウンロード（信頼できないバイナリを使わない）
      console.warn('⚠ No known hash for existing ffmpeg binary. Re-downloading...');
      fs.unlinkSync(ffmpegBinaryPath);
    }
  }

  const platformUrls = FFMPEG_URLS[platform];
  if (!platformUrls) {
    throw new Error(`Unsupported platform: ${platform}`);
  }

  const downloadUrl = platformUrls[arch] || platformUrls.x64;
  if (!downloadUrl) {
    throw new Error(`Unsupported architecture: ${arch} on ${platform}`);
  }

  const archiveExt = downloadUrl.includes('.zip') ? '.zip' : '.tar.xz';
  const archivePath = path.join(RESOURCES_DIR, `ffmpeg${archiveExt}`);

  console.log(`Downloading ffmpeg for ${platform} ${arch}...`);
  await downloadFile(downloadUrl, archivePath);

  const extractDir = path.join(RESOURCES_DIR, 'ffmpeg-temp');
  if (!fs.existsSync(extractDir)) {
    fs.mkdirSync(extractDir, { recursive: true });
  }

  await extractArchive(archivePath, extractDir);
  findAndMoveBinary(extractDir, ffmpegBinaryPath, 'ffmpeg');

  // ハッシュを記録・検証
  const hash = computeFileHash(ffmpegBinaryPath);
  if (knownHash) {
    if (hash !== knownHash) {
      throw new Error(
        `ffmpeg hash mismatch for ${platform}-${arch}!\n` +
        `  Expected: ${knownHash}\n` +
        `  Got:      ${hash}\n` +
        `The downloaded binary may have been tampered with.`
      );
    }
    console.log(`✓ ffmpeg hash verified against known good hash`);
  } else {
    // KNOWN_HASHES未登録 → 初回ダウンロードを信じない。ハッシュを表示してビルドを中断。
    // 開発者がバイナリを手動検証した上で KNOWN_HASHES に追加する必要がある。
    // 未検証ファイルをすべて削除してからビルド中断
    fs.unlinkSync(ffmpegBinaryPath);
    if (fs.existsSync(extractDir)) fs.rmSync(extractDir, { recursive: true, force: true });
    if (fs.existsSync(archivePath)) fs.unlinkSync(archivePath);
    console.error(`\n${'!'.repeat(60)}`);
    console.error(`ffmpeg downloaded for ${platform}-${arch} but no known hash registered.`);
    console.error(`Downloaded binary hash: '${hash}'`);
    console.error(`\nTo proceed, verify this binary is legitimate, then add to KNOWN_HASHES in download-ffmpeg.js:`);
    console.error(`  '${platform}-${arch}': '${hash}'`);
    console.error(`${'!'.repeat(60)}\n`);
    throw new Error(
      `Build aborted: ffmpeg hash for ${platform}-${arch} is not in KNOWN_HASHES.\n` +
      `Add the hash above after manual verification.`
    );
  }
  fs.writeFileSync(HASH_FILE, hash);
  console.log(`✓ ffmpeg hash recorded: ${hash.substring(0, 16)}...`);

  // Cleanup
  console.log('Cleaning up temporary files...');
  fs.rmSync(extractDir, { recursive: true, force: true });
  fs.unlinkSync(archivePath);

  console.log('✓ ffmpeg binary ready');
}

// Main
const platform = process.platform;
const arch = process.env.TARGET_ARCH || process.arch;

console.log(`Platform: ${platform} ${arch}`);

downloadFFmpeg(platform, arch)
  .then(() => {
    console.log('✓ Download complete');
    process.exit(0);
  })
  .catch((error) => {
    console.error('✗ Error:', error.message);
    process.exit(1);
  });
