# 🎉 Async Image Downloader v2.1.1 - Critical PyInstaller Fixes

## 🚨 Critical Bug Fix Release

This release resolves a **critical issue** where the PyInstaller-built executable would fail to start due to missing SSL certificate modules.

### ❌ Previous Issue
```
ModuleNotFoundError: No module named 'certifi'
[PYI-17140:ERROR] Failed to execute script 'main' due to unhandled exception!
```

### ✅ Now Fixed
The executable now runs smoothly with proper SSL certificate handling!

---

## 🔧 What's Fixed

### **PyInstaller Bundling Issues**
- **Added `certifi` dependency** to `requirements.txt` for SSL certificate verification
- **Created comprehensive `.spec` file** with all hidden imports properly defined
- **Fixed GitHub Actions workflow** to use the proper spec file instead of CLI arguments
- **Resolved SSL/TLS certificate issues** in the bundled executable

### **Dependencies Now Properly Bundled**
- ✅ `certifi` - SSL certificates
- ✅ `curl_cffi` & `curl_cffi.aio` - HTTP client with browser emulation  
- ✅ `aiofiles` - Async file operations
- ✅ `PIL` modules - Image processing
- ✅ `imagehash` - Duplicate detection
- ✅ `scipy` & `numpy` - Mathematical operations
- ✅ `questionary` - Interactive CLI
- ✅ `psutil` & `tqdm` - System monitoring and progress bars

### **Build System Improvements**
- **Stable executable** generation on all supported platforms (Windows, macOS, Linux)
- **Automated GitHub Actions** builds use correct configuration
- **Comprehensive error handling** in the build process

---

## 🧪 Testing Improvements

### **New Test Suite Added**
- **Unit Tests**: Image hashing, duplicate detection, validation logic
- **Integration Tests**: Complete download workflow testing
- **Mocking**: Proper test isolation with pytest-mock
- **Coverage**: pytest-cov integration for test coverage reporting
- **Configuration**: Centralized pytest setup in `conftest.py`

### **Test Structure**
```
tests/
├── unit/
│   ├── test_image_hashing.py
│   ├── test_duplicate_detection_mocks.py
│   └── test_validation_and_modifications.py
├── integration/
│   └── test_download_workflow.py
└── conftest.py
```

---

## 📦 Installation & Usage

### **Download Pre-built Executable**
1. Download `async_image_downloader.exe` from the release assets
2. Run directly - no Python installation required!

### **From Source**
```bash
git clone https://github.com/mrfadzay/async_image_downloader.git
cd async_image_downloader
pip install -r requirements.txt
python main.py
```

### **Build Your Own**
```bash
pip install pyinstaller
pyinstaller async_image_downloader.spec
```

---

## 🚀 Features Still Available

- **⚡ Bulk Image Downloading** - Download hundreds of images asynchronously
- **🔍 Duplicate Detection** - Find visual duplicates using perceptual hashing
- **🎨 Image Uniquification** - Make images unique for SEO purposes  
- **🖥️ Interactive & CLI Modes** - Flexible usage options
- **🌐 Anti-Bot Protection** - curl_cffi with browser emulation
- **📊 Progress Tracking** - Real-time download progress
- **🛡️ Error Handling** - Robust retry mechanisms

---

## 🔗 Quick Start

### Interactive Mode
```bash
./async_image_downloader.exe
```

### CLI Mode
```bash
# Download images
./async_image_downloader.exe download "https://example.com/image1.jpg" "https://example.com/image2.jpg"

# Find duplicates
./async_image_downloader.exe find-duplicates ./images

# Uniquify images
./async_image_downloader.exe uniquify ./images
```

---

## 🙏 Acknowledgments

Thanks to all users who reported the PyInstaller SSL certificate issue. This release ensures a smooth experience for all users of the standalone executable.

---

## 📋 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete version history and detailed changes.

**Previous Release**: v2.1.0  
**Current Release**: v2.1.1  
**Type**: Bug Fix Release  
**Priority**: Critical