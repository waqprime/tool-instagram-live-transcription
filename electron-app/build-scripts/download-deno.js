const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const unzipper = require('unzipper');

const DENO_VERSION = '2.1.4';
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const DENO_DIR = path.join(RESOURCES_DIR, 'deno');
const HASH_FILE = path.join(DENO_DIR, '.deno_hash');

// Known good hashes (verified binaries).
// When a new version is released, run the build once to get the hash,
// verify the binary manually, then add the hash here.
const KNOWN_HASHES = {
  'win32-x64': '83c98e4365c9e629c6a351b141cbabed0abe6265bde93b256cc10e49d4265fee',
  'darwin-arm64': '4a3228aa41c0767099ae31bf51e4c6f2cbfcef6b380996f524e885865e586e40',
  'darwin-x64': '09fc6ce6396e54bf97238e26d82a65360b22255def184f57bc67e1b3aeb7a629',
  'linux-x64': '10af0f31dc48bfea949e83daa042c03a9a84f7c52056d20597cac7ad005ab6aa',
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

// Main
const platform = process.platform;
const arch = process.env.TARGET_ARCH || process.arch;

console.log(`Platform: ${platform} ${arch}`);

downloadDeno(platform, arch)
  .then(() => {
    console.log('  Download complete');
    process.exit(0);
  })
  .catch((error) => {
    console.error('  Error:', error.message);
    process.exit(1);
  });
