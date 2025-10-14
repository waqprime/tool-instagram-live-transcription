const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class ProcessManager {
  constructor(pythonPath) {
    this.pythonPath = pythonPath || 'python3';
    this.currentProcess = null;
    this.logCallback = null;
    this.progressCallback = null;
    this.stopped = false;
  }

  onLog(callback) {
    this.logCallback = callback;
  }

  onProgress(callback) {
    this.progressCallback = callback;
  }

  log(type, message) {
    console.log(`[${type}] ${message}`);
    if (this.logCallback) {
      this.logCallback({ type, message });
    }
  }

  updateProgress(percent, status, details) {
    if (this.progressCallback) {
      this.progressCallback({ percent, status, details });
    }
  }

  async processUrls(urls, outputDir, language, model) {
    this.stopped = false;
    const results = [];
    const totalUrls = urls.length;

    // Ensure output directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    for (let i = 0; i < urls.length; i++) {
      if (this.stopped) {
        this.log('warning', '処理が中断されました');
        break;
      }

      const url = urls[i];
      const urlNum = i + 1;

      // Create dedicated folder for this URL
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const folderName = `video_${urlNum}_${timestamp}`;
      const urlOutputDir = path.join(outputDir, folderName);

      if (!fs.existsSync(urlOutputDir)) {
        fs.mkdirSync(urlOutputDir, { recursive: true });
      }

      this.log('info', `[${urlNum}/${totalUrls}] 処理開始: ${url}`);
      this.log('info', `[${urlNum}/${totalUrls}] 保存先: ${folderName}/`);
      this.updateProgress((i / totalUrls) * 100, `URL ${urlNum}/${totalUrls} を処理中...`);

      try {
        // Step 1: Download video
        this.log('info', `[${urlNum}/${totalUrls}] ダウンロード中...`);
        const videoPath = await this.downloadVideo(url, urlOutputDir, `video_${urlNum}`);

        if (!videoPath) {
          this.log('error', `[${urlNum}/${totalUrls}] ダウンロード失敗`);
          results.push({ url, success: false, error: 'Download failed' });
          continue;
        }

        // Step 2: Extract audio
        this.log('info', `[${urlNum}/${totalUrls}] 音声抽出中...`);
        const audioPath = await this.extractAudio(videoPath);

        if (!audioPath) {
          this.log('error', `[${urlNum}/${totalUrls}] 音声抽出失敗`);
          results.push({ url, success: false, error: 'Audio extraction failed' });
          this.cleanupFile(videoPath);
          continue;
        }

        // Check audio file size and warn if large
        const stats = fs.statSync(audioPath);
        const fileSizeMB = stats.size / (1024 * 1024);
        const durationMinutes = Math.round(fileSizeMB / 2.3); // Rough estimate: ~2.3MB per minute

        if (fileSizeMB > 50) {
          // Large file warning
          const recommendedModel = fileSizeMB > 200 ? 'tiny' : fileSizeMB > 100 ? 'base' : 'small';

          this.log('warning', `⚠️ 大きな音声ファイルです: ${fileSizeMB.toFixed(1)}MB (約${durationMinutes}分)`);

          if (model === 'large' || model === 'medium') {
            this.log('warning', `現在のモデル「${model}」は処理に時間がかかります`);
            this.log('warning', `推奨モデル: ${recommendedModel} (より高速)`);
            this.updateProgress(null, '⚠️ 大きなファイルです',
              `${fileSizeMB.toFixed(1)}MB (約${durationMinutes}分) - 推奨モデル: ${recommendedModel}`);
          }
        }

        // Step 3: Transcribe audio
        this.log('info', `[${urlNum}/${totalUrls}] 文字起こし中（Whisper ${model}モデル）...`);
        this.log('warning', `[${urlNum}/${totalUrls}] この処理には数分かかる場合があります`);

        const transcriptPath = await this.transcribeAudio(audioPath, language, model, urlOutputDir);

        if (!transcriptPath) {
          this.log('error', `[${urlNum}/${totalUrls}] 文字起こし失敗`);
          results.push({ url, success: false, error: 'Transcription failed' });
        } else {
          this.log('success', `[${urlNum}/${totalUrls}] 完了: ${transcriptPath}`);
          results.push({ url, success: true, output: transcriptPath });
        }

        // Cleanup temporary video file
        this.cleanupFile(videoPath);

      } catch (error) {
        this.log('error', `[${urlNum}/${totalUrls}] エラー: ${error.message}`);
        results.push({ url, success: false, error: error.message });
      }

      // Update progress
      this.updateProgress(((i + 1) / totalUrls) * 100, `${urlNum}/${totalUrls} 完了`);
    }

    return results;
  }

  async downloadVideo(url, outputDir, filename) {
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(__dirname, '..', '..', 'downloader.py');
      const outputTemplate = path.join(outputDir, filename);

      const args = [scriptPath, url, '-o', outputDir, '-n', filename];

      this.currentProcess = spawn(this.pythonPath, args);

      let outputData = '';
      let errorData = '';

      this.currentProcess.stdout.on('data', (data) => {
        const text = data.toString();
        outputData += text;
        this.log('debug', text.trim());
      });

      this.currentProcess.stderr.on('data', (data) => {
        const text = data.toString();
        errorData += text;
        this.log('debug', text.trim());
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        if (code === 0) {
          // Find the downloaded file
          const extensions = ['mp4', 'webm', 'mkv', 'm4a'];
          for (const ext of extensions) {
            const filepath = path.join(outputDir, `${filename}.${ext}`);
            if (fs.existsSync(filepath)) {
              resolve(filepath);
              return;
            }
          }
          reject(new Error('Downloaded file not found'));
        } else {
          reject(new Error(`Download failed with code ${code}`));
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;
        reject(error);
      });
    });
  }

  async extractAudio(videoPath) {
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(__dirname, '..', '..', 'audio_converter.py');
      const audioPath = videoPath.replace(/\.[^.]+$/, '.mp3');

      const args = [scriptPath, videoPath, '-o', audioPath];

      this.currentProcess = spawn(this.pythonPath, args);

      this.currentProcess.stdout.on('data', (data) => {
        this.log('debug', data.toString().trim());
      });

      this.currentProcess.stderr.on('data', (data) => {
        this.log('debug', data.toString().trim());
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        if (code === 0 && fs.existsSync(audioPath)) {
          resolve(audioPath);
        } else {
          reject(new Error(`Audio extraction failed with code ${code}`));
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;
        reject(error);
      });
    });
  }

  async transcribeAudio(audioPath, language, model, outputDir) {
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(__dirname, '..', '..', 'transcriber.py');

      const args = [
        scriptPath,
        audioPath,
        '-m', model,
        '-l', language,
        '-o', outputDir
      ];

      this.currentProcess = spawn(this.pythonPath, args);

      let lastOutput = '';
      let isDownloadingModel = false;
      let isTranscribing = false;

      this.currentProcess.stdout.on('data', (data) => {
        const text = data.toString().trim();
        lastOutput = text;

        if (text.includes('Whisperモデルを読み込み中')) {
          isDownloadingModel = true;
          this.updateProgress(null, '文字起こし準備中...', 'Whisperモデルをダウンロードしています');
        } else if (text.includes('文字起こし中')) {
          isDownloadingModel = false;
          isTranscribing = true;
          this.updateProgress(null, '文字起こし実行中...', '音声を解析しています');
        } else if (text.includes('完了')) {
          this.updateProgress(null, '✓ 文字起こし完了', text);
        }

        this.log('info', text);
      });

      this.currentProcess.stderr.on('data', (data) => {
        const text = data.toString().trim();

        // Whisper model download progress (appears in stderr)
        if (text.includes('%|') && text.includes('/')) {
          // Parse progress like "45%|████▌| 1.29G/2.88G"
          const match = text.match(/(\d+)%.*?(\d+\.?\d*[MGk]?)\/(\d+\.?\d*[MGk]?)/);
          if (match) {
            const percent = parseInt(match[1]);
            const current = match[2];
            const total = match[3];

            if (isDownloadingModel) {
              this.updateProgress(percent, `Whisperモデルダウンロード中: ${percent}%`, `${current} / ${total}`);
            } else {
              // During transcription, show partial progress
              this.updateProgress(null, '文字起こし実行中...', text.substring(0, 100));
            }
          }
        }

        // Log to console for debugging
        if (text) {
          this.log('debug', text);
        }
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        if (code === 0) {
          // Find the transcript file
          const baseName = path.basename(audioPath, '.mp3');
          const transcriptPath = path.join(outputDir, `${baseName}_transcript.txt`);

          if (fs.existsSync(transcriptPath)) {
            resolve(transcriptPath);
          } else {
            reject(new Error('Transcript file not found'));
          }
        } else {
          reject(new Error(`Transcription failed with code ${code}`));
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;
        reject(error);
      });
    });
  }

  cleanupFile(filepath) {
    try {
      if (fs.existsSync(filepath)) {
        fs.unlinkSync(filepath);
        this.log('debug', `一時ファイル削除: ${filepath}`);
      }
    } catch (error) {
      this.log('warning', `ファイル削除エラー: ${error.message}`);
    }
  }

  stop() {
    this.stopped = true;
    if (this.currentProcess) {
      this.currentProcess.kill('SIGTERM');
      this.currentProcess = null;
      this.log('warning', '現在の処理を停止しました');
    }
  }

  cleanup() {
    this.stop();
  }
}

module.exports = { ProcessManager };
