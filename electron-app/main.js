const { app, BrowserWindow, ipcMain, dialog, safeStorage, Menu } = require('electron');
const path = require('path');
const os = require('os');
const { execFileSync, spawn } = require('child_process');
const { ProcessManager } = require('./backend/process-bundled');
const { autoUpdater } = require('electron-updater');
const fs = require('fs');

// Set application name
app.setName('文字起こしツール');

let mainWindow;
let processManager;
const isDev = process.argv.includes('--dev');

// Settings file path (in user home directory, survives app upgrades)
const SETTINGS_DIR = path.join(os.homedir(), '.transcription-tool');
const SETTINGS_FILE = path.join(SETTINGS_DIR, 'settings.json');

function getSettingsPath() {
  return SETTINGS_FILE;
}

// Load settings from file
function loadSettings() {
  try {
    const settingsPath = getSettingsPath();

    // Migrate from old location if needed
    if (!fs.existsSync(settingsPath)) {
      const oldPath = path.join(app.getPath('userData'), 'settings.json');
      if (fs.existsSync(oldPath)) {
        if (!fs.existsSync(SETTINGS_DIR)) {
          fs.mkdirSync(SETTINGS_DIR, { recursive: true });
        }
        fs.copyFileSync(oldPath, settingsPath);
        console.log('Migrated settings from', oldPath, 'to', settingsPath);
      }
    }

    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf-8');
      const settings = JSON.parse(data);

      // Decrypt API key if encrypted
      if (settings._apiKeyEncrypted && settings.apiKey) {
        try {
          const encrypted = Buffer.from(settings.apiKey, 'base64');
          settings.apiKey = safeStorage.decryptString(encrypted);
        } catch (decryptError) {
          console.error('Failed to decrypt API key:', decryptError);
          settings.apiKey = '';
        }
        delete settings._apiKeyEncrypted;
      }

      // Decrypt Gemini API key if encrypted
      if (settings._geminiApiKeyEncrypted && settings.geminiApiKey) {
        try {
          const encrypted = Buffer.from(settings.geminiApiKey, 'base64');
          settings.geminiApiKey = safeStorage.decryptString(encrypted);
        } catch (decryptError) {
          console.error('Failed to decrypt Gemini API key:', decryptError);
          settings.geminiApiKey = '';
        }
        delete settings._geminiApiKeyEncrypted;
      }

      return settings;
    }
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
  return {};
}

// Save settings to file
function saveSettings(settings) {
  try {
    if (!fs.existsSync(SETTINGS_DIR)) {
      fs.mkdirSync(SETTINGS_DIR, { recursive: true });
    }
    const settingsPath = getSettingsPath();

    // 削除専用リクエストの場合: 既存設定から該当キーだけ削除して保存
    if (settings._deleteApiKey || settings._deleteGeminiApiKey) {
      const existing = fs.existsSync(settingsPath)
        ? JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
        : {};
      if (settings._deleteApiKey) {
        delete existing.apiKey;
        delete existing._apiKeyEncrypted;
      }
      if (settings._deleteGeminiApiKey) {
        delete existing.geminiApiKey;
        delete existing._geminiApiKeyEncrypted;
      }
      fs.writeFileSync(settingsPath, JSON.stringify(existing, null, 2), 'utf-8');
      return true;
    }

    const toSave = { ...settings };

    // 保存済みキーを維持（rendererから空で送られた場合）
    if (toSave._keepApiKey) {
      const existing = loadSettings();
      if (existing.apiKey) toSave.apiKey = existing.apiKey;
    }
    delete toSave._keepApiKey;
    if (toSave._keepGeminiApiKey) {
      const existing = loadSettings();
      if (existing.geminiApiKey) toSave.geminiApiKey = existing.geminiApiKey;
    }
    delete toSave._keepGeminiApiKey;

    // Encrypt API keys if safeStorage is available
    if (toSave.apiKey || toSave.geminiApiKey) {
      if (safeStorage.isEncryptionAvailable()) {
        if (toSave.apiKey) {
          const encrypted = safeStorage.encryptString(toSave.apiKey);
          toSave.apiKey = encrypted.toString('base64');
          toSave._apiKeyEncrypted = true;
        }
        if (toSave.geminiApiKey) {
          const encrypted = safeStorage.encryptString(toSave.geminiApiKey);
          toSave.geminiApiKey = encrypted.toString('base64');
          toSave._geminiApiKeyEncrypted = true;
        }
      } else {
        // safeStorageが利用不可の場合、APIキーを平文で保存しない
        console.warn('safeStorage is not available. API keys will NOT be saved.');
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('processing-log', {
            type: 'warning',
            message: 'APIキーの暗号化が利用できないため、キーは保存されませんでした。アプリを再起動して再試行してください。'
          });
        }
        delete toSave.apiKey;
        delete toSave.geminiApiKey;
      }
    }

    fs.writeFileSync(settingsPath, JSON.stringify(toSave, null, 2), 'utf-8');
    return true;
  } catch (error) {
    console.error('Failed to save settings:', error);
    return false;
  }
}

// Get bundled backend binary path
function getBackendBinaryPath() {
  const isWindows = process.platform === 'win32';
  const binaryName = isWindows ? 'instagram-transcriber.exe' : 'instagram-transcriber';

  if (isDev) {
    // In development, use the binary from resources if it exists
    const devBinaryPath = path.join(__dirname, 'resources', 'backend', binaryName);
    if (fs.existsSync(devBinaryPath)) {
      console.log('Using dev binary:', path.basename(devBinaryPath));
      return devBinaryPath;
    }
    console.warn('Dev binary not found. Run "npm run prebuild" first.');
    return null;
  }

  // In production, use the bundled binary
  const binaryPath = path.join(process.resourcesPath, 'resources', 'backend', binaryName);
  console.log('Using production binary:', path.basename(binaryPath));
  return binaryPath;
}

// Check if ffmpeg is available on system PATH
function findSystemFFmpeg() {
  const isWindows = process.platform === 'win32';
  const ffmpegName = isWindows ? 'ffmpeg.exe' : 'ffmpeg';

  try {
    // Try running ffmpeg -version to see if it's on PATH
    execFileSync(ffmpegName, ['-version'], { stdio: 'ignore', timeout: 5000 });
    console.log('Found ffmpeg on system PATH');
    return ffmpegName;
  } catch (e) {
    // Not on PATH
  }

  // Check common installation locations on Windows
  if (isWindows) {
    const commonPaths = [
      path.join(os.homedir(), 'scoop', 'shims', 'ffmpeg.exe'),
      'C:\\ffmpeg\\bin\\ffmpeg.exe',
      'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
      'C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe',
    ];
    for (const p of commonPaths) {
      if (fs.existsSync(p)) {
        console.log('Found ffmpeg at:', path.basename(p));
        return p;
      }
    }
  }

  return null;
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
    // Fallback to system ffmpeg in dev mode
    return findSystemFFmpeg();
  }

  // In production, use ONLY the bundled binary (no system fallback for security)
  const bundledPath = path.join(process.resourcesPath, 'resources', 'ffmpeg', ffmpegName);
  if (fs.existsSync(bundledPath)) {
    return bundledPath;
  }

  console.error('Bundled ffmpeg not found. Application may be corrupted.');
  return null;
}

// Get deno binary directory path (yt-dlp needs deno for YouTube JS extraction)
function getDenoDirPath() {
  const isWindows = process.platform === 'win32';
  const denoName = isWindows ? 'deno.exe' : 'deno';

  if (isDev) {
    const devDenoDir = path.join(__dirname, 'resources', 'deno');
    if (fs.existsSync(path.join(devDenoDir, denoName))) {
      return devDenoDir;
    }
    // In dev mode, deno on system PATH is fine (yt-dlp finds it automatically)
    return null;
  }

  // In production, use the bundled binary
  const bundledDir = path.join(process.resourcesPath, 'resources', 'deno');
  if (fs.existsSync(path.join(bundledDir, denoName))) {
    return bundledDir;
  }

  console.warn('Bundled deno not found. YouTube may use limited formats.');
  return null;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#f5f5f7',
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

  // F12 to toggle DevTools (development only)
  if (isDev) {
    mainWindow.webContents.on('before-input-event', (event, input) => {
      if (input.key === 'F12') {
        mainWindow.webContents.toggleDevTools();
      }
    });
  }

  // Right-click context menu (cut/copy/paste)
  mainWindow.webContents.on('context-menu', (event, params) => {
    const menuItems = [];

    if (params.isEditable) {
      menuItems.push(
        { label: '切り取り', role: 'cut' },
        { label: 'コピー', role: 'copy' },
        { label: '貼り付け', role: 'paste' },
        { type: 'separator' },
        { label: 'すべて選択', role: 'selectAll' }
      );
    } else if (params.selectionText) {
      menuItems.push(
        { label: 'コピー', role: 'copy' },
        { type: 'separator' },
        { label: 'すべて選択', role: 'selectAll' }
      );
    }

    if (menuItems.length > 0) {
      Menu.buildFromTemplate(menuItems).popup();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  // Auto-update check
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

// Get default output directory based on OS
function getDefaultOutputDirectory() {
  const os = require('os');
  const homeDir = os.homedir();
  const platform = process.platform;

  if (platform === 'darwin') {
    // macOS: ~/Downloads/InstagramTranscripts
    return path.join(homeDir, 'Downloads', 'InstagramTranscripts');
  } else if (platform === 'win32') {
    // Windows: ~/Downloads/InstagramTranscripts
    return path.join(homeDir, 'Downloads', 'InstagramTranscripts');
  } else {
    // Linux: ~/Downloads/InstagramTranscripts
    return path.join(homeDir, 'Downloads', 'InstagramTranscripts');
  }
}

// Model cache directory (matches transcriber.py)
const MODEL_CACHE_DIR = path.join(os.homedir(), '.cache', 'transcription-tool', 'models');

// faster-whisper model → HuggingFace repo mapping
const MODEL_REPO_MAP = {
  'large-v3-turbo': 'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo',
  'large-v3': 'models--Systran--faster-whisper-large-v3',
  'large-v2': 'models--Systran--faster-whisper-large-v2',
  'medium': 'models--Systran--faster-whisper-medium',
  'small': 'models--Systran--faster-whisper-small',
  'base': 'models--Systran--faster-whisper-base',
  'tiny': 'models--Systran--faster-whisper-tiny',
};

// Check which faster-whisper models are downloaded
function getDownloadedModels() {
  const downloaded = {};
  for (const [model, dirName] of Object.entries(MODEL_REPO_MAP)) {
    const modelPath = path.join(MODEL_CACHE_DIR, dirName, 'snapshots');
    downloaded[model] = fs.existsSync(modelPath) && fs.readdirSync(modelPath).length > 0;
  }
  return downloaded;
}

// Active model download process
let modelDownloadProcess = null;

// IPC Handlers
ipcMain.handle('get-default-output-dir', async () => {
  return getDefaultOutputDirectory();
});

ipcMain.handle('load-settings', async () => {
  const settings = loadSettings();
  // APIキー文字列はrendererに返さない（保存済みフラグのみ）
  const safeSettings = { ...settings };
  if (safeSettings.apiKey) {
    safeSettings._hasApiKey = true;
    delete safeSettings.apiKey;
  }
  if (safeSettings.geminiApiKey) {
    safeSettings._hasGeminiApiKey = true;
    delete safeSettings.geminiApiKey;
  }
  return safeSettings;
});

ipcMain.handle('save-settings', async (event, settings) => {
  return saveSettings(settings);
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Video/Audio Files', extensions: ['mp4', 'mp3', 'm4a', 'wav', 'webm', 'mkv', 'mov'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths;
  }
  return [];
});

ipcMain.handle('get-downloaded-models', async () => {
  return getDownloadedModels();
});

ipcMain.handle('get-system-memory', async () => {
  return Math.round(os.totalmem() / (1024 * 1024 * 1024));
});

ipcMain.handle('download-model', async (event, modelName) => {
  if (!MODEL_REPO_MAP[modelName]) {
    return { success: false, error: `無効なモデル名: ${modelName}` };
  }

  const binaryPath = getBackendBinaryPath();
  if (!binaryPath || !fs.existsSync(binaryPath)) {
    return { success: false, error: 'バックエンドバイナリが見つかりません' };
  }

  // Kill any existing download
  if (modelDownloadProcess) {
    modelDownloadProcess.kill('SIGTERM');
    modelDownloadProcess = null;
  }

  return new Promise((resolve) => {
    const args = ['--download-model', modelName];
    const env = { ...process.env, PYTHONUNBUFFERED: '1' };

    modelDownloadProcess = spawn(binaryPath, args, { env });

    modelDownloadProcess.stdout.on('data', (data) => {
      const text = data.toString();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('model-download-progress', { message: text.trim() });
      }
    });

    modelDownloadProcess.stderr.on('data', (data) => {
      const text = data.toString();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('model-download-progress', { message: text.trim() });
      }
    });

    modelDownloadProcess.on('close', (code) => {
      modelDownloadProcess = null;
      if (code === 0) {
        resolve({ success: true });
      } else {
        resolve({ success: false, error: `ダウンロード失敗 (exit code: ${code})` });
      }
    });

    modelDownloadProcess.on('error', (error) => {
      modelDownloadProcess = null;
      resolve({ success: false, error: error.message });
    });
  });
});

ipcMain.handle('cancel-model-download', async () => {
  if (modelDownloadProcess) {
    modelDownloadProcess.kill('SIGTERM');
    modelDownloadProcess = null;
    return { success: true };
  }
  return { success: false, error: 'ダウンロード中ではありません' };
});

ipcMain.handle('start-processing', async (event, config) => {
  try {
    // 保存済みAPIキーをmainプロセス側で注入（rendererからは送らない）
    const savedSettings = loadSettings();
    if (!config.apiKey && savedSettings.apiKey) {
      config.apiKey = savedSettings.apiKey;
    }
    if (!config.geminiApiKey && savedSettings.geminiApiKey) {
      config.geminiApiKey = savedSettings.geminiApiKey;
    }

    const safeConfig = { ...config, apiKey: config.apiKey ? '[REDACTED]' : '', geminiApiKey: config.geminiApiKey ? '[REDACTED]' : '' };
    console.log('Starting processing with config:', safeConfig);

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
    if (!ffmpegPath) {
      return {
        success: false,
        error: 'ffmpegが見つかりません。ffmpegをインストールしてください。\nWindows: https://ffmpeg.org/download.html\nまたは: winget install ffmpeg'
      };
    }

    // Get deno path (optional, for YouTube JS extraction)
    const denoDirPath = getDenoDirPath();

    console.log('Backend binary:', path.basename(binaryPath));
    console.log('ffmpeg:', ffmpegPath ? path.basename(ffmpegPath) : 'not found');
    console.log('deno:', denoDirPath || 'not found (YouTube may use limited formats)');

    // Initialize ProcessManager with bundled binary
    processManager = new ProcessManager(binaryPath, ffmpegPath, denoDirPath);

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
      config.files || [],
      config.outputDir,
      config.language,
      config.model,
      config.keepVideo || false,
      config.engine || 'faster-whisper',
      config.apiKey || '',
      config.obsidianVault || '',
      config.obsidianFolder || '',
      config.diarize || false,
      config.summarize || false,
      config.summaryPrompt || '',
      config.summaryProvider || 'builtin',
      config.summaryModel || '',
      config.geminiApiKey || '',
      config.cookiesBrowser || ''
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
  const resolved = path.resolve(String(folderPath));

  // 絶対パスのみ許可
  if (!path.isAbsolute(resolved)) {
    console.error('Blocked open-folder: non-absolute path:', resolved);
    return;
  }

  // パスが存在しディレクトリであることを確認
  try {
    const stat = fs.statSync(resolved);
    if (!stat.isDirectory()) {
      console.error('Blocked open-folder: path is not a directory:', resolved);
      return;
    }
  } catch (err) {
    console.error('Blocked open-folder: path does not exist:', resolved);
    return;
  }

  const { shell } = require('electron');
  shell.openPath(resolved);
});

// Auto-update functions
function checkForUpdates() {
  // 全プラットフォーム共通: GitHub APIでリリースをチェック
  console.log('Checking for updates via GitHub API...');
  checkGitHubUpdate();
}

// GitHub APIで最新リリースをチェック
async function checkGitHubUpdate() {
  try {
    const https = require('https');
    const currentVersion = app.getVersion();

    const options = {
      hostname: 'api.github.com',
      path: '/repos/waqprime/tool-instagram-live-transcription/releases/latest',
      headers: {
        'User-Agent': 'TranscriptionTool'
      }
    };

    https.get(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const release = JSON.parse(data);
          const latestVersion = release.tag_name.replace('v', '');

          console.log(`Current version: ${currentVersion}, Latest version: ${latestVersion}`);

          // semver比較
          const compareSemver = (a, b) => {
            const pa = a.split('.').map(Number);
            const pb = b.split('.').map(Number);
            for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
              const na = pa[i] || 0;
              const nb = pb[i] || 0;
              if (na > nb) return 1;
              if (na < nb) return -1;
            }
            return 0;
          };

          if (compareSemver(latestVersion, currentVersion) > 0) {
            console.log(`Update available: ${latestVersion}`);
            if (mainWindow && !mainWindow.isDestroyed()) {
              const downloadPageUrl = 'https://waqprime.github.io/tool-instagram-live-transcription/download.html';
              mainWindow.webContents.send('update-available-portable', {
                version: latestVersion,
                downloadUrl: downloadPageUrl,
                releaseUrl: downloadPageUrl
              });
            }
          } else {
            console.log('App is up to date.');
          }
        } catch (err) {
          console.error('Error parsing release data:', err);
        }
      });
    }).on('error', (err) => {
      console.error('Error checking for updates:', err);
    });
  } catch (error) {
    console.error('Error in checkGitHubUpdate:', error);
  }
}

ipcMain.handle('install-update', () => {
  autoUpdater.quitAndInstall();
});

ipcMain.handle('open-download-page', (event, url) => {
  // Validate that the URL is from github.com or GitHub Pages
  try {
    const parsed = new URL(url);
    const allowed = parsed.hostname === 'github.com'
      || parsed.hostname.endsWith('.github.com')
      || parsed.hostname.endsWith('.github.io');
    if (!allowed) {
      console.error('Blocked open-download-page: non-GitHub URL:', url);
      return;
    }
  } catch (e) {
    console.error('Blocked open-download-page: invalid URL:', url);
    return;
  }

  const { shell } = require('electron');
  shell.openExternal(url);
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
