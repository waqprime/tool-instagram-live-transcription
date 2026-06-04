# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Support cross-architecture builds (e.g., arm64 host building for x86_64)
target_arch = os.environ.get('PYINSTALLER_TARGET_ARCH', None)

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
    pathex=[os.path.abspath('.')],
    binaries=ctranslate2_binaries,
    datas=faster_whisper_datas + ctranslate2_datas
        + ([('.app_token', '.')] if os.path.exists('.app_token') else [])
        + [
            # ローカルモジュール（単独.pyファイルはhiddenimportsでは不十分なためdatasで同梱）
            ('transcriber.py', '.'),
            ('downloader.py', '.'),
            ('audio_converter.py', '.'),
            ('summarizer.py', '.'),
            ('log_sender.py', '.'),
            ('title_generator.py', '.'),
            ('obsidian_writer.py', '.'),
            ('voicy_extractor.py', '.'),
            ('standfm_extractor.py', '.'),
            ('utage_extractor.py', '.'),
        ],
    hiddenimports=[
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
        # openai API client (pydantic is a required dependency of openai>=1.0)
        'openai',
        'pydantic',
        'pydantic.deprecated',
        'pydantic.deprecated.class_validators',
        'pydantic_core',
        'httpx',
        'httpcore',
        'anyio',
        'sniffio',
        'h11',
        'socksio',
        'distro',
        # Voicy/UTAGE: Selenium
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.desired_capabilities',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'webdriver_manager',
        'webdriver_manager.chrome',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # PyTorch / ML
        'torch',
        'torchaudio',
        'torchvision',
        'torchsde',
        'torchdiffeq',
        'torchmetrics',
        'pytorch_lightning',
        'whisper',
        'speechbrain',
        'transformers',
        'accelerate',
        'sklearn',
        'scikit-learn',
        'scipy',
        'sympy',
        # Data / Visualization
        'matplotlib',
        'pandas',
        'pyarrow',
        'altair',
        # Image processing (not needed)
        'skimage',
        'cv2',
        'opencv-python',
        'imageio',
        'PIL',
        # GUI / misc
        'tkinter',
        '_tkinter',
        'tcl',
        # Dev / test
        'numpy.testing',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        # Other heavy unused
        'pygments',
        'lxml',
        'open_clip_torch',
        'uvicorn',
        'starlette',
        'fastapi',
        'jsonschema',
        'narwhals',
    ],
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
    target_arch=target_arch,
    codesign_identity=os.environ.get('CODESIGN_IDENTITY', None),
    entitlements_file=None,
)
