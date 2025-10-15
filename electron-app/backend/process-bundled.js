const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class ProcessManager {
  constructor(binaryPath, ffmpegPath) {
    this.binaryPath = binaryPath;
    this.ffmpegPath = ffmpegPath;
    this.currentProcess = null;
    this.logCallback = null;
    this.progressCallback = null;
    this.stopped = false;

    console.log('ProcessManager initialized (Bundled mode):');
    console.log('  Backend binary:', this.binaryPath);
    console.log('  ffmpeg binary:', this.ffmpegPath);
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
        // Run the bundled binary with URL
        const result = await this.processSingleUrl(url, urlOutputDir, language, model, urlNum, totalUrls);

        if (result.success) {
          this.log('success', `[${urlNum}/${totalUrls}] 完了`);
          results.push({ url, success: true, output: result.output });
        } else {
          this.log('error', `[${urlNum}/${totalUrls}] 失敗: ${result.error}`);
          results.push({ url, success: false, error: result.error });
        }

      } catch (error) {
        this.log('error', `[${urlNum}/${totalUrls}] エラー: ${error.message}`);
        results.push({ url, success: false, error: error.message });
      }

      // Update progress
      this.updateProgress(((i + 1) / totalUrls) * 100, `${urlNum}/${totalUrls} 完了`);
    }

    return results;
  }

  async processSingleUrl(url, outputDir, language, model, urlNum, totalUrls) {
    return new Promise((resolve, reject) => {
      // Verify binary exists
      if (!fs.existsSync(this.binaryPath)) {
        const error = `Backend binary not found: ${this.binaryPath}`;
        this.log('error', error);
        reject(new Error(error));
        return;
      }

      const args = [
        '--url', url,
        '--model', model,
        '--language', language,
        '--output-dir', outputDir
      ];

      // Set ffmpeg path as environment variable
      const env = { ...process.env };
      if (this.ffmpegPath) {
        env.FFMPEG_BINARY = this.ffmpegPath;
        this.log('info', `Using ffmpeg: ${this.ffmpegPath}`);
      }

      this.log('info', `[${urlNum}/${totalUrls}] バイナリ実行: ${this.binaryPath}`);
      this.log('info', `[${urlNum}/${totalUrls}] 引数: ${args.join(' ')}`);
      this.log('info', `[${urlNum}/${totalUrls}] 出力先: ${outputDir}`);

      this.currentProcess = spawn(this.binaryPath, args, { env });

      let outputData = '';
      let errorData = '';
      let lastProgressUpdate = Date.now();

      this.currentProcess.stdout.on('data', (data) => {
        const text = data.toString();
        outputData += text;

        // Parse progress messages
        const lines = text.split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;

          // Log important messages
          if (line.includes('ステップ') || line.includes('処理') || line.includes('✓') || line.includes('✗')) {
            this.log('info', line.trim());
          }

          // Update progress for long operations
          const now = Date.now();
          if (now - lastProgressUpdate > 2000) {
            this.updateProgress(null, `処理中: URL ${urlNum}/${totalUrls}`, line.substring(0, 100));
            lastProgressUpdate = now;
          }
        }
      });

      this.currentProcess.stderr.on('data', (data) => {
        const text = data.toString();
        errorData += text;

        // Log all stderr output for debugging
        const lines = text.split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;

          // Log as error or warning based on content
          if (line.includes('error') || line.includes('Error') || line.includes('ERROR') || line.includes('Exception') || line.includes('Traceback')) {
            this.log('error', `STDERR: ${line.trim()}`);
          } else if (line.includes('warning') || line.includes('Warning') || line.includes('WARN')) {
            this.log('warning', `STDERR: ${line.trim()}`);
          } else {
            // Log all other stderr as info for debugging
            this.log('debug', `STDERR: ${line.trim()}`);
          }
        }
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        if (code === 0) {
          // Find the output files
          const mp3Files = fs.readdirSync(outputDir).filter(f => f.endsWith('.mp3'));
          const transcriptFiles = fs.readdirSync(outputDir).filter(f => f.endsWith('_transcript.txt'));

          if (mp3Files.length > 0 && transcriptFiles.length > 0) {
            resolve({
              success: true,
              output: path.join(outputDir, transcriptFiles[0])
            });
          } else {
            resolve({
              success: false,
              error: '出力ファイルが見つかりませんでした'
            });
          }
        } else {
          resolve({
            success: false,
            error: `処理が失敗しました (exit code: ${code})`
          });
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;
        reject(error);
      });
    });
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
