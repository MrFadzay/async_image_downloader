"""
Unit tests for URL validation and image modification functions.
"""
import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, patch

from utils.validation import (
    validate_url_security,
    validate_file_size,
    validate_image_size,
    validate_mime_type,
    validate_file_extension,
    validate_download_request
)
from core.image_utils import (
    _modify_brightness,
    _modify_contrast,
    _modify_crop,
    _modify_add_noise,
    get_modification_functions
)


class TestURLValidation:
    """Test cases for URL validation functions."""

    @pytest.mark.unit
    def test_validate_url_security_valid_urls(self):
        """Test validation of valid and safe URLs."""
        valid_urls = [
            "https://example.com/image.jpg",
            "http://example.com/path/to/image.png",
            "https://cdn.example.com/images/photo.jpeg",
            "http://subdomain.example.org/file.gif"
        ]

        for url in valid_urls:
            assert validate_url_security(url), f"URL should be valid: {url}"

    @pytest.mark.unit
    def test_validate_url_security_dangerous_schemes(self):
        """Test rejection of dangerous URL schemes."""
        dangerous_urls = [
            "file:///etc/passwd",
            "ftp://example.com/file.jpg",
            "javascript:alert('xss')",
            "data:image/jpeg;base64,/9j/4AAQ...",
        ]

        for url in dangerous_urls:
            assert not validate_url_security(
                url), f"URL should be invalid: {url}"

    @pytest.mark.unit
    def test_validate_url_security_local_addresses(self):
        """Test rejection of local/private IP addresses."""
        local_urls = [
            "http://localhost/image.jpg",
            "http://127.0.0.1/image.jpg",
            "http://0.0.0.0/image.jpg",
            "http://192.168.1.1/image.jpg",
            "http://10.0.0.1/image.jpg",
            "http://172.16.0.1/image.jpg",
        ]

        for url in local_urls:
            assert not validate_url_security(
                url), f"Local URL should be invalid: {url}"

    @pytest.mark.unit
    def test_validate_url_security_malformed_urls(self):
        """Test rejection of malformed URLs."""
        malformed_urls = [
            "not-a-url",
            "http://",
            "https://",
            "",
            None,
            "example.com/image.jpg",  # Missing scheme
        ]

        for url in malformed_urls:
            assert not validate_url_security(
                url), f"Malformed URL should be invalid: {url}"

    @pytest.mark.unit
    def test_validate_download_request_valid(self):
        """Test validation of valid download requests."""
        valid_url = "https://example.com/image.jpg"

        # Test without size
        assert validate_download_request(valid_url)

        # Test with valid size
        assert validate_download_request(valid_url, 1024 * 1024)  # 1MB

    @pytest.mark.unit
    def test_validate_download_request_invalid_url(self):
        """Test rejection of invalid URLs in download requests."""
        invalid_url = "file:///etc/passwd"
        assert not validate_download_request(invalid_url)

    @pytest.mark.unit
    def test_validate_download_request_large_size(self):
        """Test rejection of files that are too large."""
        valid_url = "https://example.com/image.jpg"
        large_size = 200 * 1024 * 1024  # 200MB (exceeds MAX_DOWNLOAD_SIZE)

        assert not validate_download_request(valid_url, large_size)


class TestFileSizeValidation:
    """Test cases for file size validation functions."""

    @pytest.mark.unit
    def test_validate_file_size_valid_sizes(self):
        """Test validation of valid file sizes."""
        valid_sizes = [
            1024,           # 1KB
            1024 * 1024,    # 1MB
            50 * 1024 * 1024,  # 50MB
        ]

        for size in valid_sizes:
            assert validate_file_size(size), f"Size should be valid: {size}"

    @pytest.mark.unit
    def test_validate_file_size_too_small(self):
        """Test rejection of files that are too small."""
        small_sizes = [0, 50, 99]  # Below MIN_FILE_SIZE (100)

        for size in small_sizes:
            assert not validate_file_size(
                size), f"Size should be invalid: {size}"

    @pytest.mark.unit
    def test_validate_file_size_too_large(self):
        """Test rejection of files that are too large."""
        large_sizes = [
            101 * 1024 * 1024,  # 101MB (exceeds MAX_DOWNLOAD_SIZE)
            500 * 1024 * 1024,  # 500MB
        ]

        for size in large_sizes:
            assert not validate_file_size(
                size), f"Size should be invalid: {size}"

    @pytest.mark.unit
    def test_validate_image_size_valid(self):
        """Test validation of valid image sizes for processing."""
        valid_sizes = [
            1024,           # 1KB
            10 * 1024 * 1024,  # 10MB
            49 * 1024 * 1024,  # 49MB (under MAX_IMAGE_SIZE)
        ]

        for size in valid_sizes:
            assert validate_image_size(
                size), f"Image size should be valid: {size}"

    @pytest.mark.unit
    def test_validate_image_size_too_large(self):
        """Test rejection of images that are too large for processing."""
        large_sizes = [
            51 * 1024 * 1024,  # 51MB (exceeds MAX_IMAGE_SIZE)
            100 * 1024 * 1024,  # 100MB
        ]

        for size in large_sizes:
            assert not validate_image_size(
                size), f"Image size should be invalid: {size}"


class TestMimeTypeValidation:
    """Test cases for MIME type validation."""

    @pytest.mark.unit
    def test_validate_mime_type_valid_types(self):
        """Test validation of valid image MIME types."""
        valid_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/tiff",
            "image/webp",
            "image/jpeg; charset=utf-8",  # With additional parameters
        ]

        for mime_type in valid_types:
            assert validate_mime_type(
                mime_type), f"MIME type should be valid: {mime_type}"

    @pytest.mark.unit
    def test_validate_mime_type_invalid_types(self):
        """Test rejection of invalid MIME types."""
        invalid_types = [
            "text/html",
            "application/json",
            "video/mp4",
            "audio/mpeg",
            "application/pdf",
            "text/plain",
            "",
            None,
        ]

        for mime_type in invalid_types:
            assert not validate_mime_type(
                mime_type), f"MIME type should be invalid: {mime_type}"


class TestFileExtensionValidation:
    """Test cases for file extension validation."""

    @pytest.mark.unit
    def test_validate_file_extension_valid_extensions(self):
        """Test validation of valid image file extensions."""
        valid_files = [
            "image.jpg",
            "photo.jpeg",
            "picture.png",
            "animation.gif",
            "bitmap.bmp",
            "document.tiff",
            "IMAGE.JPG",  # Case insensitive
            Path("path/to/file.png"),  # Path object
        ]

        for filename in valid_files:
            assert validate_file_extension(
                filename), f"Extension should be valid: {filename}"

    @pytest.mark.unit
    def test_validate_file_extension_invalid_extensions(self):
        """Test rejection of invalid file extensions."""
        invalid_files = [
            "document.txt",
            "video.mp4",
            "audio.mp3",
            "archive.zip",
            "script.py",
            "file_without_extension",
            "",
        ]

        for filename in invalid_files:
            assert not validate_file_extension(
                filename), f"Extension should be invalid: {filename}"


class TestImageModificationFunctions:
    """Test cases for image modification functions."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        # Создаем изображение с градиентом для лучшего тестирования модификаций
        image = Image.new('RGB', (100, 100))
        pixels = []
        for y in range(100):
            for x in range(100):
                # Создаем градиент от черного к белому
                value = int((x + y) * 255 / 200)
                pixels.append((value, value, value))
        image.putdata(pixels)
        return image

    @pytest.mark.unit
    def test_modify_brightness(self, sample_image):
        """Test brightness modification function."""
        original_image = sample_image.copy()
        modified_image = _modify_brightness(original_image)

        # Should return an Image object
        assert isinstance(modified_image, Image.Image)

        # Should have same dimensions
        assert modified_image.size == original_image.size

        # Should have same mode
        assert modified_image.mode == original_image.mode

        # Pixel values should be different (brightness changed)
        original_pixels = list(original_image.getdata())
        modified_pixels = list(modified_image.getdata())

        # Count different pixels instead of comparing entire lists
        different_pixels = sum(1 for orig, mod in zip(
            original_pixels, modified_pixels) if orig != mod)
        assert different_pixels > 0, f"Expected at least 1 different pixel, but found {different_pixels}"

    @pytest.mark.unit
    def test_modify_contrast(self, sample_image):
        """Test contrast modification function."""
        original_image = sample_image.copy()
        modified_image = _modify_contrast(original_image)

        # Should return an Image object
        assert isinstance(modified_image, Image.Image)

        # Should have same dimensions and mode
        assert modified_image.size == original_image.size
        assert modified_image.mode == original_image.mode

    @pytest.mark.unit
    def test_modify_crop(self, sample_image):
        """Test crop modification function."""
        original_image = sample_image.copy()
        modified_image = _modify_crop(original_image)

        # Should return an Image object
        assert isinstance(modified_image, Image.Image)

        # Should be smaller by 2 pixels in each dimension (1 pixel cropped from each side)
        original_width, original_height = original_image.size
        modified_width, modified_height = modified_image.size

        assert modified_width == original_width - 2
        assert modified_height == original_height - 2

    @pytest.mark.unit
    def test_modify_crop_small_image(self):
        """Test crop modification with very small image."""
        small_image = Image.new('RGB', (2, 2), color='blue')
        modified_image = _modify_crop(small_image)

        # Should return the same image without cropping (too small to crop)
        assert modified_image.size == small_image.size

    @pytest.mark.unit
    def test_modify_add_noise(self, sample_image):
        """Test noise addition function."""
        original_image = sample_image.copy()
        modified_image = _modify_add_noise(original_image)

        # Should return an Image object
        assert isinstance(modified_image, Image.Image)

        # Should have same dimensions and mode
        assert modified_image.size == original_image.size
        assert modified_image.mode == original_image.mode

        # At least one pixel should be different (noise added)
        original_pixels = list(original_image.getdata())
        modified_pixels = list(modified_image.getdata())

        # Count different pixels instead of comparing entire lists
        different_pixels = sum(1 for orig, mod in zip(
            original_pixels, modified_pixels) if orig != mod)
        assert different_pixels > 0, f"Expected at least 1 different pixel, but found {different_pixels}"

    @pytest.mark.unit
    def test_get_modification_functions(self):
        """Test that get_modification_functions returns all expected functions."""
        functions = get_modification_functions()

        # Should return a list
        assert isinstance(functions, list)

        # Should contain all modification functions
        assert len(functions) == 4

        # All items should be callable
        for func in functions:
            assert callable(func)

        # Verify function names
        function_names = [func.__name__ for func in functions]
        expected_names = [
            '_modify_brightness',
            '_modify_contrast',
            '_modify_crop',
            '_modify_add_noise'
        ]

        for expected_name in expected_names:
            assert expected_name in function_names


class TestImageModificationIntegration:
    """Integration tests for image modification workflow."""

    @pytest.mark.unit
    def test_multiple_modifications_preserve_image(self):
        """Test that applying multiple modifications preserves image integrity."""
        original_image = Image.new('RGB', (50, 50), color='green')

        # Apply all modification functions
        functions = get_modification_functions()
        modified_image = original_image.copy()

        for func in functions:
            modified_image = func(modified_image)

        # Should still be a valid image
        assert isinstance(modified_image, Image.Image)
        assert modified_image.mode == 'RGB'

        # Should have reasonable dimensions (might be smaller due to cropping)
        width, height = modified_image.size
        assert width > 0
        assert height > 0

    @pytest.mark.unit
    def test_modification_randomness(self):
        """Test that modifications produce different results due to randomness."""
        original_image = Image.new('RGB', (100, 100), color='purple')

        # Apply same modifications multiple times
        results = []
        for _ in range(5):
            modified = _modify_brightness(original_image.copy())
            modified = _modify_add_noise(modified)
            results.append(list(modified.getdata()))

        # Results should be different due to randomness
        first_result = results[0]
        different_results = [
            result for result in results[1:] if result != first_result]

        # At least some results should be different
        assert len(
            different_results) > 0, "Modifications should produce different results"
