"""
Pytest configuration and shared fixtures for async image downloader tests.
"""
import asyncio
import tempfile
import pytest
from pathlib import Path
from typing import AsyncGenerator, Generator, List, Any
from unittest.mock import Mock, AsyncMock

# Test configuration
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_dir() -> AsyncGenerator[Path, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_image_urls() -> List[str]:
    """Sample image URLs for testing."""
    return [
        "https://httpbin.org/image/jpeg",
        "https://httpbin.org/image/png", 
        "https://httpbin.org/image/webp"
    ]


@pytest.fixture
def invalid_urls() -> List[str]:
    """Invalid URLs for testing validation."""
    return [
        "file:///etc/passwd",
        "ftp://example.com/file.jpg",
        "http://localhost/image.jpg",
        "http://192.168.1.1/image.jpg",
        "not-a-url-at-all"
    ]


@pytest.fixture
def mock_response() -> Mock:
    """Mock HTTP response for testing."""
    mock = Mock()
    mock.status_code = 200
    mock.headers = {'content-type': 'image/jpeg'}
    mock.content = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG header
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async session for testing."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_image_data() -> bytes:
    """Sample image data for testing."""
    # Create a minimal valid JPEG (1x1 pixel) that PIL can process
    # This is a real JPEG file encoded as bytes
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
        0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
        0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
        0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x80, 0xFF, 0xD9
    ])


@pytest.fixture
def large_image_data() -> bytes:
    """Large image data for testing size limits."""
    # Create data larger than MAX_IMAGE_SIZE
    return b'\xff\xd8\xff\xe0' + b'x' * (60 * 1024 * 1024)  # 60MB


@pytest.fixture
def small_image_data() -> bytes:
    """Small image data for testing minimum size."""
    return b'\xff\xd8\xff\xe0\x00\x10'  # 6 bytes


class AsyncContextManager:
    """Helper class for async context manager testing."""
    
    def __init__(self, mock_object: Any) -> None:
        self.mock_object = mock_object
        
    async def __aenter__(self) -> Any:
        return self.mock_object
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


@pytest.fixture
def async_context_manager() -> type[AsyncContextManager]:
    """Factory for creating async context managers in tests."""
    return AsyncContextManager


# Configure test markers
def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "async_test: marks tests as async tests"
    )
    config.addinivalue_line(
        "markers", "network: marks tests as requiring network access"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )