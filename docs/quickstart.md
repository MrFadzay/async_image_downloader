# Quick Start Guide

This guide will help you get up and running with the Async Image Downloader quickly.

## Installation

### Option 1: From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/mrfadzay/async_image_downloader.git
cd async_image_downloader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Option 2: Using pip (Development Install)

```bash
pip install -e .
```

### Option 3: Download Executable

Download the latest release from [GitHub Releases](https://github.com/mrfadzay/async_image_downloader/releases) and run the executable directly.

## Basic Usage

### Interactive Mode

The easiest way to get started is with interactive mode:

```bash
python main.py
```

This will show you a menu with options:
- Download images
- Find duplicates
- Uniquify images
- Exit

### Command Line Mode

For automation and scripting, use command line mode:

#### Download Images

```bash
# Download single image
python main.py download "https://example.com/image.jpg"

# Download multiple images
python main.py download \
  "https://example.com/img1.jpg" \
  "https://example.com/img2.png" \
  "https://example.com/img3.webp"

# With custom settings
python main.py download \
  --start-index 2000 \
  --retries 5 \
  "https://example.com/image.jpg"
```

#### Find Duplicates

```bash
# Find and rename duplicates
python main.py find-duplicates ./my_images

# This will rename duplicates like:
# original.jpg -> original.jpg (unchanged)
# copy.jpg -> copy_duplicate_1.jpg
```

#### Uniquify Images

```bash
# Make duplicates unique
python main.py uniquify ./my_images

# Apply modifications to all images
python main.py uniquify-all ./my_images
```

## Configuration

### Using Configuration Profiles

The application comes with pre-defined profiles for different use cases:

```python
from utils.config_profiles import ConfigProfiles

# Fast download profile (speed-optimized)
fast_config = ConfigProfiles.create_fast_download_profile()

# SEO optimization profile (quality-focused)
seo_config = ConfigProfiles.create_seo_optimization_profile()

# Safe processing profile (conservative settings)
safe_config = ConfigProfiles.create_safe_processing_profile()
```

### Custom Configuration

Create a `config.yaml` file in your project directory:

```yaml
download:
  max_concurrent_downloads: 25
  download_timeout: 45
  default_retries: 3

validation:
  max_download_size_mb: 50
  min_file_size: 1000

duplicates:
  similarity_threshold: 2
  create_backups: true

ui:
  show_welcome_message: true
  progress_bar_style: "detailed"
```

## Common Workflows

### Content Manager Workflow

1. **Bulk Download**: Download images from a list of URLs
2. **Quality Check**: Review downloaded images
3. **Duplicate Detection**: Find and identify duplicates
4. **SEO Optimization**: Uniquify images for web use

```bash
# Step 1: Download
python main.py download \
  --start-index 3000 \
  "https://source1.com/img1.jpg" \
  "https://source2.com/img2.jpg" \
  "https://source3.com/img3.jpg"

# Step 2: Find duplicates
python main.py find-duplicates ./images/downloaded_images

# Step 3: Make unique for SEO
python main.py uniquify ./images/downloaded_images
```

### E-commerce Workflow

For product images that need to be unique across platforms:

```bash
# Download product images
python main.py download \
  --start-index 5000 \
  "https://supplier.com/product1.jpg" \
  "https://supplier.com/product2.jpg"

# Make all images unique (even non-duplicates)
python main.py uniquify-all ./images/downloaded_images
```

### Blog Content Workflow

For blog images that need duplicate checking:

```bash
# Download blog images
python main.py download \
  "https://unsplash.com/photo1.jpg" \
  "https://pexels.com/photo2.jpg"

# Check for duplicates only
python main.py find-duplicates ./blog_images

# Manual review, then uniquify if needed
python main.py uniquify ./blog_images
```

## Advanced Features

### Session Management

The application supports pause and resume for long download sessions:

1. Start a download
2. Press `Ctrl+C` to pause
3. Restart the application - it will offer to resume

### Progress Tracking

All operations show detailed progress with:
- Current item being processed
- Speed statistics
- Estimated time remaining
- Success/failure counts

### Error Handling

The application handles various error scenarios:
- Network timeouts and retries
- Invalid image formats
- Disk space issues
- Permission problems

### Memory Management

For large image sets:
- Streaming downloads (no full file in memory)
- Configurable memory thresholds
- Automatic cleanup of temporary files
- Garbage collection tuning

## Configuration Options

### Download Settings

```yaml
download:
  max_concurrent_downloads: 50     # Parallel downloads
  download_timeout: 30             # Request timeout (seconds)
  default_retries: 3               # Retry attempts
  enable_pause_resume: true        # Session persistence
  user_agent_rotation: true        # Rotate browser headers
```

### Validation Settings

```yaml
validation:
  max_download_size_mb: 100        # Maximum file size
  max_image_size_mb: 50            # Maximum processing size
  min_file_size: 100               # Minimum file size (bytes)
  allowed_schemes: ["https"]       # URL protocols
  forbidden_domains:               # Blocked domains
    - "localhost"
    - "127.0.0.1"
```

### Duplicate Detection Settings

```yaml
duplicates:
  similarity_threshold: 2          # Hash matches needed (0-3)
  max_uniquify_attempts: 10        # Modification attempts
  auto_confirm_operations: false   # Skip confirmations
  create_backups: true             # Backup original files
```

## Troubleshooting

### Common Issues

#### "Permission Denied" Errors
```bash
# Make sure you have write permissions
chmod 755 ./images
```

#### "Too Many Open Files" Errors
```bash
# Reduce concurrent downloads
# In config.yaml:
download:
  max_concurrent_downloads: 10
```

#### Memory Issues with Large Images
```bash
# Reduce image size limits
# In config.yaml:
validation:
  max_image_size_mb: 25
```

### Performance Tuning

#### For Maximum Speed
```yaml
download:
  max_concurrent_downloads: 100
duplicates:
  auto_confirm_operations: true
ui:
  show_operation_tips: false
```

#### For Maximum Safety
```yaml
download:
  max_concurrent_downloads: 5
  default_retries: 5
validation:
  max_download_size_mb: 20
duplicates:
  create_backups: true
```

## Getting Help

### Documentation
- **API Reference**: Detailed function and class documentation
- **Architecture Guide**: System design and component interactions
- **Contributing Guide**: Development setup and contribution guidelines

### Support Channels
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and community support

### Useful Commands

```bash
# Check version
python main.py --version

# Get help for specific command
python main.py download --help

# Verbose logging
python main.py --verbose download "https://example.com/img.jpg"

# Test configuration
python -c "from utils.config_manager import get_config; print(get_config())"
```

## Next Steps

1. **Read the Architecture Guide** to understand the system design
2. **Explore the API Reference** for detailed technical documentation
3. **Check out the Contributing Guide** if you want to contribute
4. **Join the community** through GitHub Discussions

Happy downloading! 🚀