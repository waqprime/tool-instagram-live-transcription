const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const unzipper = require('unzipper');

const FFMPEG_VERSION = '6.0';
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const FFMPEG_DIR = path.join(RESOURCES_DIR, 'ffmpeg');

// Platform-specific download URLs
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

async function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    console.log(`Downloading from: ${url}`);

    const file = fs.createWriteStream(destPath);

    const download = (downloadUrl) => {
      const parsedUrl = new URL(downloadUrl);
      const protocol = parsedUrl.protocol === 'https:' ? https : require('http');

      protocol.get(downloadUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (response) => {
        // Handle redirects
        if (response.statusCode === 302 || response.statusCode === 301) {
          const redirectLocation = response.headers.location;
          // Convert relative URLs to absolute
          const redirectUrl = redirectLocation.startsWith('http')
            ? redirectLocation
            : new URL(redirectLocation, downloadUrl).href;
          console.log(`Redirecting to: ${redirectUrl}`);
          download(redirectUrl);
          return;
        }

        response.pipe(file);

        file.on('finish', () => {
          file.close();
          console.log(`Downloaded to: ${destPath}`);
          resolve();
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
      // Use Node.js unzipper for cross-platform compatibility
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

  // Recursively find the binary
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

  // Make executable on Unix
  if (process.platform !== 'win32') {
    fs.chmodSync(destPath, 0o755);
  }
}

async function downloadFFmpeg(platform, arch) {
  // Create directories
  if (!fs.existsSync(RESOURCES_DIR)) {
    fs.mkdirSync(RESOURCES_DIR, { recursive: true });
  }

  if (!fs.existsSync(FFMPEG_DIR)) {
    fs.mkdirSync(FFMPEG_DIR, { recursive: true });
  }

  // Check if ffmpeg already exists
  const binaryName = platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
  const ffmpegBinaryPath = path.join(FFMPEG_DIR, binaryName);

  if (fs.existsSync(ffmpegBinaryPath)) {
    console.log('ffmpeg binary already exists, skipping download');
    return;
  }

  // Get download URL
  const platformUrls = FFMPEG_URLS[platform];
  if (!platformUrls) {
    throw new Error(`Unsupported platform: ${platform}`);
  }

  const downloadUrl = platformUrls[arch] || platformUrls.x64;
  if (!downloadUrl) {
    throw new Error(`Unsupported architecture: ${arch} on ${platform}`);
  }

  // Download
  const archiveExt = downloadUrl.includes('.zip') ? '.zip' : '.tar.xz';
  const archivePath = path.join(RESOURCES_DIR, `ffmpeg${archiveExt}`);

  console.log(`Downloading ffmpeg for ${platform} ${arch}...`);
  await downloadFile(downloadUrl, archivePath);

  // Extract
  const extractDir = path.join(RESOURCES_DIR, 'ffmpeg-temp');
  if (!fs.existsSync(extractDir)) {
    fs.mkdirSync(extractDir, { recursive: true });
  }

  await extractArchive(archivePath, extractDir);

  // Find and move binary
  findAndMoveBinary(extractDir, ffmpegBinaryPath, 'ffmpeg');

  // Cleanup
  console.log('Cleaning up temporary files...');
  fs.rmSync(extractDir, { recursive: true, force: true });
  fs.unlinkSync(archivePath);

  console.log('✓ ffmpeg binary ready');
}

// Main
const platform = process.platform;
const arch = process.arch;

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
