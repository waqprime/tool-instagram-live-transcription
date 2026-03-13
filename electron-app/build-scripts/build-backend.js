const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, '..', '..');
const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const BACKEND_DIR = path.join(RESOURCES_DIR, 'backend');

// Build configuration from environment variables
const TARGET_ARCH = process.env.TARGET_ARCH; // 'arm64' or 'x64'
const BUILD_VARIANT = process.env.BUILD_VARIANT || 'full'; // 'full' or 'lite'

console.log('='.repeat(60));
console.log('Building Backend for Distribution');
console.log(`  Architecture: ${TARGET_ARCH || process.arch} (${TARGET_ARCH ? 'override' : 'native'})`);
console.log(`  Variant: ${BUILD_VARIANT}`);
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

// Select spec file based on build variant
const specFile = BUILD_VARIANT === 'lite'
  ? 'instagram-transcriber-lite.spec'
  : 'instagram-transcriber.spec';
console.log(`Using spec file: ${specFile}`);

// Build environment: pass PYINSTALLER_TARGET_ARCH if TARGET_ARCH is set
const buildEnv = { ...process.env };
if (TARGET_ARCH) {
  // Map Node.js arch names to PyInstaller/macOS arch names
  const archMap = { 'arm64': 'arm64', 'x64': 'x86_64' };
  const pyinstallerArch = archMap[TARGET_ARCH] || TARGET_ARCH;
  buildEnv.PYINSTALLER_TARGET_ARCH = pyinstallerArch;
  console.log(`Target architecture: ${TARGET_ARCH} → PyInstaller: ${pyinstallerArch}`);
}

// On macOS arm64 host building for x64, use venv-x64 python
const isCrossCompileX64 = platform === 'darwin' && TARGET_ARCH === 'x64' && process.arch === 'arm64';
let pyinstallerCmd = `${pythonCmd} -m PyInstaller`;

if (isCrossCompileX64) {
  // Use x64 venv's pyinstaller directly (system python3 is arm64-only)
  const venvX64Pyinstaller = path.join(ROOT_DIR, 'venv-x64', 'bin', 'pyinstaller');
  const venvX64Exists = fs.existsSync(venvX64Pyinstaller);
  if (venvX64Exists) {
    pyinstallerCmd = `arch -x86_64 ${venvX64Pyinstaller}`;
    console.log(`Cross-compiling: using venv-x64 PyInstaller (${venvX64Pyinstaller})`);
  } else {
    pyinstallerCmd = `arch -x86_64 ${pythonCmd} -m PyInstaller`;
    console.log('Cross-compiling: arm64 host → x86_64 target (using arch -x86_64)');
  }
}

// Build with PyInstaller
try {
  console.log('Running PyInstaller...');
  execSync(`${pyinstallerCmd} ${specFile} --clean`, {
    stdio: 'inherit',
    cwd: ROOT_DIR,
    env: buildEnv
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
    cwd: path.join(__dirname, '..'),
    env: buildEnv
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
