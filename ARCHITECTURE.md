# Async Image Downloader - Architecture Documentation

This document provides a comprehensive overview of the Async Image Downloader's architecture, component interactions, and design patterns.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Interactions](#component-interactions)
- [Data Flow](#data-flow)
- [Design Patterns](#design-patterns)
- [Module Details](#module-details)
- [Configuration System](#configuration-system)
- [Error Handling Strategy](#error-handling-strategy)
- [Performance Considerations](#performance-considerations)
- [Future Architecture Plans](#future-architecture-plans)

## 🏗 Overview

The Async Image Downloader follows a **modular, asynchronous architecture** built around Python's `asyncio` framework. The system is designed for:

- **High Performance**: Concurrent downloads and processing
- **Reliability**: Robust error handling and retry mechanisms  
- **Extensibility**: Modular design for easy feature additions
- **Usability**: Both CLI and interactive modes
- **Maintainability**: Clear separation of concerns

### Key Architectural Principles

1. **Asynchronous by Design**: All I/O operations are non-blocking
2. **Modular Architecture**: Clear separation of concerns
3. **Configuration-Driven**: Behavior controlled by configuration
4. **Error-First Design**: Comprehensive error handling at all levels
5. **Resource-Aware**: Memory and file descriptor management

## 🏛 System Architecture

```mermaid
graph TB
    %% Entry Point
    A[main.py] --> B[UI Layer]
    
    %% UI Layer
    B --> C[CLI Interface]
    B --> D[Interactive Interface]
    
    %% Core Layer
    C --> E[Core Layer]
    D --> E
    E --> F[Downloader]
    E --> G[Duplicates]
    E --> H[Image Utils]
    
    %% Utils Layer
    F --> I[Utils Layer]
    G --> I
    H --> I
    I --> J[Config Manager]
    I --> K[Logger]
    I --> L[Validation]
    I --> M[Progress]
    I --> N[Session Manager]
    I --> O[Error Handling]
    I --> P[Resource Manager]
    
    %% External Dependencies
    F --> Q[curl_cffi]
    F --> R[aiofiles]
    G --> S[PIL/Pillow]
    G --> T[imagehash]
    
    %% Configuration
    J --> U[Config Profiles]
    J --> V[Config Files]
    
    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style I fill:#e8f5e8
    style Q fill:#fff3e0
    style R fill:#fff3e0
    style S fill:#fff3e0
    style T fill:#fff3e0
```

## 🔄 Component Interactions

### High-Level Component Flow

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI Interface
    participant DL as Downloader
    participant DUP as Duplicates
    participant IMG as Image Utils
    participant CFG as Config Manager
    participant LOG as Logger
    
    U->>CLI: Execute command
    CLI->>CFG: Load configuration
    CFG-->>CLI: Configuration loaded
    
    alt Download Command
        CLI->>DL: Start download
        DL->>IMG: Process images
        DL->>LOG: Log progress
        DL-->>CLI: Download complete
    else Find Duplicates
        CLI->>DUP: Analyze directory
        DUP->>IMG: Calculate hashes
        DUP->>LOG: Log findings
        DUP-->>CLI: Duplicates found
    else Uniquify
        CLI->>DUP: Process duplicates
        DUP->>IMG: Modify images
        DUP->>LOG: Log changes
        DUP-->>CLI: Uniquification complete
    end
    
    CLI-->>U: Operation result
```

### Download Workflow Detail

```mermaid
flowchart TD
    A[Start Download] --> B[Load Configuration]
    B --> C[Validate URLs]
    C --> D{URLs Valid?}
    D -->|No| E[Report Errors]
    D -->|Yes| F[Create Session Manager]
    F --> G[Initialize Progress Tracker]
    G --> H[Create Download Tasks]
    H --> I[Execute Concurrent Downloads]
    I --> J[Process Each URL]
    
    J --> K[Validate Content]
    K --> L{Content Valid?}
    L -->|No| M[Log Error & Retry]
    L -->|Yes| N[Process Image]
    N --> O[Save to Disk]
    O --> P[Update Progress]
    
    M --> Q{Retries Left?}
    Q -->|Yes| J
    Q -->|No| R[Mark Failed]
    
    P --> S{More URLs?}
    R --> S
    S -->|Yes| T[Continue Processing]
    S -->|No| U[Generate Summary]
    
    T --> I
    U --> V[End Download]
    
    style A fill:#c8e6c9
    style V fill:#ffcdd2
    style D fill:#fff3e0
    style L fill:#fff3e0
    style Q fill:#fff3e0
    style S fill:#fff3e0
```

### Duplicate Detection Architecture

```mermaid
graph TB
    A[Input Directory] --> B[Scan Image Files]
    B --> C[Parallel Hash Calculation]
    
    C --> D[phash Calculation]
    C --> E[dhash Calculation]  
    C --> F[average_hash Calculation]
    
    D --> G[Hash Comparison Engine]
    E --> G
    F --> G
    
    G --> H{Similarity Threshold}
    H -->|Match| I[Mark as Duplicate]
    H -->|No Match| J[Mark as Unique]
    
    I --> K[Duplicate Processing]
    J --> L[Unique File Registry]
    
    K --> M[Rename Strategy]
    K --> N[Uniquify Strategy]
    
    M --> O[Add Suffix]
    N --> P[Apply Modifications]
    
    P --> Q[Brightness Adjustment]
    P --> R[Contrast Adjustment]
    P --> S[Crop Operation]
    P --> T[Noise Addition]
    
    Q --> U[Recalculate Hash]
    R --> U
    S --> U
    T --> U
    
    U --> V{Still Duplicate?}
    V -->|Yes| W[Retry with Different Modifications]
    V -->|No| X[Success]
    
    W --> P
    X --> Y[Update Registry]
    
    style A fill:#e3f2fd
    style G fill:#f3e5f5
    style H fill:#fff3e0
    style P fill:#e8f5e8
    style V fill:#fff3e0
```

## 📊 Data Flow

### Configuration Data Flow

```mermaid
flowchart LR
    A[Default Config] --> B[Config Manager]
    C[Config Files] --> B
    D[Environment Variables] --> B
    E[Command Line Args] --> B
    
    B --> F[Merged Configuration]
    F --> G[Validation]
    G --> H{Valid?}
    H -->|Yes| I[Active Configuration]
    H -->|No| J[Error & Fallback]
    
    I --> K[Application Components]
    J --> A
    
    K --> L[Downloader Settings]
    K --> M[Validation Rules]
    K --> N[UI Preferences]
    K --> O[Resource Limits]
    
    style B fill:#e1f5fe
    style G fill:#fff3e0
    style H fill:#ffeb3b
    style I fill:#c8e6c9
```

### Error Handling Flow

```mermaid
graph TD
    A[Operation Start] --> B[Try Block]
    B --> C{Error Occurs?}
    C -->|No| D[Success Path]
    C -->|Yes| E[Error Handler]
    
    E --> F[Classify Error]
    F --> G{Error Type}
    
    G -->|Network| H[Network Error Handler]
    G -->|File I/O| I[File Error Handler]
    G -->|Image Processing| J[Image Error Handler]
    G -->|Validation| K[Validation Error Handler]
    G -->|Unknown| L[Generic Error Handler]
    
    H --> M{Retryable?}
    I --> N[Log & Continue]
    J --> O[Save as Unknown]
    K --> P[User Feedback]
    L --> Q[Log & Report]
    
    M -->|Yes| R[Exponential Backoff]
    M -->|No| S[Log & Skip]
    
    R --> T{Max Retries?}
    T -->|No| B
    T -->|Yes| S
    
    N --> U[Continue Operation]
    O --> U
    P --> U
    Q --> U
    S --> U
    D --> U
    
    U --> V[Operation Complete]
    
    style E fill:#ffcdd2
    style F fill:#fff3e0
    style M fill:#fff3e0
    style T fill:#fff3e0
```

## 🎯 Design Patterns

### 1. Command Pattern
The CLI interface implements the Command pattern for handling different operations:

```python
# Each command is encapsulated as a separate function
async def download_command(urls, start_index, retries)
async def find_duplicates_command(directory)
async def uniquify_command(directory)
```

### 2. Strategy Pattern
Different image modification strategies are implemented as pluggable functions:

```python
def _modify_brightness(image: Image) -> Image
def _modify_contrast(image: Image) -> Image
def _modify_crop(image: Image) -> Image
def _modify_add_noise(image: Image) -> Image
```

### 3. Observer Pattern
Progress tracking uses an observer-like pattern to update UI:

```python
class ProgressTracker:
    def update(self, progress_data)
    def notify_completion(self, results)
```

### 4. Singleton Pattern
Configuration and logging use singleton-like patterns:

```python
config_manager = ConfigManager()  # Global instance
logger = setup_logger()           # Shared logger
```

### 5. Factory Pattern
Configuration profiles use factory methods:

```python
class ConfigProfiles:
    @staticmethod
    def create_fast_download_profile() -> AppConfig
    @staticmethod
    def create_seo_optimization_profile() -> AppConfig
```

## 🧩 Module Details

### Core Modules

#### `core/downloader.py`
**Responsibility**: Asynchronous image downloading
- **Key Functions**: `download_images()`, `download_file()`, `handle_and_save_response()`
- **Dependencies**: curl_cffi, aiofiles, utils modules
- **Concurrency**: Uses semaphore to limit concurrent downloads
- **Error Handling**: Retry mechanism with exponential backoff

#### `core/duplicates.py`
**Responsibility**: Duplicate detection and processing
- **Key Functions**: `handle_duplicates()`, `uniquify_duplicates()`, `uniquify_all_images()`
- **Algorithm**: Multi-hash comparison (phash, dhash, average_hash)
- **Performance**: O(n log n) optimization using hash indexing
- **Safety**: Backup creation before modifications

#### `core/image_utils.py`
**Responsibility**: Image processing and hashing
- **Key Functions**: `process_and_save_image_sync()`, `get_file_hashes()`, modification functions
- **Formats**: JPEG, PNG, WebP, GIF support
- **Optimization**: Executor usage for CPU-bound operations
- **Quality**: Configurable image quality settings

### Utility Modules

#### `utils/config_manager.py`
**Responsibility**: Configuration management
- **Features**: JSON/YAML support, validation, profiles
- **Pattern**: Singleton-like global instance
- **Flexibility**: Runtime configuration updates
- **Safety**: Configuration validation and fallbacks

#### `utils/session_manager.py`
**Responsibility**: Download session management
- **Features**: Pause/resume, progress persistence
- **State**: JSON-based state storage
- **Recovery**: Automatic session restoration
- **Control**: User interaction handling

#### `utils/progress.py`
**Responsibility**: Progress tracking and display
- **UI**: Rich progress bars with statistics
- **Async**: Non-blocking progress updates
- **Flexibility**: Multiple progress bar styles
- **Information**: Speed, ETA, completion statistics

### UI Modules

#### `ui/cli.py`
**Responsibility**: Command-line interface
- **Modes**: Interactive and command-line modes
- **Validation**: Input validation and error messages
- **Help**: Comprehensive help system
- **Integration**: Seamless integration with core modules

## ⚙️ Configuration System

### Configuration Hierarchy

```mermaid
graph TD
    A[Command Line Arguments] --> B[Environment Variables]
    B --> C[Configuration Files]
    C --> D[Configuration Profiles]
    D --> E[Default Values]
    
    F[Final Configuration] <-- A
    F <-- B
    F <-- C
    F <-- D
    F <-- E
    
    style A fill:#ff9800
    style F fill:#4caf50
```

### Configuration Structure

```yaml
# Example configuration structure
download:
  max_concurrent_downloads: 50
  download_timeout: 30
  default_retries: 3
  enable_pause_resume: true

paths:
  image_dir: "./images"
  temp_dir: "./temp"
  log_file: "app.log"

validation:
  max_download_size_mb: 100
  min_file_size: 100
  allowed_schemes: ["http", "https"]

duplicates:
  similarity_threshold: 2
  max_uniquify_attempts: 10
  auto_confirm_operations: false

ui:
  show_welcome_message: true
  progress_bar_style: "default"
  error_details_level: "medium"
```

## 🚨 Error Handling Strategy

### Error Classification

1. **Network Errors**: Connection timeouts, HTTP errors
2. **File System Errors**: Permission issues, disk space
3. **Image Processing Errors**: Corrupted files, unsupported formats
4. **Validation Errors**: Invalid URLs, configuration errors
5. **Resource Errors**: Memory exhaustion, file descriptor limits

### Recovery Strategies

- **Automatic Retry**: For transient network errors
- **Graceful Degradation**: Continue processing other items
- **User Notification**: Clear error messages and suggestions
- **State Preservation**: Save progress for resumption
- **Fallback Options**: Alternative processing methods

## 🚀 Performance Considerations

### Concurrency Model

```mermaid
graph LR
    A[Main Thread] --> B[Async Event Loop]
    B --> C[Download Tasks]
    B --> D[Progress Updates]
    B --> E[User Interface]
    
    C --> F[Network I/O]
    C --> G[File I/O]
    C --> H[Image Processing]
    
    F --> I[Semaphore Limited]
    G --> I
    H --> J[Executor Pool]
    
    style B fill:#e3f2fd
    style I fill:#fff3e0
    style J fill:#f3e5f5
```

### Optimization Techniques

1. **Connection Pooling**: Reuse HTTP connections
2. **Semaphore Limiting**: Control concurrent operations
3. **Executor Usage**: CPU-bound tasks in separate threads
4. **Memory Management**: Streaming downloads, cleanup
5. **Hash Indexing**: O(n log n) duplicate detection
6. **Lazy Loading**: Load resources only when needed

### Resource Management

- **Memory**: Streaming downloads, periodic cleanup
- **File Descriptors**: Proper session management
- **CPU**: Balanced async/sync processing
- **Disk Space**: Temporary file cleanup
- **Network**: Rate limiting and retries

## 🔮 Future Architecture Plans

### Phase 1: Web Interface
```mermaid
graph TB
    A[FastAPI Backend] --> B[REST API]
    A --> C[WebSocket Real-time]
    B --> D[Core Logic]
    C --> D
    E[React Frontend] --> B
    E --> C
    F[Database] --> A
```

### Phase 2: Microservices
```mermaid
graph TB
    A[API Gateway] --> B[Download Service]
    A --> C[Processing Service]
    A --> D[Storage Service]
    B --> E[Message Queue]
    C --> E
    D --> E
    F[Database Cluster] --> B
    F --> C
    F --> D
```

### Phase 3: Cloud Native
```mermaid
graph TB
    A[Load Balancer] --> B[Kubernetes Cluster]
    B --> C[Download Pods]
    B --> D[Processing Pods]
    B --> E[API Pods]
    F[Object Storage] --> B
    G[Message Broker] --> B
    H[Monitoring] --> B
```

---

**Last Updated**: August 24, 2024  
**Version**: 2.1.1  
**Authors**: Project Contributors