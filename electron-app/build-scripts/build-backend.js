const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, '..', '..');
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const BACKEND_DIR = path.join(RESOURCES_DIR, 'backend');

console.log('='.repeat(60));
console.log('Building Backend for Distribution');
console.log('='.repeat(60));

// Step 1: Create resources directory
console.log('\n[1/4] Creating resources directory...');
if (!fs.existsSync(RESOURCES_DIR)) {
  fs.mkdirSync(RESOURCES_DIR, { recursive: true });
}
if (!fs.existsSync(BACKEND_DIR)) {
  fs.mkdirSync(BACKEND_DIR, { recursive: true });
}
console.log('✓ Resources directory ready');

// Step 2: Build Python binary with PyInstaller
console.log('\n[2/4] Building Python binary with PyInstaller...');

const platform = process.platform;
const binaryName = platform === 'win32' ? 'instagram-transcriber.exe' : 'instagram-transcriber';
const distBinaryPath = path.join(ROOT_DIR, 'dist', binaryName);
const targetBinaryPath = path.join(BACKEND_DIR, binaryName);

// Check if PyInstaller is available
// Try both python and python3 for cross-platform compatibility
const pythonCmd = platform === 'win32' ? 'python' : 'python3';
const pipCmd = platform === 'win32' ? 'pip' : 'pip3';

try {
  execSync(`${pythonCmd} -m PyInstaller --version`, { stdio: 'pipe' });
} catch (error) {
  console.error('✗ PyInstaller not found. Installing...');
  try {
    execSync(`${pipCmd} install pyinstaller`, { stdio: 'inherit', cwd: ROOT_DIR });
  } catch (pipError) {
    try {
      execSync(`${pythonCmd} -m pip install pyinstaller`, { stdio: 'inherit', cwd: ROOT_DIR });
    } catch (pythonPipError) {
      console.error('✗ Failed to install PyInstaller. Please install manually:');
      console.error(`   ${pipCmd} install pyinstaller`);
      process.exit(1);
    }
  }
}

// Build with PyInstaller
try {
  console.log('Running PyInstaller...');
  execSync(`${pythonCmd} -m PyInstaller instagram-transcriber.spec --clean`, {
    stdio: 'inherit',
    cwd: ROOT_DIR
  });

  // Check if binary was created
  if (!fs.existsSync(distBinaryPath)) {
    throw new Error(`Binary not found at: ${distBinaryPath}`);
  }

  // Copy to resources
  console.log(`Copying binary to: ${targetBinaryPath}`);
  fs.copyFileSync(distBinaryPath, targetBinaryPath);

  // Make executable on Unix
  if (platform !== 'win32') {
    fs.chmodSync(targetBinaryPath, 0o755);
  }

  console.log('✓ Python binary built successfully');
} catch (error) {
  console.error('✗ Failed to build Python binary:', error.message);
  process.exit(1);
}

// Step 3: Download ffmpeg
console.log('\n[3/4] Downloading ffmpeg...');
try {
  execSync('node build-scripts/download-ffmpeg.js', {
    stdio: 'inherit',
    cwd: path.join(__dirname, '..')
  });
  console.log('✓ ffmpeg downloaded');
} catch (error) {
  console.error('✗ Failed to download ffmpeg:', error.message);
  process.exit(1);
}

// Step 4: Verify resources
console.log('\n[4/4] Verifying resources...');

const ffmpegName = platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
const ffmpegPath = path.join(RESOURCES_DIR, 'ffmpeg', ffmpegName);

const checks = [
  { name: 'Backend binary', path: targetBinaryPath },
  { name: 'ffmpeg binary', path: ffmpegPath }
];

let allGood = true;
for (const check of checks) {
  if (fs.existsSync(check.path)) {
    const stats = fs.statSync(check.path);
    const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
    console.log(`✓ ${check.name}: ${sizeMB} MB`);
  } else {
    console.error(`✗ ${check.name} not found: ${check.path}`);
    allGood = false;
  }
}

if (!allGood) {
  console.error('\n✗ Build failed: Some resources are missing');
  process.exit(1);
}

console.log('\n' + '='.repeat(60));
console.log('✓ Backend build complete!');
console.log('='.repeat(60));
console.log('\nResources location:', RESOURCES_DIR);
