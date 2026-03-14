// State management
let urlCount = 1;
let fileCount = 0;
let selectedFiles = [];  // Store selected file paths
let outputDirectory = '';
let isProcessing = false;
let startTime = null;
let timerInterval = null;

// DOM Elements
const urlList = document.getElementById('url-list');
const fileList = document.getElementById('file-list');
const addUrlBtn = document.getElementById('add-url-btn');
const addFileBtn = document.getElementById('add-file-btn');
const selectDirBtn = document.getElementById('select-dir-btn');
const outputDirInput = document.getElementById('output-dir');
const languageSelect = document.getElementById('language-select');
const engineSelect = document.getElementById('engine-select');
const apiKeyInput = document.getElementById('api-key-input');
const toggleApiKeyBtn = document.getElementById('toggle-api-key-btn');
const modelSelect = document.getElementById('model-select');
const keepVideoCheckbox = document.getElementById('keep-video-checkbox');
const diarizeCheckbox = document.getElementById('diarize-checkbox');
const summarizeCheckbox = document.getElementById('summarize-checkbox');
const summaryProviderSection = document.getElementById('summary-provider-section');
const summaryProviderSelect = document.getElementById('summary-provider-select');
const summaryModelSection = document.getElementById('summary-model-section');
const summaryModelSelect = document.getElementById('summary-model-select');
const fetchModelsBtn = document.getElementById('fetch-models-btn');
const geminiApiKeySection = document.getElementById('gemini-api-key-section');
const geminiApiKeyInput = document.getElementById('gemini-api-key-input');
const summaryPromptSection = document.getElementById('summary-prompt-section');
const summaryPromptInput = document.getElementById('summary-prompt-input');
const obsidianEnabledCheckbox = document.getElementById('obsidian-enabled-checkbox');
const obsidianVaultSection = document.getElementById('obsidian-vault-section');
const obsidianVaultDirInput = document.getElementById('obsidian-vault-dir');
const selectVaultBtn = document.getElementById('select-vault-btn');
const obsidianSubfolderSection = document.getElementById('obsidian-subfolder-section');
const obsidianSubfolderInput = document.getElementById('obsidian-subfolder-input');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const openFolderBtn = document.getElementById('open-folder-btn');
const clearBtn = document.getElementById('clear-btn');
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const settingsCloseBtn = document.getElementById('settings-close-btn');
const settingsSaveBtn = document.getElementById('settings-save-btn');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const progressDetails = document.getElementById('progress-details');
const dropZone = document.getElementById('drop-zone');

// Supported file extensions for drag & drop
const SUPPORTED_EXTENSIONS = ['.mp4', '.mp3', '.m4a', '.wav', '.webm', '.mkv', '.mov'];

// Engine-specific model options
const ENGINE_MODELS = {
  'faster-whisper': [
    { value: 'large-v3-turbo', label: 'large-v3-turbo - 高速・高精度（推奨）', selected: true },
    { value: 'large-v3', label: 'large-v3 - 最高精度' },
    { value: 'large-v2', label: 'large-v2 - 高精度' },
    { value: 'medium', label: 'medium - バランス型' },
    { value: 'small', label: 'small - 軽量・高速' },
    { value: 'base', label: 'base - 軽量' },
    { value: 'tiny', label: 'tiny - 最速（精度は低め）' },
  ],
  'kotoba-whisper': [
    { value: 'kotoba-whisper-v2.0', label: 'kotoba-whisper-v2.0 - 日本語特化（推奨）', selected: true },
  ],
  'openai-api': [
    { value: 'gpt-4o-transcribe', label: 'gpt-4o-transcribe - 最高精度（推奨）', selected: true },
    { value: 'gpt-4o-mini-transcribe', label: 'gpt-4o-mini-transcribe - 高速・低コスト' },
    { value: 'whisper-1', label: 'whisper-1 - 従来モデル' },
  ],
};

// Summary provider model options
const SUMMARY_MODELS = {
  'builtin': [
    { value: 'gemini-2.5-flash-lite', label: 'gemini-2.5-flash-lite（APIキー不要・低精度）', selected: true },
  ],
  'openai': [
    { value: 'gpt-4o-mini', label: 'gpt-4o-mini（推奨）', selected: true },
    { value: 'gpt-4o', label: 'gpt-4o' },
  ],
  'gemini': [
    { value: 'gemini-2.5-flash', label: 'gemini-2.5-flash（推奨）', selected: true },
    { value: 'gemini-2.5-flash-lite', label: 'gemini-2.5-flash-lite（軽量・高速）' },
    { value: 'gemini-2.5-pro', label: 'gemini-2.5-pro（高精度）' },
  ],
};

// APIキー保存済みマーク + 削除ボタン追加
function _markKeySaved(inputEl, keyName) {
  inputEl.placeholder = '保存済み（変更する場合のみ入力）';
  inputEl.dataset.saved = 'true';

  // 既存の削除ボタンがあれば追加しない
  if (inputEl.parentElement.querySelector('.btn-delete-key')) return;

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'btn btn-secondary btn-delete-key';
  deleteBtn.textContent = '削除';
  deleteBtn.title = '保存済みAPIキーを削除';
  deleteBtn.style.marginLeft = '4px';
  deleteBtn.style.color = '#ff6b6b';
  deleteBtn.addEventListener('click', async () => {
    if (!confirm('保存済みのAPIキーを削除しますか？')) return;
    const settings = { [`_delete${keyName.charAt(0).toUpperCase() + keyName.slice(1)}`]: true };
    await window.electronAPI.saveSettings(settings);
    inputEl.placeholder = keyName === 'apiKey' ? 'sk-...' : 'AIza...';
    inputEl.dataset.saved = '';
    inputEl.value = '';
    deleteBtn.remove();
  });
  inputEl.parentElement.appendChild(deleteBtn);
}

// Initialize
async function init() {
  // Get default output directory based on OS (via IPC)
  const defaultOutputDir = await window.electronAPI.getDefaultOutputDir();
  outputDirectory = defaultOutputDir;
  outputDirInput.value = defaultOutputDir;

  // Add initial URL input
  addUrlInput();

  // Setup engine-related UI
  engineSelect.addEventListener('change', onEngineChange);
  toggleApiKeyBtn.addEventListener('click', toggleApiKeyVisibility);

  // Load settings from file
  const settings = await window.electronAPI.loadSettings();

  // Restore saved settings
  // APIキーは文字列ではなく保存済みフラグで管理
  if (settings._hasApiKey) {
    _markKeySaved(apiKeyInput, 'apiKey');
  }
  if (settings.diarize) {
    diarizeCheckbox.checked = true;
  }
  if (settings.summarize) {
    summarizeCheckbox.checked = true;
  }
  if (settings.summaryProvider) {
    summaryProviderSelect.value = settings.summaryProvider;
    populateSummaryModels(settings.summaryProvider);
    if (settings.summaryProvider === 'gemini') {
      geminiApiKeySection.style.display = '';
    }
  }
  if (settings._hasGeminiApiKey) {
    _markKeySaved(geminiApiKeyInput, 'geminiApiKey');
  }
  if (settings.summaryModel) {
    summaryModelSelect.value = settings.summaryModel;
  }
  if (settings.summaryPrompt) {
    summaryPromptInput.value = settings.summaryPrompt;
  }
  if (settings.obsidianVault) {
    obsidianVaultDirInput.value = settings.obsidianVault;
    obsidianEnabledCheckbox.checked = true;
    obsidianVaultSection.style.display = '';
    obsidianSubfolderSection.style.display = '';
  }
  if (settings.obsidianSubfolder) {
    obsidianSubfolderInput.value = settings.obsidianSubfolder;
  }
  if (settings.outputDir) {
    outputDirectory = settings.outputDir;
    outputDirInput.value = settings.outputDir;
  }
  if (settings.engine) {
    engineSelect.value = settings.engine;
  }
  if (settings.language) {
    languageSelect.value = settings.language;
  }

  // Setup summarize checkbox and provider handlers
  summarizeCheckbox.addEventListener('change', onSummarizeChange);
  summaryProviderSelect.addEventListener('change', onSummaryProviderChange);
  // fetchModelsBtn is kept in DOM but unused

  // Setup Obsidian checkbox handler
  obsidianEnabledCheckbox.addEventListener('change', onObsidianChange);
  selectVaultBtn.addEventListener('click', selectObsidianVault);

  // Initialize model options based on engine (after restoring engine setting)
  onEngineChange();

  // Restore model after onEngineChange populated options
  if (settings.model) {
    modelSelect.value = settings.model;
  }

  // Setup settings modal
  settingsBtn.addEventListener('click', openSettingsModal);
  settingsCloseBtn.addEventListener('click', closeSettingsModal);
  settingsSaveBtn.addEventListener('click', saveAndCloseSettings);
  settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) closeSettingsModal();
  });

  // Setup event listeners
  addUrlBtn.addEventListener('click', () => addUrlInput());
  addFileBtn.addEventListener('click', () => selectFiles());
  selectDirBtn.addEventListener('click', selectOutputDirectory);
  startBtn.addEventListener('click', startProcessing);
  stopBtn.addEventListener('click', stopProcessing);
  openFolderBtn.addEventListener('click', openOutputFolder);
  clearBtn.addEventListener('click', clearAll);

  // Setup drag & drop
  setupDragAndDrop();

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

  // Setup portable version update listener
  window.electronAPI.onUpdateAvailablePortable((info) => {
    const download = confirm(
      `新しいバージョン ${info.version} が利用可能です！\n\n` +
      `現在：ポータブル版\n` +
      `このバージョンでは自動アップデートができません。\n\n` +
      `「OK」を押すとダウンロードページを開きます。\n` +
      `新しいバージョンをダウンロードして、現在の実行ファイルを置き換えてください。`
    );

    if (download) {
      window.electronAPI.openDownloadPage(info.releaseUrl);
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
  input.placeholder = 'https://www.instagram.com/... / https://www.youtube.com/... / https://twitter.com/i/spaces/...';
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

    // Safety check: Ensure URL is a valid string and not an object
    if (url && typeof url === 'string' && !url.includes('[object')) {
      // Further validation: Check if it looks like a URL
      if (url.startsWith('http://') || url.startsWith('https://')) {
        urls.push(url);
        console.log('Valid URL added:', url);
      } else {
        console.warn('Invalid URL format (missing http/https):', url);
      }
    } else if (url) {
      console.error('Invalid URL detected (not a string or contains object):', url);
    }
  });

  return urls;
}

// Start processing
async function startProcessing() {
  const urls = getUrls();
  const files = selectedFiles;

  if (urls.length === 0 && files.length === 0) {
    alert('URLまたはファイルを追加してください');
    return;
  }

  if (!outputDirectory) {
    alert('保存先を選択してください');
    return;
  }

  const engine = engineSelect.value;
  const apiKey = apiKeyInput.value.trim();

  const hasApiKey = apiKey || apiKeyInput.dataset.saved === 'true';
  const hasGeminiApiKey = geminiApiKeyInput.value.trim() || geminiApiKeyInput.dataset.saved === 'true';

  // Validate API key when OpenAI API engine is selected
  if (engine === 'openai-api' && !hasApiKey) {
    alert('OpenAI API エンジンを使用するにはAPIキーを入力してください');
    apiKeyInput.focus();
    return;
  }

  // Validate API key when summarize with OpenAI is enabled
  if (summarizeCheckbox.checked && summaryProviderSelect.value === 'openai' && !hasApiKey) {
    alert('OpenAIでの内容要約を使用するにはAPIキーを入力してください');
    apiKeyInput.focus();
    return;
  }

  // Validate Gemini API key when summarize with Gemini is enabled
  if (summarizeCheckbox.checked && summaryProviderSelect.value === 'gemini' && !hasGeminiApiKey) {
    alert('Geminiでの内容要約を使用するにはGemini APIキーを入力してください');
    geminiApiKeyInput.focus();
    return;
  }

  // Save settings to file
  const obsidianVault = obsidianVaultDirInput.value.trim();
  const obsidianSubfolder = obsidianSubfolderInput.value.trim();

  // 新しいキーが入力された場合のみ保存（空欄なら保存済みキーを維持）
  const settingsToSave = {
    apiKey: apiKey || undefined,  // 空なら保存済みキーがmain側で維持される
    _keepApiKey: !apiKey && apiKeyInput.dataset.saved === 'true',
    diarize: diarizeCheckbox.checked,
    summarize: summarizeCheckbox.checked,
    summaryProvider: summaryProviderSelect.value,
    summaryModel: summaryModelSelect.value,
    summaryPrompt: summaryPromptInput.value.trim() || undefined,
    geminiApiKey: geminiApiKeyInput.value.trim() || undefined,
    _keepGeminiApiKey: !geminiApiKeyInput.value.trim() && geminiApiKeyInput.dataset.saved === 'true',
    obsidianVault: obsidianEnabledCheckbox.checked ? obsidianVault : undefined,
    obsidianSubfolder: obsidianEnabledCheckbox.checked ? obsidianSubfolder : undefined,
    outputDir: outputDirectory,
    engine: engine,
    model: modelSelect.value,
    language: languageSelect.value,
  };
  window.electronAPI.saveSettings(settingsToSave);

  // Update UI
  isProcessing = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  openFolderBtn.disabled = true;
  clearBtn.disabled = true;
  addUrlBtn.disabled = true;
  addFileBtn.disabled = true;
  selectDirBtn.disabled = true;
  languageSelect.disabled = true;
  engineSelect.disabled = true;
  apiKeyInput.disabled = true;
  toggleApiKeyBtn.disabled = true;
  modelSelect.disabled = true;
  keepVideoCheckbox.disabled = true;
  diarizeCheckbox.disabled = true;
  summarizeCheckbox.disabled = true;
  summaryProviderSelect.disabled = true;
  summaryModelSelect.disabled = true;
  summaryPromptInput.disabled = true;
  obsidianEnabledCheckbox.disabled = true;
  selectVaultBtn.disabled = true;
  obsidianSubfolderInput.disabled = true;

  // Disable all URL inputs
  const inputs = urlList.querySelectorAll('input');
  inputs.forEach(input => input.disabled = true);

  // Disable file remove buttons
  const fileRemoveBtns = fileList.querySelectorAll('.btn-remove-small');
  fileRemoveBtns.forEach(btn => btn.disabled = true);

  // Reset progress and start timer
  startTime = Date.now();
  const totalItems = urls.length + files.length;
  updateProgress(0, '処理を開始しています...', `${totalItems}件のアイテムを処理します`);
  startTimer();

  // Start processing
  const config = {
    urls: urls,
    files: files,
    outputDir: outputDirectory,
    language: languageSelect.value,
    model: modelSelect.value,
    keepVideo: keepVideoCheckbox.checked,
    engine: engine,
    apiKey: apiKey,
    diarize: diarizeCheckbox.checked,
    summarize: summarizeCheckbox.checked,
    summaryProvider: summarizeCheckbox.checked ? summaryProviderSelect.value : 'builtin',
    summaryModel: summarizeCheckbox.checked ? summaryModelSelect.value : '',
    summaryPrompt: summarizeCheckbox.checked ? summaryPromptInput.value.trim() : '',
    geminiApiKey: summarizeCheckbox.checked ? geminiApiKeyInput.value.trim() : '',
    obsidianVault: obsidianEnabledCheckbox.checked ? obsidianVault : '',
    obsidianFolder: obsidianEnabledCheckbox.checked ? obsidianSubfolder : '',
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
    clearBtn.disabled = false;
    addUrlBtn.disabled = false;
    addFileBtn.disabled = false;
    selectDirBtn.disabled = false;
    languageSelect.disabled = false;
    engineSelect.disabled = false;
    apiKeyInput.disabled = false;
    toggleApiKeyBtn.disabled = false;
    modelSelect.disabled = false;
    keepVideoCheckbox.disabled = false;
    diarizeCheckbox.disabled = false;
    summarizeCheckbox.disabled = false;
    summaryProviderSelect.disabled = false;
    summaryModelSelect.disabled = false;
    summaryPromptInput.disabled = false;
    obsidianEnabledCheckbox.disabled = false;
    selectVaultBtn.disabled = false;
    obsidianSubfolderInput.disabled = false;

    inputs.forEach(input => input.disabled = false);

    const fileRemoveBtns = fileList.querySelectorAll('.btn-remove-small');
    fileRemoveBtns.forEach(btn => btn.disabled = false);
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
  const type = log.type || 'info';
  const message = log.message || log;

  // Log to console for debugging (open DevTools with F12)
  console.log(`[${type}]`, message);

  // Show errors prominently
  if (type === 'error') {
    updateProgress(null, '⚠️ エラー発生', message);
    return;
  }

  // Extract important progress info from log messages
  // 初期化メッセージ（「有効」「対応」含む）はステータス更新しない
  if (message.includes(': 有効') || message.includes('対応:') || message.includes('エンジン:')) {
    // 初期化ログはスキップ
  } else if (message.includes('ダウンロード')) {
    updateProgress(null, '動画をダウンロード中...', message);
  } else if (message.includes('文字起こし') || message.includes('Whisper')) {
    updateProgress(null, '文字起こし中...', message);
  } else if (message.includes('音声') || message.includes('MP3')) {
    updateProgress(null, 'MP3を抽出中...', message);
  } else if (message.includes('話者分離')) {
    updateProgress(null, '話者分離中...', message);
  } else if (message.includes('【追加ステップ】内容要約') || message.includes('要約を生成中')) {
    updateProgress(null, '内容要約中...', message);
  } else if (message.includes('完了')) {
    // Keep details if available
    updateProgress(null, null, message);
  } else if (message.includes('実行') || message.includes('バイナリ') || message.includes('引数')) {
    // Show detailed execution info
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

// File selection and management
async function selectFiles() {
  const filePaths = await window.electronAPI.selectFiles();

  if (filePaths && filePaths.length > 0) {
    filePaths.forEach(filePath => {
      if (!selectedFiles.includes(filePath)) {
        selectedFiles.push(filePath);
        addFileItem(filePath);
      }
    });
  }
}

// Add file item to the list
function addFileItem(filePath) {
  const fileItem = document.createElement('div');
  fileItem.className = 'file-item';
  fileItem.dataset.path = filePath;

  // Extract filename from path
  const fileName = filePath.split(/[\\/]/).pop();

  const fileInfo = document.createElement('div');
  fileInfo.className = 'file-info';

  const fileNameSpan = document.createElement('span');
  fileNameSpan.className = 'file-name';
  fileNameSpan.textContent = fileName;

  const filePathSpan = document.createElement('span');
  filePathSpan.className = 'file-path';
  filePathSpan.textContent = filePath;

  fileInfo.appendChild(fileNameSpan);
  fileInfo.appendChild(filePathSpan);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'btn btn-remove-small';
  removeBtn.textContent = '×';
  removeBtn.addEventListener('click', () => removeFileItem(fileItem, filePath));

  fileItem.appendChild(fileInfo);
  fileItem.appendChild(removeBtn);
  fileList.appendChild(fileItem);

  // Hide drop zone placeholder when files exist
  dropZone.classList.add('has-files');
}

// Remove file item
function removeFileItem(fileItem, filePath) {
  const index = selectedFiles.indexOf(filePath);
  if (index > -1) {
    selectedFiles.splice(index, 1);
  }
  fileItem.remove();

  // Show drop zone placeholder when no files remain
  if (selectedFiles.length === 0) {
    dropZone.classList.remove('has-files');
  }
}

// Engine change handler
function onEngineChange() {
  const engine = engineSelect.value;

  // Update model dropdown options
  const models = ENGINE_MODELS[engine] || [];
  modelSelect.innerHTML = '';
  models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.value;
    opt.textContent = m.label;
    if (m.selected) opt.selected = true;
    modelSelect.appendChild(opt);
  });

  // Disable model select when only one model available
  modelSelect.disabled = models.length <= 1;
}

// Toggle API key visibility
function toggleApiKeyVisibility() {
  if (apiKeyInput.type === 'password') {
    apiKeyInput.type = 'text';
    toggleApiKeyBtn.textContent = '非表示';
  } else {
    apiKeyInput.type = 'password';
    toggleApiKeyBtn.textContent = '表示';
  }
}

// Summarize checkbox change handler
function onSummarizeChange() {
  // No-op: detail settings are always visible in the settings modal
}

// Summary provider change handler
function onSummaryProviderChange() {
  const provider = summaryProviderSelect.value;
  geminiApiKeySection.style.display = provider === 'gemini' ? '' : 'none';
  summaryModelSelect.disabled = provider === 'builtin';
  populateSummaryModels(provider);
}

// Populate summary model select based on provider
function populateSummaryModels(provider) {
  const models = SUMMARY_MODELS[provider] || [];
  summaryModelSelect.innerHTML = '';
  models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.value;
    opt.textContent = m.label;
    if (m.selected) opt.selected = true;
    summaryModelSelect.appendChild(opt);
  });
}

// Obsidian checkbox change handler
function onObsidianChange() {
  const enabled = obsidianEnabledCheckbox.checked;
  obsidianVaultSection.style.display = enabled ? '' : 'none';
  obsidianSubfolderSection.style.display = enabled ? '' : 'none';
}

// Select Obsidian Vault directory
async function selectObsidianVault() {
  const dir = await window.electronAPI.selectDirectory();
  if (dir) {
    obsidianVaultDirInput.value = dir;
  }
}

// Settings modal functions
function openSettingsModal() {
  settingsModal.style.display = '';
}

function closeSettingsModal() {
  settingsModal.style.display = 'none';
}

async function saveAndCloseSettings() {
  const newApiKey = apiKeyInput.value.trim();
  const newGeminiKey = geminiApiKeyInput.value.trim();
  const settingsToSave = {
    apiKey: newApiKey || undefined,
    _keepApiKey: !newApiKey && apiKeyInput.dataset.saved === 'true',
    diarize: diarizeCheckbox.checked,
    summarize: summarizeCheckbox.checked,
    summaryProvider: summaryProviderSelect.value,
    summaryModel: summaryModelSelect.value,
    summaryPrompt: summaryPromptInput.value.trim() || undefined,
    geminiApiKey: newGeminiKey || undefined,
    _keepGeminiApiKey: !newGeminiKey && geminiApiKeyInput.dataset.saved === 'true',
    obsidianVault: obsidianEnabledCheckbox.checked ? obsidianVaultDirInput.value.trim() : undefined,
    obsidianSubfolder: obsidianEnabledCheckbox.checked ? obsidianSubfolderInput.value.trim() : undefined,
    outputDir: outputDirectory,
    engine: engineSelect.value,
    model: modelSelect.value,
    language: languageSelect.value,
  };
  await window.electronAPI.saveSettings(settingsToSave);
  closeSettingsModal();
}

// Clear all inputs, files, and progress
function clearAll() {
  if (isProcessing) return;

  // Clear URL list and add one empty input
  urlList.innerHTML = '';
  urlCount = 1;
  addUrlInput();

  // Clear selected files
  selectedFiles = [];
  // Remove all file items (keep drop zone)
  const fileItems = fileList.querySelectorAll('.file-item');
  fileItems.forEach(item => item.remove());

  // Show drop zone placeholder
  dropZone.classList.remove('has-files');

  // Reset progress
  updateProgress(0, '待機中...', '');

  // Reset open folder button
  openFolderBtn.disabled = true;
}

// Setup drag & drop for file section
function setupDragAndDrop() {
  const fileSection = fileList.closest('section');

  // Prevent default browser behavior for drag & drop on the whole window
  window.addEventListener('dragover', (e) => {
    e.preventDefault();
  });
  window.addEventListener('drop', (e) => {
    e.preventDefault();
  });

  // Drag over the file section
  fileSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (!isProcessing) {
      dropZone.classList.add('drag-over');
    }
  });

  fileSection.addEventListener('dragleave', (e) => {
    // Only remove highlight when leaving the section entirely
    if (!fileSection.contains(e.relatedTarget)) {
      dropZone.classList.remove('drag-over');
    }
  });

  fileSection.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    if (isProcessing) return;

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!SUPPORTED_EXTENSIONS.includes(ext)) continue;

      const filePath = file.path;
      if (!filePath || selectedFiles.includes(filePath)) continue;

      selectedFiles.push(filePath);
      addFileItem(filePath);
    }

    // Hide drop zone placeholder if files exist
    if (selectedFiles.length > 0) {
      dropZone.classList.add('has-files');
    }
  });
}

// Cleanup on unload
window.addEventListener('beforeunload', () => {
  if (window.electronAPI && window.electronAPI.removeAllListeners) {
    window.electronAPI.removeAllListeners('processing-log');
    window.electronAPI.removeAllListeners('processing-progress');
  }
});
