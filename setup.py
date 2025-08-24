#!/usr/bin/env python3
"""
Setup script for Async Image Downloader.

This script configures the package for installation via pip, including
dependencies, entry points, and package metadata.

Installation:
    pip install .                    # Install package
    pip install -e .                 # Install in development mode
    pip install .[dev]               # Install with development dependencies
    pip install .[all]               # Install with all optional dependencies

Building distribution:
    python setup.py sdist bdist_wheel
    
Publishing to PyPI:
    twine upload dist/*
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Ensure Python version compatibility
if sys.version_info < (3, 8):
    sys.exit('Error: Async Image Downloader requires Python 3.8 or higher.')

# Read the directory containing setup.py
here = Path(__file__).parent.resolve()

# Read the README file for long description
def read_readme():
    """Read README.md for the long description."""
    readme_path = here / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Async Image Downloader and Processor"

# Read requirements from requirements.txt
def read_requirements(filename):
    """Read requirements from a file."""
    req_path = here / filename
    if req_path.exists():
        with open(req_path, "r", encoding="utf-8") as f:
            return [
                line.strip() 
                for line in f.readlines() 
                if line.strip() and not line.startswith("#")
            ]
    return []

# Get version from a version file or fallback
def get_version():
    """Get version from various sources."""
    # Try to read from version file
    version_file = here / "version.txt"
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    # Try to read from __init__.py
    init_file = here / "core" / "__init__.py"
    if init_file.exists():
        with open(init_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    
    # Fallback version
    return "2.1.1"

# Core requirements (production dependencies)
install_requires = [
    "curl_cffi[aio]>=0.5.0",
    "aiofiles>=23.0.0", 
    "Pillow>=10.0.0",
    "imagehash>=4.3.0",
    "questionary>=2.0.0",
    "psutil>=5.9.0",
    "tqdm>=4.65.0",
    "certifi>=2023.0.0",
    "PyYAML>=6.0.0",
]

# Development dependencies
dev_requires = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0", 
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "pytest-timeout>=2.1.0",
    "types-aiofiles>=23.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
]

# Documentation dependencies  
docs_requires = [
    "sphinx>=6.0.0",
    "sphinx-rtd-theme>=1.2.0",
    "sphinxcontrib-asyncio>=0.3.0",
    "myst-parser>=1.0.0",
]

# Build and distribution dependencies
build_requires = [
    "pyinstaller>=6.0.0",
    "wheel>=0.40.0",
    "twine>=4.0.0",
    "build>=0.10.0",
]

# Performance and monitoring dependencies
performance_requires = [
    "memory-profiler>=0.61.0",
    "line-profiler>=4.0.0",
    "py-spy>=0.3.14",
]

# Security scanning dependencies
security_requires = [
    "bandit>=1.7.5",
    "safety>=2.3.0",
    "pip-audit>=2.5.0",
]

# All optional dependencies combined
all_requires = (
    dev_requires + 
    docs_requires + 
    build_requires + 
    performance_requires + 
    security_requires
)

setup(
    # Package metadata
    name="async-image-downloader",
    version=get_version(),
    description="Asynchronous image downloader and duplicate processor",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="mrfadzay",
    author_email="",  # Add email if available
    maintainer="mrfadzay",
    maintainer_email="",  # Add email if available
    
    # URLs
    url="https://github.com/mrfadzay/async_image_downloader",
    project_urls={
        "Homepage": "https://github.com/mrfadzay/async_image_downloader",
        "Repository": "https://github.com/mrfadzay/async_image_downloader.git",
        "Bug Tracker": "https://github.com/mrfadzay/async_image_downloader/issues",
        "Documentation": "https://github.com/mrfadzay/async_image_downloader/blob/main/README.md",
        "Changelog": "https://github.com/mrfadzay/async_image_downloader/blob/main/CHANGELOG.md",
    },
    
    # Package discovery
    packages=find_packages(
        include=[
            "core",
            "core.*", 
            "ui",
            "ui.*",
            "utils", 
            "utils.*"
        ]
    ),
    
    # Include additional files
    include_package_data=True,
    package_data={
        "": [
            "*.md",
            "*.txt", 
            "*.yml",
            "*.yaml",
            "*.json",
            "*.toml",
            "*.cfg",
            "*.ini",
        ],
    },
    
    # Dependencies
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
        "docs": docs_requires, 
        "build": build_requires,
        "performance": performance_requires,
        "security": security_requires,
        "all": all_requires,
    },
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Entry points for command-line usage
    entry_points={
        "console_scripts": [
            "async-image-downloader=main:main",
            "image-downloader=main:main", 
            "async-img-dl=main:main",
        ],
    },
    
    # Classification
    classifiers=[
        # Development status
        "Development Status :: 4 - Beta",
        
        # Intended audience
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        
        # Topic
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Archiving",
        "Topic :: Utilities",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Programming language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # Operating systems
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux", 
        "Operating System :: MacOS",
        
        # Environment
        "Environment :: Console",
        
        # Natural language
        "Natural Language :: English",
        "Natural Language :: Russian",
    ],
    
    # Keywords for PyPI search
    keywords=[
        "async", "asyncio", "image", "downloader", "download", 
        "duplicate", "detection", "processing", "batch", "bulk",
        "perceptual", "hash", "curl", "cli", "tool", "utility",
        "seo", "content", "management", "automation"
    ],
    
    # License
    license="MIT",
    
    # Platforms
    platforms=["any"],
    
    # Zip safety
    zip_safe=False,
    
    # Tests
    test_suite="tests",
    tests_require=dev_requires,
    
    # Command class for custom commands
    cmdclass={},
    
    # Additional metadata
    options={
        "build_scripts": {
            "executable": "/usr/bin/env python3",
        },
        "egg_info": {
            "tag_build": "",
            "tag_date": False,
        },
    },
)

# Post-installation message
def _post_install_message():
    """Display a message after successful installation."""
    print("\n" + "="*60)
    print("🎉 Async Image Downloader installed successfully!")
    print("="*60)
    print("📖 Quick start:")
    print("   async-image-downloader                    # Interactive mode")
    print("   async-image-downloader download <url>     # Download images")
    print("   async-image-downloader find-duplicates <dir>  # Find duplicates")
    print("")
    print("📚 Documentation:")
    print("   https://github.com/mrfadzay/async_image_downloader")
    print("")
    print("🐛 Issues & Support:")
    print("   https://github.com/mrfadzay/async_image_downloader/issues")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Show post-install message for direct installation
    import atexit
    atexit.register(_post_install_message)