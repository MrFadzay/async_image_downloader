# Async Image Downloader - API Documentation

This document provides comprehensive API documentation for the Async Image Downloader project, including all modules, classes, and functions.

## 📋 Table of Contents

- [Overview](#overview)
- [Core Modules](#core-modules)
  - [downloader](#downloader)
  - [duplicates](#duplicates)
  - [image_utils](#image_utils)
- [Utils Modules](#utils-modules)
  - [config_manager](#config_manager)
  - [config_profiles](#config_profiles)
  - [validation](#validation)
  - [progress](#progress)
  - [session_manager](#session_manager)
  - [error_handling](#error_handling)
  - [resource_manager](#resource_manager)
- [UI Modules](#ui-modules)
  - [cli](#cli)
- [Configuration Reference](#configuration-reference)
- [Examples](#examples)

## 🔍 Overview

The Async Image Downloader API is organized into three main layers:

1. **Core Layer**: Core business logic for downloading and processing images
2. **Utils Layer**: Utility functions and supporting infrastructure
3. **UI Layer**: User interface components

All modules follow async/await patterns where applicable and use type hints for better IDE support.

## 🎯 Core Modules

### downloader

**File**: `core/downloader.py`

The downloader module handles asynchronous image downloading with concurrent processing and error handling.

#### Functions

##### `create_dir(dir_name: Path) -> None`

Creates a directory if it doesn't exist.

```python
await create_dir(Path("./downloads"))
```

**Parameters:**
- `dir_name` (Path): Directory path to create

**Returns:**
- None

**Raises:**
- OSError: If directory creation fails

---

##### `generate_unique_filename(target_dir: Path, base_filename: str) -> Path`

Generates a unique filename in the target directory by adding numeric suffixes.

```python
unique_path = await generate_unique_filename(
    Path("./downloads"), 
    "image001"
)
# Returns: ./downloads/image001.jpeg or ./downloads/image001.1.jpeg
```

**Parameters:**
- `target_dir` (Path): Directory for the file
- `base_filename` (str): Base name without extension

**Returns:**
- Path: Unique file path with .jpeg extension

---

##### `handle_and_save_response(image_data: bytes, headers: dict, full_path: Path, url: str, min_size: int = 100) -> bool`

Processes and saves image data with validation and error handling.

```python
success = await handle_and_save_response(
    image_data=response_content,
    headers=response_headers,
    full_path=Path("./downloads/image.jpg"),
    url="https://example.com/image.jpg"
)
```

**Parameters:**
- `image_data` (bytes): Raw image data
- `headers` (dict): HTTP response headers
- `full_path` (Path): Path to save the image
- `url` (str): Original URL for logging
- `min_size` (int, optional): Minimum file size in bytes (default: 100)

**Returns:**
- bool: True if successfully saved, False otherwise

**Validation:**
- MIME type validation
- File size validation  
- Content type checking

---

##### `download_file(session: AsyncSession, semaphore: asyncio.Semaphore, url: str, target_dir: Path, file_index: int, retries: int = 3) -> bool`

Downloads a single image file asynchronously with retry logic.

```python
import asyncio
from curl_cffi import AsyncSession

async def download_example():
    semaphore = asyncio.Semaphore(5)
    async with AsyncSession() as session:
        success = await download_file(
            session=session,
            semaphore=semaphore,
            url="https://example.com/image.jpg",
            target_dir=Path("./downloads"),
            file_index=1001,
            retries=3
        )
```

**Parameters:**
- `session` (AsyncSession): HTTP session for requests
- `semaphore` (asyncio.Semaphore): Concurrency limiter
- `url` (str): Image URL to download
- `target_dir` (Path): Directory to save the image
- `file_index` (int): Numeric index for filename
- `retries` (int, optional): Number of retry attempts (default: 3)

**Returns:**
- bool: True if download successful, False otherwise

**Features:**
- Automatic retry with exponential backoff
- Rate limiting (429) handling
- Random User-Agent rotation
- URL validation
- Semaphore-controlled concurrency

---

##### `download_images(session: AsyncSession, urls: List[str], target_dir: Path, start_index: int = 1000, retries: int = 3) -> int`

Downloads multiple images concurrently with progress tracking.

```python
async def bulk_download():
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.png"
    ]
    async with AsyncSession() as session:
        count = await download_images(
            session=session,
            urls=urls,
            target_dir=Path("./downloads"),
            start_index=2000,
            retries=5
        )
    print(f"Downloaded {count} images")
```

**Parameters:**
- `session` (AsyncSession): HTTP session for requests
- `urls` (List[str]): List of image URLs
- `target_dir` (Path): Directory to save images
- `start_index` (int, optional): Starting index for filenames (default: 1000)
- `retries` (int, optional): Retry attempts per URL (default: 3)

**Returns:**
- int: Number of successfully downloaded images

**Features:**
- Progress bar with statistics
- Concurrent downloads (configurable limit)
- Individual URL error handling
- Final summary report

---

### duplicates

**File**: `core/duplicates.py`

The duplicates module handles detection and processing of duplicate images using perceptual hashing.

#### Functions

##### `handle_duplicates(directory: Path) -> None`

Finds and renames duplicate images in a directory.

```python
await handle_duplicates(Path("./my_images"))
```

**Parameters:**
- `directory` (Path): Directory to scan for duplicates

**Algorithm:**
- Uses combination of phash, dhash, and average_hash
- Configurable similarity threshold (default: 2 out of 3 hashes match)
- Renames duplicates with "_duplicate_N" suffix

**Example Output:**
```
Before: photo1.jpg, vacation.jpg (duplicate)
After:  photo1.jpg, vacation_duplicate_1.jpg
```

---

##### `uniquify_duplicates(directory: Path) -> None`

Finds duplicates and modifies them to make them unique.

```python
await uniquify_duplicates(Path("./seo_images"))
```

**Parameters:**
- `directory` (Path): Directory containing images to process

**Process:**
1. Detect duplicates using perceptual hashing
2. Apply random modifications (brightness, contrast, crop, noise)
3. Verify uniqueness by recalculating hashes
4. Retry with different modifications if still duplicate

**Modifications Applied:**
- Brightness adjustment (±5-15%)
- Contrast adjustment (±5-15%)
- Random crop (1-5% from edges)
- Subtle noise addition

---

##### `uniquify_all_images(directory: Path) -> None`

Applies uniquification modifications to all images in a directory.

```python
await uniquify_all_images(Path("./batch_process"))
```

**Parameters:**
- `directory` (Path): Directory containing images

**Use Case:**
- SEO optimization (make all images technically unique)
- Batch processing for content uniqueness
- Preparing images for multiple platform uploads

---

### image_utils

**File**: `core/image_utils.py`

Utilities for image processing, hashing, and manipulation.

#### Functions

##### `get_file_hashes(directory: Path) -> Tuple[Dict[Tuple[str, str, str], Path], List[Tuple[Path, Tuple[str, str, str], Path]]]`

Calculates perceptual hashes for all images in a directory and identifies duplicates.

```python
unique_hashes, duplicates = await get_file_hashes(Path("./images"))
print(f"Found {len(duplicates)} duplicates")
```

**Parameters:**
- `directory` (Path): Directory to process

**Returns:**
- Tuple containing:
  - Dict mapping hash tuples to file paths (unique images)
  - List of duplicate info tuples (file_path, hash_tuple, original_path)

**Performance:**
- Optimized O(n log n) algorithm using hash indexing
- Parallel hash calculation using asyncio
- Memory-efficient processing

---

##### `process_and_save_image_sync(image_data: bytes, full_path: Path, content_type: str = "") -> None`

Synchronously processes and saves image data with format conversion.

```python
# Called via executor for non-blocking operation
loop = asyncio.get_running_loop()
await loop.run_in_executor(
    None, 
    process_and_save_image_sync,
    image_data, 
    save_path,
    "image/jpeg"
)
```

**Parameters:**
- `image_data` (bytes): Raw image bytes
- `full_path` (Path): Where to save the processed image
- `content_type` (str, optional): MIME type for debugging

**Features:**
- Auto-format detection from headers
- Transparent background handling (converts to white)
- Quality optimization (95% JPEG quality)
- Error recovery (saves as .unknown if processing fails)

**Supported Formats:**
- JPEG, PNG, WebP, GIF, BMP, TIFF

---

##### `get_modification_functions() -> List[Callable[[Image.Image], Image.Image]]`

Returns list of available image modification functions.

```python
mod_functions = get_modification_functions()
# Returns: [_modify_brightness, _modify_contrast, _modify_crop, _modify_add_noise]
```

**Returns:**
- List[Callable]: Image modification functions

**Available Modifications:**
- `_modify_brightness`: Adjusts image brightness (±5-15%)
- `_modify_contrast`: Adjusts image contrast (±5-15%) 
- `_modify_crop`: Randomly crops 1-5% from edges
- `_modify_add_noise`: Adds subtle random noise

---

## 🛠 Utils Modules

### config_manager

**File**: `utils/config_manager.py`

Comprehensive configuration management with JSON/YAML support.

#### Classes

##### `AppConfig`

Main configuration dataclass containing all application settings.

```python
from utils.config_manager import AppConfig, DownloadConfig

config = AppConfig(
    download=DownloadConfig(max_concurrent_downloads=100),
    version="2.1.1"
)

# Serialization
config_dict = config.to_dict()
config_yaml = yaml.dump(config_dict)

# Deserialization  
restored_config = AppConfig.from_dict(config_dict)
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary
- `from_dict(data: Dict[str, Any]) -> AppConfig`: Create from dictionary

**Attributes:**
- `download`: Download-related settings
- `paths`: File and directory paths
- `validation`: Validation rules
- `duplicates`: Duplicate handling settings
- `ui`: User interface preferences
- `resources`: Resource management settings

---

##### `ConfigManager`

Manages configuration loading, saving, and validation.

```python
from utils.config_manager import ConfigManager
from pathlib import Path

manager = ConfigManager(Path("./config"))

# Load configuration
config = manager.load_config()

# Save configuration
manager.save_config(config, format_type="yaml")

# Update specific settings
manager.update_config("download", max_concurrent_downloads=75)
```

**Methods:**

###### `load_config(config_file: Optional[Path] = None) -> AppConfig`

Loads configuration from file or returns default.

**Parameters:**
- `config_file` (Path, optional): Specific config file path

**Returns:**
- AppConfig: Loaded or default configuration

---

###### `save_config(config: Optional[AppConfig] = None, config_file: Optional[Path] = None, format_type: str = "yaml") -> bool`

Saves configuration to file.

**Parameters:**
- `config` (AppConfig, optional): Configuration to save
- `config_file` (Path, optional): Target file path
- `format_type` (str): "yaml" or "json"

**Returns:**
- bool: Success status

---

### config_profiles

**File**: `utils/config_profiles.py`

Pre-defined configuration profiles for different use cases.

#### Classes

##### `ConfigProfiles`

Factory class for creating specialized configurations.

```python
from utils.config_profiles import ConfigProfiles

# Fast download profile
fast_config = ConfigProfiles.create_fast_download_profile()

# SEO optimization profile
seo_config = ConfigProfiles.create_seo_optimization_profile()

# Safe processing profile
safe_config = ConfigProfiles.create_safe_processing_profile()
```

**Static Methods:**

###### `create_fast_download_profile() -> AppConfig`

Creates configuration optimized for maximum download speed.

**Features:**
- High concurrency (100 downloads)
- Minimal validation
- Auto-confirmations
- Reduced UI messaging

---

###### `create_seo_optimization_profile() -> AppConfig`

Creates configuration optimized for SEO content processing.

**Features:**
- Strict duplicate detection
- Mandatory backups
- HTTPS-only downloads
- Detailed logging

---

###### `create_safe_processing_profile() -> AppConfig`

Creates configuration for safe, conservative processing.

**Features:**
- Low concurrency (10 downloads)
- Strict size limits
- Manual confirmations
- Comprehensive backups

---

### validation

**File**: `utils/validation.py`

Input validation functions for URLs, files, and configurations.

#### Functions

##### `validate_download_request(url: str) -> bool`

Validates URL for safe downloading.

```python
if validate_download_request("https://example.com/image.jpg"):
    # Safe to download
    pass
```

**Checks:**
- Valid URL format
- Allowed schemes (http/https)
- Not in forbidden domains
- No local file access attempts

---

##### `validate_file_size(size_bytes: int) -> bool`

Validates file size against configured limits.

```python
if validate_file_size(len(image_data)):
    # Size is acceptable
    process_image(image_data)
```

---

##### `validate_mime_type(content_type: str) -> bool`

Validates MIME type for image content.

```python
if validate_mime_type("image/jpeg"):
    # Valid image type
    pass
```

**Accepted Types:**
- image/jpeg, image/jpg
- image/png
- image/webp
- image/gif

---

### progress

**File**: `utils/progress.py`

Progress tracking and display utilities.

#### Classes

##### `ProgressTracker`

Manages progress bars and statistics for long-running operations.

```python
from utils.progress import get_progress_tracker

tracker = get_progress_tracker()

async with tracker.track_download_progress(100, "Downloading") as progress:
    for i in range(100):
        # Do work
        progress.update(1)
```

**Methods:**
- `track_download_progress()`: For download operations
- `track_duplicate_progress()`: For duplicate detection
- `track_uniquify_progress()`: For uniquification
- `show_operation_summary()`: Display final statistics

---

### session_manager

**File**: `utils/session_manager.py`

Download session management with pause/resume functionality.

#### Classes

##### `SessionManager`

Manages download sessions with state persistence.

```python
from utils.session_manager import get_session_manager

session_mgr = get_session_manager()

# Check if paused
if not await session_mgr.wait_if_paused():
    # User cancelled operation
    return

# Update progress
await session_mgr.update_progress(url, success=True)
```

**Features:**
- Session state persistence (JSON)
- Pause/resume functionality  
- Progress tracking
- User interaction handling

---

## 🖥 UI Modules

### cli

**File**: `ui/cli.py`

Command-line interface implementation.

#### Functions

##### `main() -> None`

Main entry point for the CLI application.

Handles both interactive and command-line modes based on arguments.

---

##### `interactive_mode() -> None`

Starts interactive menu-driven interface.

**Features:**
- User-friendly menu system
- Input validation
- Help and tips
- Operation confirmations

---

##### Command Functions

###### `download_command(urls: List[str], start_index: int, retries: int) -> None`

CLI command for downloading images.

```bash
python main.py download --start-index 1000 "https://example.com/img.jpg"
```

---

###### `find_duplicates_command(directory: str) -> None`

CLI command for finding duplicates.

```bash
python main.py find-duplicates ./my_images
```

---

###### `uniquify_command(directory: str) -> None`

CLI command for uniquifying duplicates.

```bash
python main.py uniquify ./my_images
```

---

## ⚙️ Configuration Reference

### Complete Configuration Schema

```yaml
# Download settings
download:
  max_concurrent_downloads: 50        # Concurrent download limit
  download_timeout: 30                # Timeout in seconds
  default_retries: 3                  # Retry attempts
  default_start_index: 1000           # Starting filename index
  enable_pause_resume: true           # Pause/resume support
  user_agent_rotation: true           # Rotate User-Agent headers

# File paths
paths:
  image_dir: "./images"               # Base image directory
  download_dir_name: "downloaded_images" # Download subdirectory
  temp_dir: "./temp"                  # Temporary files
  log_file: "app.log"                 # Log file path
  session_file: "download_session.json" # Session state file

# Validation rules
validation:
  max_download_size_mb: 100           # Maximum download size
  max_image_size_mb: 50               # Maximum image processing size
  min_file_size: 100                  # Minimum file size in bytes
  allowed_schemes: ["http", "https"]  # Allowed URL schemes
  forbidden_domains:                  # Blocked domains
    - "localhost"
    - "127.0.0.1"
    - "0.0.0.0"

# Duplicate detection
duplicates:
  similarity_threshold: 2             # Hash matches required (0-3)
  max_uniquify_attempts: 10           # Max uniquification attempts
  auto_confirm_operations: false      # Auto-confirm destructive ops
  create_backups: true                # Create backup files
  backup_suffix: ".backup"            # Backup file suffix

# User interface
ui:
  show_welcome_message: true          # Show startup message
  show_operation_tips: true           # Show helpful tips
  show_safety_warnings: true          # Show safety warnings
  progress_bar_style: "default"       # Progress bar style
  error_details_level: "medium"       # Error detail level

# Resource management
resources:
  memory_threshold_mb: 1000           # Memory usage threshold
  auto_cleanup_temp_files: true       # Auto-clean temp files
  max_temp_files: 1000                # Max temp files
  gc_frequency: 100                   # Garbage collection frequency
```

## 📝 Examples

### Basic Download Example

```python
import asyncio
from pathlib import Path
from curl_cffi import AsyncSession
from core.downloader import download_images

async def download_example():
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.png"
    ]
    
    async with AsyncSession() as session:
        count = await download_images(
            session=session,
            urls=urls,
            target_dir=Path("./downloads"),
            start_index=1000,
            retries=3
        )
    
    print(f"Downloaded {count} images")

# Run the example
asyncio.run(download_example())
```

### Duplicate Detection Example

```python
import asyncio
from pathlib import Path
from core.duplicates import handle_duplicates

async def find_dupes_example():
    await handle_duplicates(Path("./my_images"))
    print("Duplicate detection complete")

asyncio.run(find_dupes_example())
```

### Configuration Example

```python
from utils.config_manager import ConfigManager, AppConfig
from utils.config_profiles import ConfigProfiles

# Use a pre-defined profile
config = ConfigProfiles.create_fast_download_profile()

# Customize settings
config.download.max_concurrent_downloads = 75
config.validation.max_download_size_mb = 200

# Save configuration
manager = ConfigManager()
manager.save_config(config, format_type="yaml")
```

### Custom Progress Tracking

```python
import asyncio
from utils.progress import get_progress_tracker

async def progress_example():
    tracker = get_progress_tracker()
    
    async with tracker.track_download_progress(100, "Processing") as progress:
        for i in range(100):
            # Simulate work
            await asyncio.sleep(0.1)
            progress.update(1)
    
    print("Processing complete!")

asyncio.run(progress_example())
```

---

**Last Updated**: August 24, 2024  
**Version**: 2.1.1  
**License**: MIT