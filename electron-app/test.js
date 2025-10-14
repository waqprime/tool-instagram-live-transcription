#!/usr/bin/env node

/**
 * Environment Verification Script
 * Tests all dependencies before running the app
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('\n========================================');
console.log('Instagram Live Transcription - Setup Check');
console.log('========================================\n');

let allPassed = true;

// Test 1: Check Node.js version
function testNodeVersion() {
  console.log('1. Checking Node.js version...');
  const version = process.version;
  const major = parseInt(version.slice(1).split('.')[0]);

  if (major >= 18) {
    console.log(`   ✓ Node.js ${version} (OK)\n`);
    return true;
  } else {
    console.log(`   ✗ Node.js ${version} (Need 18+)\n`);
    return false;
  }
}

// Test 2: Check Python virtual environment
function testPythonVenv() {
  console.log('2. Checking Python virtual environment...');
  const venvPath = path.join(__dirname, '..', 'venv_new');
  const pythonPath = path.join(venvPath, 'bin', 'python3');

  if (fs.existsSync(pythonPath)) {
    console.log(`   ✓ Virtual environment found: ${venvPath}\n`);
    return pythonPath;
  } else {
    console.log(`   ✗ Virtual environment not found at: ${venvPath}`);
    console.log(`   Run: python3 -m venv ${venvPath}\n`);
    return null;
  }
}

// Test 3: Check Python dependencies
async function testPythonDeps(pythonPath) {
  console.log('3. Checking Python dependencies...');

  const deps = ['whisper', 'yt_dlp'];
  const results = [];

  for (const dep of deps) {
    const result = await checkPythonModule(pythonPath, dep);
    results.push(result);

    if (result) {
      console.log(`   ✓ ${dep} installed`);
    } else {
      console.log(`   ✗ ${dep} not installed`);
    }
  }

  console.log('');
  return results.every(r => r);
}

function checkPythonModule(pythonPath, module) {
  return new Promise((resolve) => {
    const proc = spawn(pythonPath, ['-c', `import ${module}`]);

    proc.on('close', (code) => {
      resolve(code === 0);
    });

    proc.on('error', () => {
      resolve(false);
    });
  });
}

// Test 4: Check ffmpeg
async function testFfmpeg() {
  console.log('4. Checking ffmpeg...');

  return new Promise((resolve) => {
    const proc = spawn('ffmpeg', ['-version']);

    proc.on('close', (code) => {
      if (code === 0) {
        console.log('   ✓ ffmpeg installed\n');
        resolve(true);
      } else {
        console.log('   ✗ ffmpeg not found\n');
        resolve(false);
      }
    });

    proc.on('error', () => {
      console.log('   ✗ ffmpeg not found');
      console.log('   Install: brew install ffmpeg (macOS)\n');
      resolve(false);
    });
  });
}

// Test 5: Check Python scripts
function testPythonScripts() {
  console.log('5. Checking Python scripts...');

  const scripts = [
    'downloader.py',
    'audio_converter.py',
    'transcriber.py'
  ];

  let allFound = true;

  for (const script of scripts) {
    const scriptPath = path.join(__dirname, '..', script);
    if (fs.existsSync(scriptPath)) {
      console.log(`   ✓ ${script}`);
    } else {
      console.log(`   ✗ ${script} not found`);
      allFound = false;
    }
  }

  console.log('');
  return allFound;
}

// Test 6: Check output directory
function testOutputDir() {
  console.log('6. Checking output directory...');

  const outputDir = path.join(__dirname, '..', 'output');

  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    console.log(`   ✓ Created output directory: ${outputDir}\n`);
  } else {
    console.log(`   ✓ Output directory exists: ${outputDir}\n`);
  }

  return true;
}

// Run all tests
async function runTests() {
  allPassed = testNodeVersion() && allPassed;

  const pythonPath = testPythonVenv();
  allPassed = (pythonPath !== null) && allPassed;

  if (pythonPath) {
    allPassed = await testPythonDeps(pythonPath) && allPassed;
  }

  allPassed = await testFfmpeg() && allPassed;
  allPassed = testPythonScripts() && allPassed;
  allPassed = testOutputDir() && allPassed;

  // Summary
  console.log('========================================');
  if (allPassed) {
    console.log('✓ All checks passed! Ready to run.');
    console.log('\nStart the app with:');
    console.log('  npm start       (Production)');
    console.log('  npm run dev     (Development with DevTools)');
    console.log('  ./start.sh      (Quick start)');
  } else {
    console.log('✗ Some checks failed. Please fix the issues above.');
    console.log('\nSetup instructions:');
    console.log('  1. Install Python dependencies:');
    console.log('     source ../venv_new/bin/activate');
    console.log('     pip install -r ../requirements.txt');
    console.log('  2. Install ffmpeg:');
    console.log('     brew install ffmpeg  (macOS)');
  }
  console.log('========================================\n');

  process.exit(allPassed ? 0 : 1);
}

// Start tests
runTests().catch(error => {
  console.error('Error running tests:', error);
  process.exit(1);
});
