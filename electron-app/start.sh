#!/bin/bash

# Instagram Live Transcription - Quick Start Script

echo "=================================="
echo "Instagram Live Transcription"
echo "=================================="
echo ""

# Check if Python virtual environment exists
if [ ! -d "../venv_new" ]; then
    echo "Error: Python virtual environment not found!"
    echo "Please run: python3 -m venv ../venv_new"
    echo "Then: source ../venv_new/bin/activate && pip install -r ../requirements.txt"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Electron dependencies..."
    npm install
fi

# Check if Python dependencies are installed
if ! ../venv_new/bin/python3 -c "import whisper" 2>/dev/null; then
    echo "Warning: Python dependencies may not be installed."
    echo "Run: source ../venv_new/bin/activate && pip install -r ../requirements.txt"
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: ffmpeg is not installed."
    echo "Install with: brew install ffmpeg (macOS)"
    echo ""
fi

echo "Starting Electron app..."
echo "Press F12 to toggle DevTools"
echo ""

npm run dev
