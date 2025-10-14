// State management
let urlCount = 1;
let outputDirectory = '';
let isProcessing = false;
let startTime = null;
let timerInterval = null;

// DOM Elements
const urlList = document.getElementById('url-list');
const addUrlBtn = document.getElementById('add-url-btn');
const selectDirBtn = document.getElementById('select-dir-btn');
const outputDirInput = document.getElementById('output-dir');
const languageSelect = document.getElementById('language-select');
const modelSelect = document.getElementById('model-select');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const openFolderBtn = document.getElementById('open-folder-btn');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const progressDetails = document.getElementById('progress-details');

// Initialize
function init() {
  // Set default output directory to project's output folder
  const defaultOutputDir = 'output';
  outputDirectory = defaultOutputDir;
  outputDirInput.value = defaultOutputDir;

  // Add initial URL input
  addUrlInput();

  // Setup event listeners
  addUrlBtn.addEventListener('click', addUrlInput);
  selectDirBtn.addEventListener('click', selectOutputDirectory);
  startBtn.addEventListener('click', startProcessing);
  stopBtn.addEventListener('click', stopProcessing);
  openFolderBtn.addEventListener('click', openOutputFolder);

  // Setup IPC listeners
  window.electronAPI.onProcessingLog(handleLog);
  window.electronAPI.onProcessingProgress(handleProgress);

  // Setup auto-update listeners
  window.electronAPI.onUpdateAvailable((info) => {
    updateProgress(null, `🔄 新しいバージョン ${info.version} をダウンロード中...`, 'バックグラウンドでダウンロードしています');
  });

  window.electronAPI.onUpdateProgress((progressObj) => {
    const percent = progressObj.percent || 0;
    updateProgress(percent, `🔄 アップデートダウンロード中: ${percent.toFixed(1)}%`, `${progressObj.transferred}/${progressObj.total} bytes`);
  });

  window.electronAPI.onUpdateDownloaded((info) => {
    const installNow = confirm(`新しいバージョン ${info.version} がダウンロードされました。\n\n今すぐインストールして再起動しますか？\n\nキャンセルすると、次回起動時にインストールされます。`);
    if (installNow) {
      window.electronAPI.installUpdate();
    }
  });
}

// Add URL input row
function addUrlInput(url = '') {
  const row = document.createElement('div');
  row.className = 'url-row';
  row.dataset.urlId = urlCount++;

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'glass-input';
  input.placeholder = 'https://www.instagram.com/reel/...';
  input.value = url;

  const removeBtn = document.createElement('button');
  removeBtn.className = 'btn btn-remove';
  removeBtn.innerHTML = '<span class="btn-icon">×</span>';
  removeBtn.onclick = () => removeUrlInput(row);

  row.appendChild(input);
  row.appendChild(removeBtn);
  urlList.appendChild(row);
}

// Remove URL input row
function removeUrlInput(row) {
  if (urlList.children.length > 1) {
    row.remove();
  } else {
    alert('最低1つのURL入力欄が必要です');
  }
}

// Select output directory
async function selectOutputDirectory() {
  const dir = await window.electronAPI.selectDirectory();
  if (dir) {
    outputDirectory = dir;
    outputDirInput.value = dir;
  }
}

// Get all URLs from inputs
function getUrls() {
  const inputs = urlList.querySelectorAll('input');
  const urls = [];

  inputs.forEach(input => {
    const url = input.value.trim();
    if (url) {
      urls.push(url);
    }
  });

  return urls;
}

// Start processing
async function startProcessing() {
  const urls = getUrls();

  if (urls.length === 0) {
    alert('URLを入力してください');
    return;
  }

  if (!outputDirectory) {
    alert('保存先を選択してください');
    return;
  }

  // Update UI
  isProcessing = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  openFolderBtn.disabled = true;
  addUrlBtn.disabled = true;
  selectDirBtn.disabled = true;
  languageSelect.disabled = true;
  modelSelect.disabled = true;

  // Disable all URL inputs
  const inputs = urlList.querySelectorAll('input');
  inputs.forEach(input => input.disabled = true);

  // Reset progress and start timer
  startTime = Date.now();
  updateProgress(0, '処理を開始しています...', `${urls.length}件のURLを処理します`);
  startTimer();

  // Start processing
  const config = {
    urls: urls,
    outputDir: outputDirectory,
    language: languageSelect.value,
    model: modelSelect.value
  };

  try {
    const result = await window.electronAPI.startProcessing(config);

    if (result.success) {
      updateProgress(100, '✓ 完了！', 'すべての処理が完了しました');
      openFolderBtn.disabled = false;
    } else {
      updateProgress(0, '✗ エラー', result.error || '処理に失敗しました');
    }
  } catch (error) {
    updateProgress(0, '✗ エラー', error.message);
  } finally {
    // Stop timer
    stopTimer();

    // Re-enable UI
    isProcessing = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    addUrlBtn.disabled = false;
    selectDirBtn.disabled = false;
    languageSelect.disabled = false;
    modelSelect.disabled = false;

    inputs.forEach(input => input.disabled = false);
  }
}

// Timer functions
function startTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }

  timerInterval = setInterval(() => {
    if (startTime) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      const timeStr = `経過時間: ${minutes}分${seconds}秒`;

      // Update details if not already set by progress handler
      const currentDetails = progressDetails.textContent;
      if (!currentDetails || currentDetails.includes('経過時間')) {
        progressDetails.textContent = timeStr;
      }
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

// Stop processing
async function stopProcessing() {
  const result = await window.electronAPI.stopProcessing();

  if (result.success) {
    updateProgress(0, '中断しました', '処理を停止しました');
  }
}

// Open output folder
function openOutputFolder() {
  if (outputDirectory) {
    window.electronAPI.openFolder(outputDirectory);
  }
}

// Handle log messages from backend
function handleLog(log) {
  const message = log.message || log;
  // Extract important progress info from log messages
  if (message.includes('ダウンロード')) {
    updateProgress(null, '動画をダウンロード中...', message);
  } else if (message.includes('音声') || message.includes('MP3')) {
    updateProgress(null, 'MP3を抽出中...', message);
  } else if (message.includes('文字起こし') || message.includes('Whisper')) {
    updateProgress(null, '文字起こし中...', message);
  } else if (message.includes('完了')) {
    // Keep details if available
    updateProgress(null, null, message);
  }
}

// Handle progress updates
function handleProgress(progress) {
  const percent = progress.percent || 0;
  const status = progress.status || '処理中...';
  const details = progress.details || '';
  updateProgress(percent, status, details);
}

// Update progress bar
function updateProgress(percent, status, details) {
  if (percent !== null && percent !== undefined) {
    progressFill.style.width = `${percent}%`;
  }

  if (status) {
    progressText.textContent = status;
  }

  if (details !== undefined) {
    progressDetails.textContent = details;
  }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Cleanup on unload
window.addEventListener('beforeunload', () => {
  if (window.electronAPI && window.electronAPI.removeAllListeners) {
    window.electronAPI.removeAllListeners('processing-log');
    window.electronAPI.removeAllListeners('processing-progress');
  }
});
