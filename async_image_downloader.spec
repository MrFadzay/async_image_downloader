# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Async Image Downloader.

This file defines how to package the application into a standalone executable.
It includes all necessary dependencies, hidden imports, and configurations
to ensure the built executable works correctly across different environments.

Build command:
    pyinstaller async_image_downloader.spec

Output:
    dist/async_image_downloader.exe (Windows)
    dist/async_image_downloader (Linux/macOS)
"""

import sys
import os
from pathlib import Path

# Get the current directory
current_dir = Path(__file__).parent

# Define hidden imports that PyInstaller might miss
hidden_imports = [
    # SSL/TLS support
    'certifi',
    'ssl',
    '_ssl',
    
    # HTTP and networking
    'curl_cffi',
    'curl_cffi.aio',
    'curl_cffi.requests',
    'urllib3',
    'urllib3.exceptions',
    'urllib3.util',
    'urllib3.util.ssl_',
    'urllib3.util.timeout',
    'urllib3.util.retry',
    'urllib3.contrib',
    
    # Async I/O
    'aiofiles',
    'aiofiles.os',
    'aiofiles.tempfile',
    'asyncio',
    'asyncio.selector_events',
    'asyncio.windows_events' if sys.platform == 'win32' else 'asyncio.unix_events',
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageEnhance',
    'PIL.ImageFilter',
    'PIL.ImageOps',
    'imagehash',
    
    # Configuration and data
    'yaml',
    'json',
    'configparser',
    
    # CLI and UI
    'questionary',
    'questionary.prompts',
    'questionary.styles',
    
    # System and monitoring
    'psutil',
    'psutil._psutil_windows' if sys.platform == 'win32' else 'psutil._psutil_linux',
    'tqdm',
    'tqdm.auto',
    
    # Logging
    'logging',
    'logging.handlers',
    
    # Core modules
    'core',
    'core.downloader',
    'core.duplicates', 
    'core.image_utils',
    'ui',
    'ui.cli',
    'utils',
    'utils.config',
    'utils.config_manager',
    'utils.config_profiles',
    'utils.logger',
    'utils.validation',
    'utils.progress',
    'utils.resource_manager',
    'utils.session_manager',
    'utils.confirmation',
    'utils.error_handling',
    'utils.user_guidance',
]

# Data files to include
datas = [
    # Include configuration templates if they exist
    (str(current_dir / 'utils' / '*.py'), 'utils'),
    (str(current_dir / 'core' / '*.py'), 'core'),
    (str(current_dir / 'ui' / '*.py'), 'ui'),
]

# Binary files to exclude (reduces size)
binaries = []

# Analysis configuration
a = Analysis(
    ['main.py'],
    pathex=[str(current_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
        'unittest',
        'doctest',
        'pdb',
        'turtle',
        'email',
        'xml',
        'multiprocessing',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='async_image_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one
    version=None,  # Add version info file here if you have one
)

# Collection configuration (creates directory with all files)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='async_image_downloader'
)

# Platform-specific optimizations
if sys.platform == 'win32':
    # Windows-specific settings
    exe.version_info = {
        'version': (2, 1, 1, 0),
        'file_version': (2, 1, 1, 0),
        'product_version': (2, 1, 1, 0),
        'file_description': 'Async Image Downloader',
        'product_name': 'Async Image Downloader',
        'copyright': 'Copyright (c) 2024',
        'original_filename': 'async_image_downloader.exe',
        'internal_name': 'async_image_downloader',
    }
elif sys.platform == 'darwin':
    # macOS-specific settings
    app = BUNDLE(
        coll,
        name='AsyncImageDownloader.app',
        icon=None,  # Add .icns file here if you have one
        bundle_identifier='com.async_image_downloader.app',
        version='2.1.1',
        info_plist={
            'CFBundleDisplayName': 'Async Image Downloader',
            'CFBundleIdentifier': 'com.async_image_downloader.app',
            'CFBundleVersion': '2.1.1',
            'CFBundleShortVersionString': '2.1.1',
            'NSHighResolutionCapable': True,
        },
    )