Async Image Downloader Documentation
====================================

Welcome to the documentation for Async Image Downloader, a powerful asynchronous tool for downloading images and managing duplicates.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api
   architecture
   contributing

Overview
--------

The Async Image Downloader is a command-line tool designed to automate the process of downloading images and managing duplicates. It's particularly useful for content managers working with websites, e-commerce platforms, or blogs.

Key Features
------------

* **Efficient Asynchronous Downloads**: High-performance concurrent image downloading
* **Intelligent Duplicate Detection**: Uses perceptual hashing to find visual duplicates
* **Image Uniquification**: Makes images unique for SEO purposes
* **Two Interface Modes**: CLI and interactive modes for different use cases
* **Robust Error Handling**: Automatic retries and comprehensive error management
* **Configurable Profiles**: Pre-defined configurations for different scenarios

Quick Start
-----------

1. **Installation**::

    git clone https://github.com/mrfadzay/async_image_downloader.git
    cd async_image_downloader
    pip install -r requirements.txt

2. **Basic Usage**::

    # Interactive mode
    python main.py
    
    # CLI mode
    python main.py download "https://example.com/image.jpg"
    python main.py find-duplicates ./my_images
    python main.py uniquify ./my_images

Project Structure
-----------------

::

    async_image_downloader/
    ├── core/                    # Core functionality
    │   ├── downloader.py       # Image downloading logic
    │   ├── duplicates.py       # Duplicate detection
    │   └── image_utils.py      # Image processing
    ├── ui/                     # User interface
    │   └── cli.py             # Command-line interface
    ├── utils/                  # Utilities and configuration
    ├── tests/                  # Test suite
    └── main.py                # Application entry point

API Reference
-------------

For detailed API documentation, see the :doc:`api` section.

Architecture
------------

For system architecture and design patterns, see the :doc:`architecture` section.

Contributing
------------

Interested in contributing? Check out our :doc:`contributing` guidelines.

Links
-----

* **GitHub Repository**: https://github.com/mrfadzay/async_image_downloader
* **Issue Tracker**: https://github.com/mrfadzay/async_image_downloader/issues
* **Releases**: https://github.com/mrfadzay/async_image_downloader/releases

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`