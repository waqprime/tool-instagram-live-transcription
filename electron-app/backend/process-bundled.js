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
    console.log('  Backend binary:', path.basename(this.binaryPath));
    console.log('  ffmpeg binary:', path.basename(this.ffmpegPath));
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

  // ログ出力用: stdout/stderrの行からセンシティブ情報を除去
  _sanitizeLogLine(line) {
    let sanitized = line;
    // URL: クエリパラメータ・フラグメントを除去（https://example.com/path?key=val → https://example.com/path）
    sanitized = sanitized.replace(/https?:\/\/[^\s"']+/g, (url) => this._sanitizeUrl(url));
    // 絶対パス: /Users/xxx/... や C:\Users\xxx\... をベース名に
    sanitized = sanitized.replace(/(?:\/Users\/[^\s"':]+|\/home\/[^\s"':]+|[A-Z]:\\Users\\[^\s"':]+)/g, (p) => {
      const base = p.split(/[\\/]/).pop();
      return base || p;
    });
    return sanitized;
  }

  // ログ出力用: URLからクエリパラメータを除去
  _sanitizeUrl(url) {
    try {
      const parsed = new URL(url);
      // クエリパラメータとフラグメントを除去
      return `${parsed.protocol}//${parsed.hostname}${parsed.pathname}`;
    } catch {
      return url.split('?')[0];
    }
  }

  // ログ出力用: 引数から絶対パスをベース名に、機微情報を除去
  _sanitizeArgs(args) {
    const sensitiveFlags = ['--api-key', '--gemini-api-key', '--obsidian-vault', '--obsidian-folder', '--summary-prompt'];
    return args.map((a, i, arr) => {
      // 機微フラグの値を隠す
      if (i > 0 && sensitiveFlags.includes(arr[i - 1])) return '[REDACTED]';
      if (sensitiveFlags.includes(a)) return a;
      // URLのクエリパラメータを除去
      if (a.startsWith('http://') || a.startsWith('https://')) return this._sanitizeUrl(a);
      // 絶対パスをベース名に変換（出力先ディレクトリは除く）
      if (path.isAbsolute(a) && !arr[i - 1]?.includes('output-dir')) return path.basename(a);
      return a;
    });
  }

  async processUrls(urls, files, outputDir, language, model, keepVideo = false, engine = 'faster-whisper', apiKey = '', obsidianVault = '', obsidianFolder = '', diarize = false, summarize = false, summaryPrompt = '', summaryProvider = 'builtin', summaryModel = '', geminiApiKey = '') {
    this.stopped = false;
    this.engine = engine;
    this.apiKey = apiKey;
    this.obsidianVault = obsidianVault;
    this.obsidianFolder = obsidianFolder;
    this.diarize = diarize;
    this.summarize = summarize;
    this.summaryPrompt = summaryPrompt;
    this.summaryProvider = summaryProvider;
    this.summaryModel = summaryModel;
    this.geminiApiKey = geminiApiKey;
    const results = [];
    const totalItems = urls.length + (files ? files.length : 0);

    // Validate URLs before processing
    console.log('Processing URLs:', urls.map(u => this._sanitizeUrl(u)));
    console.log('Processing Files:', files.map(f => path.basename(f)));

    for (let i = 0; i < urls.length; i++) {
      const url = urls[i];
      if (typeof url !== 'string') {
        console.error(`URL at index ${i} is not a string:`, url);
        this.log('error', `無効なURL（文字列ではありません）: ${typeof url}`);
      } else if (url.includes('[object')) {
        console.error(`URL at index ${i} contains object reference:`, url);
        this.log('error', `無効なURL（オブジェクト参照を含む）: ${url}`);
      }
    }

    // Ensure output directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    let processedCount = 0;

    // Process URLs
    for (let i = 0; i < urls.length; i++) {
      if (this.stopped) {
        this.log('warning', '処理が中断されました');
        break;
      }

      const url = urls[i];

      // Skip invalid URLs
      if (typeof url !== 'string' || url.includes('[object')) {
        this.log('error', `スキップ: 無効なURL - ${url}`);
        results.push({ url: String(url), success: false, error: '無効なURL形式' });
        continue;
      }
      const urlNum = i + 1;

      // Create dedicated folder for this URL
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const folderName = `video_${urlNum}_${timestamp}`;
      const urlOutputDir = path.join(outputDir, folderName);

      if (!fs.existsSync(urlOutputDir)) {
        fs.mkdirSync(urlOutputDir, { recursive: true });
      }

      this.log('info', `[${urlNum}/${totalItems}] 処理開始: ${this._sanitizeUrl(url)}`);
      this.log('info', `[${urlNum}/${totalItems}] 保存先: ${folderName}/`);
      this.updateProgress((i / totalItems) * 100, `URL ${urlNum}/${totalItems} を処理中...`);

      try {
        // Run the bundled binary with URL
        const result = await this.processSingleUrl(url, urlOutputDir, language, model, keepVideo, urlNum, totalItems);

        if (result.success) {
          this.log('success', `[${urlNum}/${totalItems}] 完了`);
          results.push({ url, success: true, output: result.output });
        } else {
          this.log('error', `[${urlNum}/${totalItems}] 失敗: ${result.error}`);
          results.push({ url, success: false, error: result.error });
        }

      } catch (error) {
        this.log('error', `[${urlNum}/${totalItems}] エラー: ${error.message}`);
        results.push({ url, success: false, error: error.message });
      }

      // Update progress
      processedCount++;
      this.updateProgress((processedCount / totalItems) * 100, `${processedCount}/${totalItems} 完了`);
    }

    // Process Files
    if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        if (this.stopped) {
          this.log('warning', '処理が中断されました');
          break;
        }

        const filePath = files[i];
        const fileNum = i + 1 + urls.length;

        // Create dedicated folder for this file
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const fileName = path.basename(filePath, path.extname(filePath));
        const folderName = `file_${fileName}_${timestamp}`;
        const fileOutputDir = path.join(outputDir, folderName);

        if (!fs.existsSync(fileOutputDir)) {
          fs.mkdirSync(fileOutputDir, { recursive: true });
        }

        this.log('info', `[${fileNum}/${totalItems}] ファイル処理開始: ${path.basename(filePath)}`);
        this.log('info', `[${fileNum}/${totalItems}] 保存先: ${folderName}/`);
        this.updateProgress((processedCount / totalItems) * 100, `ファイル ${fileNum}/${totalItems} を処理中...`);

        try {
          // Run the bundled binary with local file
          const result = await this.processSingleFile(filePath, fileOutputDir, language, model, keepVideo, fileNum, totalItems);

          if (result.success) {
            this.log('success', `[${fileNum}/${totalItems}] 完了`);
            results.push({ file: filePath, success: true, output: result.output });
          } else {
            this.log('error', `[${fileNum}/${totalItems}] 失敗: ${result.error}`);
            results.push({ file: filePath, success: false, error: result.error });
          }

        } catch (error) {
          this.log('error', `[${fileNum}/${totalItems}] エラー: ${error.message}`);
          results.push({ file: filePath, success: false, error: error.message });
        }

        // Update progress
        processedCount++;
        this.updateProgress((processedCount / totalItems) * 100, `${processedCount}/${totalItems} 完了`);
      }
    }

    return results;
  }

  async processSingleFile(filePath, outputDir, language, model, keepVideo, fileNum, totalItems) {
    return new Promise((resolve, reject) => {
      // Verify binary exists
      if (!fs.existsSync(this.binaryPath)) {
        const error = `Backend binary not found: ${this.binaryPath}`;
        this.log('error', error);
        reject(new Error(error));
        return;
      }

      const args = [
        '--local-file', filePath,
        '--model', model,
        '--language', language,
        '--output-dir', outputDir,
        '--engine', this.engine || 'faster-whisper'
      ];

      // Add --keep-video flag if enabled
      if (keepVideo) {
        args.push('--keep-video');
      }

      // Add Obsidian vault path if specified
      if (this.obsidianVault) {
        args.push('--obsidian-vault', this.obsidianVault);
        if (this.obsidianFolder) {
          args.push('--obsidian-folder', this.obsidianFolder);
        }
      }

      // Add --diarize flag if enabled
      if (this.diarize) {
        args.push('--diarize');
      }

      // Add --summarize flag if enabled
      if (this.summarize) {
        args.push('--summarize');
        args.push('--summary-provider', this.summaryProvider || 'builtin');
        if (this.summaryPrompt) {
          args.push('--summary-prompt', this.summaryPrompt);
        }
        if (this.summaryModel) {
          args.push('--summary-model', this.summaryModel);
        }
        // geminiApiKey is passed via env var below, not CLI args
      }

      // Set ffmpeg path and unbuffered output as environment variables
      const env = { ...process.env };
      env.PYTHONUNBUFFERED = '1';
      if (this.ffmpegPath) {
        env.FFMPEG_BINARY = this.ffmpegPath;
      }
      // Pass API keys via environment variable (not CLI args for security)
      if (this.apiKey) {
        env.OPENAI_API_KEY = this.apiKey;
      }
      if (this.geminiApiKey) {
        env.GEMINI_API_KEY = this.geminiApiKey;
      }

      // ログにはセンシティブな引数を除外して出力
      const sensitiveFlags = ['--api-key', '--gemini-api-key'];
      const safeArgs = args.filter((a, i, arr) => !sensitiveFlags.includes(a) && (i === 0 || !sensitiveFlags.includes(arr[i - 1])));
      this.log('info', `[${fileNum}/${totalItems}] バイナリ実行: ${path.basename(this.binaryPath)}`);
      this.log('info', `[${fileNum}/${totalItems}] 引数: ${this._sanitizeArgs(safeArgs).join(' ')}`);

      // Create log file
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const logFilePath = path.join(outputDir, `process_log_${timestamp}.txt`);
      const logStream = fs.createWriteStream(logFilePath, { flags: 'a' });

      const writeLog = (message) => {
        const timestampStr = new Date().toISOString();
        logStream.write(`[${timestampStr}] ${message}\n`);
      };

      writeLog('='.repeat(60));
      writeLog(`Processing file: ${path.basename(filePath)}`);
      writeLog(`Binary: ${path.basename(this.binaryPath)}`);
      writeLog(`Args: ${this._sanitizeArgs(args).join(' ')}`);
      writeLog('='.repeat(60));

      this.currentProcess = spawn(this.binaryPath, args, { env });

      let outputData = '';
      let errorData = '';

      this.currentProcess.stdout.on('data', (data) => {
        const text = data.toString();
        outputData += text;

        const lines = text.split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;
          writeLog(`STDOUT: ${this._sanitizeLogLine(line.trim())}`);

          if (line.includes('ステップ') || line.includes('処理') || line.includes('[OK]') || line.includes('[ERROR]')) {
            this.log('info', this._sanitizeLogLine(line.trim()));
          }
        }
      });

      this.currentProcess.stderr.on('data', (data) => {
        const text = data.toString();
        errorData += text;

        const lines = text.split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;
          writeLog(`STDERR: ${this._sanitizeLogLine(line.trim())}`);
        }
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        writeLog('='.repeat(60));
        writeLog(`Process finished with exit code: ${code}`);
        writeLog('='.repeat(60));

        if (code === 0) {
          // Find the output files
          const mp3Files = fs.readdirSync(outputDir).filter(f => f.endsWith('.mp3'));
          const transcriptFiles = fs.readdirSync(outputDir).filter(f => f.endsWith('_transcript.txt'));

          if (mp3Files.length > 0 && transcriptFiles.length > 0) {
            writeLog(`SUCCESS: Found output files`);
            writeLog(`Log file saved to: ${logFilePath}`);
            logStream.end();
            resolve({
              success: true,
              output: path.join(outputDir, transcriptFiles[0])
            });
          } else {
            writeLog(`ERROR: Output files not found`);
            writeLog(`Log file saved to: ${logFilePath}`);
            logStream.end();
            resolve({
              success: false,
              error: '出力ファイルが見つかりませんでした'
            });
          }
        } else {
          writeLog(`ERROR: Process failed with exit code ${code}`);
          writeLog(`Log file saved to: ${logFilePath}`);
          logStream.end();
          resolve({
            success: false,
            error: `処理が失敗しました (exit code: ${code})`
          });
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;
        writeLog('='.repeat(60));
        writeLog(`FATAL ERROR: ${this._sanitizeLogLine(error.message)}`);
        writeLog('='.repeat(60));
        logStream.end();
        reject(error);
      });
    });
  }

  async processSingleUrl(url, outputDir, language, model, keepVideo, urlNum, totalItems) {
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
        '--output-dir', outputDir,
        '--engine', this.engine || 'faster-whisper',
        '--all'  // Always process all videos on UTAGE pages
      ];

      // Add --keep-video flag if enabled
      if (keepVideo) {
        args.push('--keep-video');
      }

      // Add Obsidian vault path if specified
      if (this.obsidianVault) {
        args.push('--obsidian-vault', this.obsidianVault);
        if (this.obsidianFolder) {
          args.push('--obsidian-folder', this.obsidianFolder);
        }
      }

      // Add --diarize flag if enabled
      if (this.diarize) {
        args.push('--diarize');
      }

      // Add --summarize flag if enabled
      if (this.summarize) {
        args.push('--summarize');
        args.push('--summary-provider', this.summaryProvider || 'builtin');
        if (this.summaryPrompt) {
          args.push('--summary-prompt', this.summaryPrompt);
        }
        if (this.summaryModel) {
          args.push('--summary-model', this.summaryModel);
        }
        // geminiApiKey is passed via env var below, not CLI args
      }

      // Set ffmpeg path and unbuffered output as environment variables
      const env = { ...process.env };
      env.PYTHONUNBUFFERED = '1';  // Force unbuffered output for Windows
      if (this.ffmpegPath) {
        env.FFMPEG_BINARY = this.ffmpegPath;
        this.log('info', `Using ffmpeg: ${path.basename(this.ffmpegPath)}`);
      }
      // Pass API keys via environment variable (not CLI args for security)
      if (this.apiKey) {
        env.OPENAI_API_KEY = this.apiKey;
      }
      if (this.geminiApiKey) {
        env.GEMINI_API_KEY = this.geminiApiKey;
      }

      // ログにはセンシティブな引数を除外して出力
      const sensitiveFlags = ['--api-key', '--gemini-api-key'];
      const safeArgs = args.filter((a, i, arr) => !sensitiveFlags.includes(a) && (i === 0 || !sensitiveFlags.includes(arr[i - 1])));
      this.log('info', `[${urlNum}/${totalItems}] バイナリ実行: ${path.basename(this.binaryPath)}`);
      this.log('info', `[${urlNum}/${totalItems}] 引数: ${this._sanitizeArgs(safeArgs).join(' ')}`);

      // Create log file for this processing session
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const logFilePath = path.join(outputDir, `process_log_${timestamp}.txt`);
      const logStream = fs.createWriteStream(logFilePath, { flags: 'a' });

      const writeLog = (message) => {
        const timestampStr = new Date().toISOString();
        logStream.write(`[${timestampStr}] ${message}\n`);
      };

      writeLog('='.repeat(60));
      writeLog(`Processing started: ${this._sanitizeUrl(url)}`);
      writeLog(`Binary: ${path.basename(this.binaryPath)}`);
      writeLog(`Args: ${this._sanitizeArgs(args).join(' ')}`);
      writeLog('='.repeat(60));

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

          // Write sanitized stdout to log file
          writeLog(`STDOUT: ${this._sanitizeLogLine(line.trim())}`);

          // Parse [PROGRESS] messages
          const progressMatch = line.match(/\[PROGRESS\]\s*(.+?):\s*(\d+(?:\.\d+)?)%/);
          if (progressMatch) {
            const taskName = progressMatch[1];  // "ダウンロード", "音声抽出", "文字起こし"
            const percent = parseFloat(progressMatch[2]);

            // Calculate overall progress based on task
            // Task weights: Download 33%, Audio 33%, Transcribe 34%
            const currentUrlIndex = urlNum - 1;  // Convert to 0-based index
            let overallPercent = (currentUrlIndex / totalItems) * 100;  // Base progress for this URL
            const urlProgress = 100 / totalItems;  // Progress allocated for one URL

            if (taskName.includes('ダウンロード')) {
              overallPercent += (percent / 100) * (urlProgress * 0.33);
            } else if (taskName.includes('音声抽出')) {
              overallPercent += (urlProgress * 0.33) + (percent / 100) * (urlProgress * 0.33);
            } else if (taskName.includes('文字起こし')) {
              overallPercent += (urlProgress * 0.66) + (percent / 100) * (urlProgress * 0.34);
            }

            this.updateProgress(
              Math.min(100, overallPercent),
              `${taskName}中... (${percent.toFixed(1)}%)`,
              `URL ${urlNum}/${totalItems}`
            );
            this.log('info', `${taskName}: ${percent.toFixed(1)}%`);
            lastProgressUpdate = Date.now();
            continue;
          }

          // Log important messages (sanitized)
          if (line.includes('ステップ') || line.includes('処理') || line.includes('[OK]') || line.includes('[ERROR]') || line.includes('Whisper')) {
            this.log('info', this._sanitizeLogLine(line.trim()));
          }

          // Update progress for long operations (fallback, sanitized)
          const now = Date.now();
          if (now - lastProgressUpdate > 2000) {
            this.updateProgress(null, `処理中: URL ${urlNum}/${totalItems}`, this._sanitizeLogLine(line.substring(0, 100)));
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

          // Write sanitized stderr to log file
          writeLog(`STDERR: ${this._sanitizeLogLine(line.trim())}`);

          // Log as error or warning based on content
          const sanitizedLine = this._sanitizeLogLine(line.trim());
          if (line.includes('error') || line.includes('Error') || line.includes('ERROR') || line.includes('Exception') || line.includes('Traceback')) {
            this.log('error', `STDERR: ${sanitizedLine}`);
          } else if (line.includes('warning') || line.includes('Warning') || line.includes('WARN')) {
            this.log('warning', `STDERR: ${sanitizedLine}`);
          } else {
            // Log all other stderr as info for debugging
            this.log('debug', `STDERR: ${sanitizedLine}`);
          }
        }
      });

      this.currentProcess.on('close', (code) => {
        this.currentProcess = null;

        // Write final log entry
        writeLog('='.repeat(60));
        writeLog(`Process finished with exit code: ${code}`);
        writeLog('='.repeat(60));

        if (code === 0) {
          // Find the output files
          const mp3Files = fs.readdirSync(outputDir).filter(f => f.endsWith('.mp3'));
          const transcriptFiles = fs.readdirSync(outputDir).filter(f => f.endsWith('_transcript.txt'));

          if (mp3Files.length > 0 && transcriptFiles.length > 0) {
            writeLog(`SUCCESS: Found output files - MP3: ${mp3Files[0]}, Transcript: ${transcriptFiles[0]}`);
            writeLog(`Log file saved to: ${logFilePath}`);
            logStream.end();
            resolve({
              success: true,
              output: path.join(outputDir, transcriptFiles[0])
            });
          } else {
            writeLog(`ERROR: Output files not found - MP3s: ${mp3Files.length}, Transcripts: ${transcriptFiles.length}`);
            writeLog(`Log file saved to: ${logFilePath}`);
            logStream.end();
            resolve({
              success: false,
              error: '出力ファイルが見つかりませんでした'
            });
          }
        } else {
          writeLog(`ERROR: Process failed with exit code ${code}`);
          writeLog(`Log file saved to: ${logFilePath}`);
          logStream.end();
          resolve({
            success: false,
            error: `処理が失敗しました (exit code: ${code})`
          });
        }
      });

      this.currentProcess.on('error', (error) => {
        this.currentProcess = null;

        // Write sanitized error to log file
        writeLog('='.repeat(60));
        writeLog(`FATAL ERROR: ${this._sanitizeLogLine(error.message)}`);
        writeLog(`Stack trace: ${this._sanitizeLogLine(error.stack || '')}`);
        writeLog('='.repeat(60));
        logStream.end();

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
