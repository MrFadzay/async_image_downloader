# Contributing to Async Image Downloader

Thank you for your interest in contributing to the Async Image Downloader project! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Release Process](#release-process)

## 🤝 Code of Conduct

This project follows a simple code of conduct:
- Be respectful and inclusive in all interactions
- Focus on constructive feedback and collaboration
- Help create a welcoming environment for contributors of all levels
- Follow professional communication standards

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** (Python 3.9+ recommended)
- **Git** for version control
- **pip** package manager
- (Optional) **PyInstaller** for building executables

### Quick Start for Contributors

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/async_image_downloader.git
   cd async_image_downloader
   ```
3. **Set up development environment** (see below)
4. **Create a feature branch**: `git checkout -b feature/your-feature-name`
5. **Make your changes** following our guidelines
6. **Test your changes** thoroughly
7. **Submit a pull request**

## 🛠 Development Environment Setup

### 1. Virtual Environment Setup

**Using venv (recommended):**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

**Using conda:**
```bash
conda create -n async-image-downloader python=3.9
conda activate async-image-downloader
```

### 2. Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies (includes testing, linting, etc.)
pip install -e .[dev]

# Or install all dependencies including docs and build tools
pip install -e .[all]
```

### 3. Verify Installation

```bash
# Test basic functionality
python main.py --help

# Run tests
pytest

# Run with coverage
pytest --cov=core --cov=utils --cov=ui
```

### 4. IDE Setup (Optional)

**Visual Studio Code:**
- Install Python extension
- Configure pylint/flake8 for linting
- Set up pytest for testing
- Enable black formatter

**PyCharm:**
- Configure Python interpreter to use your virtual environment
- Enable pytest as test runner
- Configure black as code formatter

## 📁 Project Structure

```
async_image_downloader/
├── core/                    # Core functionality
│   ├── downloader.py       # Image downloading logic
│   ├── duplicates.py       # Duplicate detection and handling
│   └── image_utils.py      # Image processing utilities
├── ui/                     # User interface modules
│   └── cli.py             # Command-line interface
├── utils/                  # Utility modules
│   ├── config.py          # Configuration constants
│   ├── config_manager.py  # Configuration management
│   ├── config_profiles.py # Pre-defined configuration profiles
│   ├── logger.py          # Logging utilities
│   ├── validation.py      # Input validation
│   ├── progress.py        # Progress tracking
│   ├── resource_manager.py # Resource management
│   ├── session_manager.py # Session management
│   ├── confirmation.py    # User confirmation dialogs
│   ├── error_handling.py  # Error handling utilities
│   └── user_guidance.py   # User guidance and tips
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Pytest configuration
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup configuration
├── pyproject.toml        # Modern Python packaging config
├── async_image_downloader.spec  # PyInstaller specification
└── README.md             # Project documentation
```

## 🔄 Development Workflow

### Branch Naming Convention

- **Feature branches**: `feature/description-of-feature`
- **Bug fixes**: `fix/description-of-bug`
- **Documentation**: `docs/description-of-changes`
- **Performance**: `perf/description-of-optimization`
- **Refactoring**: `refactor/description-of-changes`

### Commit Message Guidelines

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration

**Examples:**
```
feat(downloader): add retry mechanism for failed downloads
fix(duplicates): resolve memory leak in hash calculation
docs(readme): update installation instructions
test(validation): add unit tests for URL validation
```

## 📝 Coding Standards

### Python Style Guide

- Follow **PEP 8** style guidelines
- Use **black** for code formatting: `black .`
- Use **isort** for import sorting: `isort .`
- Use **type hints** for all function parameters and return values
- Maximum line length: **88 characters** (black default)

### Code Quality Tools

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .

# Type checking
mypy core/ utils/ ui/

# Security check
bandit -r .
```

### Naming Conventions

- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_single_leading_underscore`
- **Files and modules**: `snake_case.py`

### Documentation Standards

- All public functions must have **docstrings**
- Use **Google-style docstrings**
- Include **type hints** for all parameters
- Provide **usage examples** for complex functions

**Example:**
```python
async def download_file(
    session: AsyncSession,
    url: str,
    target_dir: Path,
    retries: int = 3
) -> bool:
    """
    Downloads a single image file asynchronously.
    
    Args:
        session: HTTP session for making requests
        url: URL of the image to download
        target_dir: Directory to save the downloaded file
        retries: Number of retry attempts on failure
    
    Returns:
        bool: True if download was successful, False otherwise
    
    Raises:
        ValueError: If URL is invalid or target_dir doesn't exist
    
    Examples:
        >>> async with AsyncSession() as session:
        ...     success = await download_file(
        ...         session, "https://example.com/image.jpg", 
        ...         Path("./downloads"), retries=3
        ...     )
        ...     print(f"Download successful: {success}")
    """
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions/methods in isolation
- **Integration tests**: Test component interactions
- **Test coverage**: Aim for >80% code coverage

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=utils --cov=ui --cov-report=html

# Run specific test files
pytest tests/unit/test_downloader.py

# Run tests with specific markers
pytest -m "not slow"  # Skip slow tests
pytest -m "unit"      # Run only unit tests
```

### Writing Tests

- Use **pytest** framework
- Use **async test functions** for async code
- Use **mocking** for external dependencies
- Use **fixtures** for common test data

**Example:**
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_download_file_success():
    """Test successful file download."""
    # Arrange
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = b"fake image data"
    mock_session.get.return_value = mock_response
    
    # Act
    result = await download_file(
        mock_session, "https://example.com/test.jpg", 
        Path("./test_dir")
    )
    
    # Assert
    assert result is True
    mock_session.get.assert_called_once()
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_validation_function():
    """Unit test for validation."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio 
async def test_download_workflow():
    """Integration test for download workflow."""
    pass

@pytest.mark.slow
def test_large_dataset():
    """Test that takes a long time to run."""
    pass
```

## 📖 Documentation Guidelines

### Types of Documentation

1. **Code Documentation**: Docstrings, inline comments
2. **User Documentation**: README, usage guides
3. **Developer Documentation**: Architecture, contributing guidelines
4. **API Documentation**: Auto-generated from docstrings

### Writing Guidelines

- Write documentation in **English**
- Use **clear and concise** language
- Provide **practical examples**
- Keep documentation **up-to-date** with code changes
- Use **Markdown** for all documentation files

### Building Documentation

```bash
# Install documentation dependencies
pip install -e .[docs]

# Build documentation (if Sphinx is set up)
cd docs/
make html

# View documentation
open _build/html/index.html
```

## 🔀 Pull Request Process

### Before Creating a PR

1. **Ensure all tests pass**: `pytest`
2. **Check code formatting**: `black . && isort .`
3. **Run linting**: `flake8 .`
4. **Update documentation** if needed
5. **Add tests** for new functionality

### PR Requirements

- **Clear title** describing the change
- **Detailed description** of what was changed and why
- **Link to related issues** if applicable
- **Screenshots** for UI changes (if any)
- **Test coverage** for new code
- **Documentation updates** for new features

### PR Template

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated existing tests as needed

## Checklist
- [ ] Code follows the project's style guidelines
- [ ] Self-review of the code was performed
- [ ] Documentation was updated
- [ ] No new warnings introduced
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Testing** in different environments
4. **Final approval** and merge

## 🐛 Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description** of the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, etc.)
- **Error messages** or logs
- **Screenshots** if applicable

### Feature Requests

For new features, please provide:

- **Use case** description
- **Proposed solution** or implementation
- **Alternatives considered**
- **Additional context** or examples

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `priority-high`: High priority issue
- `priority-low`: Low priority issue

## 🚀 Release Process

### Version Numbering

We follow **Semantic Versioning** (SemVer):
- **Major.Minor.Patch** (e.g., 2.1.1)
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Workflow

1. **Update version** in relevant files
2. **Update CHANGELOG.md** with new changes
3. **Create release notes**
4. **Tag the release**: `git tag v2.1.1`
5. **Build and test** the release
6. **Publish** to GitHub releases
7. **Deploy** executables and packages

### Changelog Format

```markdown
## [2.1.1] - 2024-08-24

### Added
- New configuration profiles for different use cases
- PyInstaller specification for executable builds

### Changed
- Improved error handling in download functions
- Enhanced configuration management system

### Fixed
- Fixed memory leak in duplicate detection
- Resolved path handling issues on Windows

### Removed
- Deprecated legacy configuration options
```

## 🎯 Areas for Contribution

### High Priority
- Performance optimizations
- Better error handling
- Additional image format support
- GUI implementation

### Medium Priority
- Additional configuration options
- More comprehensive testing
- Documentation improvements
- Code refactoring

### Good First Issues
- Documentation fixes
- Simple bug fixes
- Code formatting improvements
- Adding more examples

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: Primary channel for bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Reviews**: For getting feedback on your contributions

### Support

If you need help:

1. **Check existing documentation** and issues
2. **Search for similar problems** in the issue tracker
3. **Create a new issue** with detailed information
4. **Be patient and respectful** in all interactions

## 🙏 Recognition

Contributors will be recognized in:
- **CHANGELOG.md** for their contributions
- **README.md** contributors section (for significant contributions)
- **Release notes** for major features

Thank you for contributing to the Async Image Downloader project! Your contributions help make this tool better for everyone.

---

**Last updated**: August 24, 2024
**Version**: 2.1.1