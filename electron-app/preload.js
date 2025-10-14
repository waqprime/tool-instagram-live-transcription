const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Directory selection
  selectDirectory: () => ipcRenderer.invoke('select-directory'),

  // Processing control
  startProcessing: (config) => ipcRenderer.invoke('start-processing', config),
  stopProcessing: () => ipcRenderer.invoke('stop-processing'),

  // Open folder in file explorer
  openFolder: (path) => ipcRenderer.invoke('open-folder', path),

  // Event listeners
  onProcessingLog: (callback) => {
    ipcRenderer.on('processing-log', (event, log) => callback(log));
  },

  onProcessingProgress: (callback) => {
    ipcRenderer.on('processing-progress', (event, progress) => callback(progress));
  },

  // Auto-update listeners
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', (event, info) => callback(info));
  },

  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update-downloaded', (event, info) => callback(info));
  },

  onUpdateProgress: (callback) => {
    ipcRenderer.on('update-progress', (event, progress) => callback(progress));
  },

  installUpdate: () => ipcRenderer.invoke('install-update'),

  // Remove listeners (for cleanup)
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});
