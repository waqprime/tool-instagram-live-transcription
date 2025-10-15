const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { ProcessManager } = require('./backend/process-bundled');
const { autoUpdater } = require('electron-updater');
const fs = require('fs');

// Set application name
app.setName('Instagram Live Transcription');

let mainWindow;
let processManager;
const isDev = process.argv.includes('--dev');

// Get bundled backend binary path
function getBackendBinaryPath() {
  const isWindows = process.platform === 'win32';
  const binaryName = isWindows ? 'instagram-transcriber.exe' : 'instagram-transcriber';

  if (isDev) {
    // In development, use the binary from resources if it exists
    const devBinaryPath = path.join(__dirname, 'resources', 'backend', binaryName);
    if (fs.existsSync(devBinaryPath)) {
      console.log('Using dev binary:', devBinaryPath);
      return devBinaryPath;
    }
    console.warn('Dev binary not found. Run "npm run prebuild" first.');
    return null;
  }

  // In production, use the bundled binary
  const binaryPath = path.join(process.resourcesPath, 'resources', 'backend', binaryName);
  console.log('Using production binary:', binaryPath);
  return binaryPath;
}

// Get ffmpeg binary path
function getFFmpegPath() {
  const isWindows = process.platform === 'win32';
  const ffmpegName = isWindows ? 'ffmpeg.exe' : 'ffmpeg';

  if (isDev) {
    const devFFmpegPath = path.join(__dirname, 'resources', 'ffmpeg', ffmpegName);
    if (fs.existsSync(devFFmpegPath)) {
      return devFFmpegPath;
    }
    return null;
  }

  return path.join(process.resourcesPath, 'resources', 'ffmpeg', ffmpegName);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#0f1729',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    // Default title bar for better window dragging
    titleBarStyle: 'default',
    frame: true
  });

  mainWindow.loadFile('index.html');

  // Development mode: Open DevTools automatically
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // F12 to toggle DevTools
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12') {
      mainWindow.webContents.toggleDevTools();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  // Check for updates (only in production)
  if (!isDev) {
    checkForUpdates();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (processManager) {
    processManager.cleanup();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Handlers
ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('start-processing', async (event, config) => {
  try {
    console.log('Starting processing with config:', config);

    // Get bundled backend binary
    const binaryPath = getBackendBinaryPath();
    if (!binaryPath) {
      return {
        success: false,
        error: 'Backend binary not found. Please rebuild the application.'
      };
    }

    if (!fs.existsSync(binaryPath)) {
      return {
        success: false,
        error: `Backend binary does not exist: ${binaryPath}`
      };
    }

    // Get ffmpeg path
    const ffmpegPath = getFFmpegPath();
    if (ffmpegPath && !fs.existsSync(ffmpegPath)) {
      console.warn('ffmpeg not found at:', ffmpegPath);
    }

    console.log('Backend binary:', binaryPath);
    console.log('ffmpeg binary:', ffmpegPath);

    // Initialize ProcessManager with bundled binary
    processManager = new ProcessManager(binaryPath, ffmpegPath);

    // Set up log handler
    processManager.onLog((log) => {
      mainWindow.webContents.send('processing-log', log);
    });

    // Set up progress handler
    processManager.onProgress((progress) => {
      mainWindow.webContents.send('processing-progress', progress);
    });

    // Start processing
    const results = await processManager.processUrls(
      config.urls,
      config.outputDir,
      config.language,
      config.model
    );

    return { success: true, results };
  } catch (error) {
    console.error('Processing error:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('stop-processing', async () => {
  if (processManager) {
    processManager.stop();
    return { success: true };
  }
  return { success: false, error: 'No active process' };
});

ipcMain.handle('open-folder', async (event, folderPath) => {
  const { shell } = require('electron');
  shell.openPath(folderPath);
});

// Auto-update functions
function checkForUpdates() {
  // For private repositories, set token if needed
  // autoUpdater.setFeedURL({
  //   provider: 'github',
  //   owner: 'YOUR_USERNAME',
  //   repo: 'instagram-live-transcription',
  //   private: true,
  //   token: 'YOUR_GITHUB_TOKEN'  // Only for private repos
  // });

  autoUpdater.checkForUpdatesAndNotify();

  autoUpdater.on('update-available', (info) => {
    console.log('Update available:', info.version);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-available', info);
    }
  });

  autoUpdater.on('update-downloaded', (info) => {
    console.log('Update downloaded:', info.version);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-downloaded', info);
    }
  });

  autoUpdater.on('error', (error) => {
    console.error('Auto-updater error:', error);
  });

  autoUpdater.on('download-progress', (progressObj) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-progress', progressObj);
    }
  });
}

ipcMain.handle('install-update', () => {
  autoUpdater.quitAndInstall();
});

// Log uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('processing-log', {
      type: 'error',
      message: `Fatal error: ${error.message}`
    });
  }
});
