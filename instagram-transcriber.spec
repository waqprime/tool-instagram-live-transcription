# -*- mode: python ; coding: utf-8 -*-
import os
import whisper

block_cipher = None

# Get Whisper assets path
whisper_path = os.path.dirname(whisper.__file__)
whisper_assets = os.path.join(whisper_path, 'assets')

# Collect faster-whisper / ctranslate2 data and binaries
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

faster_whisper_datas = []
ctranslate2_datas = []
ctranslate2_binaries = []
try:
    faster_whisper_datas = collect_data_files('faster_whisper')
except Exception:
    pass
try:
    ctranslate2_datas = collect_data_files('ctranslate2')
    ctranslate2_binaries = collect_dynamic_libs('ctranslate2')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ctranslate2_binaries,
    datas=[
        (whisper_assets, 'whisper/assets'),
    ] + faster_whisper_datas + ctranslate2_datas,
    hiddenimports=[
        'whisper',
        'whisper.model',
        'whisper.audio',
        'whisper.decoding',
        'whisper.timing',
        'whisper.tokenizer',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.extractor.instagram',
        'pydub',
        'certifi',
        'urllib3',
        # faster-whisper / ctranslate2
        'faster_whisper',
        'ctranslate2',
        'huggingface_hub',
        'huggingface_hub.utils',
        'tokenizers',
        # openai API client
        'openai',
        'httpx',
        'httpcore',
        'anyio',
        'sniffio',
        'h11',
        'socksio',
        'distro',
        # SpeechBrain speaker diarization
        'speechbrain',
        'speechbrain.inference',
        'speechbrain.inference.speaker',
        'sklearn',
        'sklearn.cluster',
        'torchaudio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='instagram-transcriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
