"""
Unit tests for image hashing and duplicate detection functions.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image
import numpy as np

from core.image_utils import (
    _calculate_perceptual_hash_sync,
    get_file_hashes,
    get_image_files,
    process_and_save_image_sync
)
from utils.config import SIMILARITY_THRESHOLD


class TestImageHashing:
    """Test cases for image hashing functions."""
    
    @pytest.mark.unit
    def test_calculate_perceptual_hash_sync_success(self, temp_dir):
        """Test successful hash calculation for a valid image."""
        # Create a simple test image
        image_path = temp_dir / "test_image.jpg"
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_path, format='JPEG')
        
        # Calculate hash
        result = _calculate_perceptual_hash_sync(image_path)
        
        # Verify result structure
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        phash, dhash, ahash = result
        assert isinstance(phash, str)
        assert isinstance(dhash, str) 
        assert isinstance(ahash, str)
        
        # Hashes should be non-empty
        assert len(phash) > 0
        assert len(dhash) > 0
        assert len(ahash) > 0
    
    @pytest.mark.unit
    def test_calculate_perceptual_hash_sync_file_not_found(self):
        """Test hash calculation with non-existent file."""
        non_existent_path = Path("non_existent_file.jpg")
        result = _calculate_perceptual_hash_sync(non_existent_path)
        assert result is None
    
    @pytest.mark.unit
    def test_calculate_perceptual_hash_sync_invalid_image(self, temp_dir):
        """Test hash calculation with invalid image file."""
        # Create a text file with .jpg extension
        invalid_image_path = temp_dir / "invalid_image.jpg"
        invalid_image_path.write_text("This is not an image")
        
        result = _calculate_perceptual_hash_sync(invalid_image_path)
        assert result is None
    
    @pytest.mark.unit
    def test_hash_consistency(self, temp_dir):
        """Test that identical images produce identical hashes."""
        # Create identical images
        image_path1 = temp_dir / "image1.jpg"
        image_path2 = temp_dir / "image2.jpg"
        
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(image_path1, format='JPEG')
        image.save(image_path2, format='JPEG')
        
        # Calculate hashes
        hash1 = _calculate_perceptual_hash_sync(image_path1)
        hash2 = _calculate_perceptual_hash_sync(image_path2)
        
        # Hashes should be identical
        assert hash1 == hash2
    
    @pytest.mark.unit
    def test_hash_difference(self, temp_dir):
        """Test that different images produce different hashes."""
        # Create different images
        image_path1 = temp_dir / "red_image.jpg"
        image_path2 = temp_dir / "blue_image.jpg"
        
        red_image = Image.new('RGB', (100, 100), color='red')
        blue_image = Image.new('RGB', (100, 100), color='blue')
        
        red_image.save(image_path1, format='JPEG')
        blue_image.save(image_path2, format='JPEG')
        
        # Calculate hashes
        hash1 = _calculate_perceptual_hash_sync(image_path1)
        hash2 = _calculate_perceptual_hash_sync(image_path2)
        
        # Hashes should be different
        assert hash1 != hash2


class TestGetFileHashes:
    """Test cases for get_file_hashes function."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_hashes_empty_directory(self, temp_dir):
        """Test get_file_hashes with empty directory."""
        unique_hashes, duplicates = await get_file_hashes(temp_dir)
        
        assert isinstance(unique_hashes, dict)
        assert isinstance(duplicates, list)
        assert len(unique_hashes) == 0
        assert len(duplicates) == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_hashes_single_image(self, temp_dir):
        """Test get_file_hashes with single image."""
        # Create test image
        image_path = temp_dir / "test.jpg"
        image = Image.new('RGB', (100, 100), color='green')
        image.save(image_path, format='JPEG')
        
        unique_hashes, duplicates = await get_file_hashes(temp_dir)
        
        assert len(unique_hashes) == 1
        assert len(duplicates) == 0
        
        # Check hash structure
        hash_key = list(unique_hashes.keys())[0]
        assert len(hash_key) == 3  # phash, dhash, ahash
        assert unique_hashes[hash_key] == image_path
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_hashes_identical_images(self, temp_dir):
        """Test get_file_hashes with identical images (duplicates)."""
        # Create identical images
        image1_path = temp_dir / "image1.jpg"
        image2_path = temp_dir / "image2.jpg"
        
        image = Image.new('RGB', (100, 100), color='purple')
        image.save(image1_path, format='JPEG')
        image.save(image2_path, format='JPEG')
        
        unique_hashes, duplicates = await get_file_hashes(temp_dir)
        
        # Should have one unique image and one duplicate
        assert len(unique_hashes) == 1
        assert len(duplicates) == 1
        
        # Check duplicate structure
        duplicate_path, duplicate_hash, original_path = duplicates[0]
        assert duplicate_path in [image1_path, image2_path]
        assert original_path in [image1_path, image2_path]
        assert duplicate_path != original_path
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_hashes_different_images(self, temp_dir):
        """Test get_file_hashes with different images."""
        # Create different images
        red_image_path = temp_dir / "red.jpg"
        green_image_path = temp_dir / "green.jpg"
        blue_image_path = temp_dir / "blue.jpg"
        
        Image.new('RGB', (100, 100), color='red').save(red_image_path, format='JPEG')
        Image.new('RGB', (100, 100), color='green').save(green_image_path, format='JPEG')
        Image.new('RGB', (100, 100), color='blue').save(blue_image_path, format='JPEG')
        
        unique_hashes, duplicates = await get_file_hashes(temp_dir)
        
        # Should have three unique images and no duplicates
        assert len(unique_hashes) == 3
        assert len(duplicates) == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_file_hashes_ignores_non_images(self, temp_dir):
        """Test that non-image files are ignored."""
        # Create image and non-image files
        image_path = temp_dir / "test.jpg"
        text_path = temp_dir / "test.txt"
        hidden_path = temp_dir / ".hidden_file"
        
        Image.new('RGB', (100, 100), color='yellow').save(image_path, format='JPEG')
        text_path.write_text("This is a text file")
        hidden_path.write_text("Hidden file")
        
        unique_hashes, duplicates = await get_file_hashes(temp_dir)
        
        # Should only process the image file
        assert len(unique_hashes) == 1
        assert len(duplicates) == 0


class TestGetImageFiles:
    """Test cases for get_image_files function."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_image_files_empty_directory(self, temp_dir):
        """Test get_image_files with empty directory."""
        image_files = await get_image_files(temp_dir)
        assert isinstance(image_files, list)
        assert len(image_files) == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_image_files_with_images(self, temp_dir):
        """Test get_image_files with various image formats."""
        # Create different image files
        jpg_path = temp_dir / "test.jpg"
        png_path = temp_dir / "test.png"
        gif_path = temp_dir / "test.gif"
        txt_path = temp_dir / "test.txt"
        
        # Create actual image files
        Image.new('RGB', (50, 50), color='red').save(jpg_path, format='JPEG')
        Image.new('RGB', (50, 50), color='green').save(png_path, format='PNG')
        Image.new('RGB', (50, 50), color='blue').save(gif_path, format='GIF')
        txt_path.write_text("Not an image")
        
        image_files = await get_image_files(temp_dir)
        
        # Should find only image files
        assert len(image_files) == 3
        image_file_names = {f.name for f in image_files}
        assert "test.jpg" in image_file_names
        assert "test.png" in image_file_names
        assert "test.gif" in image_file_names
        assert "test.txt" not in image_file_names
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_image_files_ignores_hidden_files(self, temp_dir):
        """Test that hidden files are ignored."""
        # Create visible and hidden files
        visible_image = temp_dir / "visible.jpg"
        hidden_image = temp_dir / ".hidden.jpg"
        
        Image.new('RGB', (50, 50), color='red').save(visible_image, format='JPEG')
        Image.new('RGB', (50, 50), color='blue').save(hidden_image, format='JPEG')
        
        image_files = await get_image_files(temp_dir)
        
        # Should only find visible image
        assert len(image_files) == 1
        assert image_files[0].name == "visible.jpg"


class TestProcessAndSaveImageSync:
    """Test cases for process_and_save_image_sync function."""
    
    @pytest.mark.unit
    def test_process_and_save_image_sync_valid_jpeg(self, temp_dir, sample_image_data):
        """Test processing and saving valid JPEG data."""
        output_path = temp_dir / "output.jpg"
        
        # Should not raise exception
        process_and_save_image_sync(sample_image_data, output_path, "image/jpeg")
        
        # File should be created
        assert output_path.exists()
        assert output_path.suffix == ".jpg"
    
    @pytest.mark.unit
    def test_process_and_save_image_sync_large_file(self, temp_dir, large_image_data):
        """Test processing large file that exceeds size limits."""
        output_path = temp_dir / "large.jpg"
        
        # Should raise ValueError due to size validation
        with pytest.raises(ValueError, match="Размер изображения превышает ограничения"):
            process_and_save_image_sync(large_image_data, output_path, "image/jpeg")
    
    @pytest.mark.unit
    def test_process_and_save_image_sync_invalid_extension(self, temp_dir, sample_image_data):
        """Test processing with invalid file extension."""
        output_path = temp_dir / "output.txt"
        
        # Should raise ValueError due to extension validation
        with pytest.raises(ValueError, match="Неподдерживаемое расширение файла"):
            process_and_save_image_sync(sample_image_data, output_path, "image/jpeg")
    
    @pytest.mark.unit
    def test_process_and_save_image_sync_invalid_data(self, temp_dir):
        """Test processing invalid image data."""
        output_path = temp_dir / "output.jpg"
        invalid_data = b"This is not image data"
        
        # Should handle invalid data gracefully and create .unknown file
        process_and_save_image_sync(invalid_data, output_path, "image/jpeg")
        
        # Original file should not exist, but .unknown file should
        assert not output_path.exists()
        unknown_file = output_path.parent / f"{output_path.name}.unknown"
        assert unknown_file.exists()


class TestSimilarityDetection:
    """Test cases for similarity detection logic."""
    
    @pytest.mark.unit
    def test_similarity_threshold_logic(self):
        """Test the similarity threshold logic."""
        # Test cases for similarity matching
        test_cases = [
            # (hash1, hash2, expected_match)
            (("a", "b", "c"), ("a", "b", "c"), True),  # Identical: 3/3 matches
            (("a", "b", "c"), ("a", "b", "d"), True),  # Similar: 2/3 matches >= threshold
            (("a", "b", "c"), ("a", "x", "y"), False),  # Different: 1/3 matches < threshold
            (("a", "b", "c"), ("x", "y", "z"), False),  # Completely different: 0/3 matches
        ]
        
        for hash1, hash2, expected_match in test_cases:
            matching_hashes = sum(1 for i in range(3) if hash1[i] == hash2[i])
            is_similar = matching_hashes >= SIMILARITY_THRESHOLD
            
            assert is_similar == expected_match, (
                f"Hash comparison failed: {hash1} vs {hash2}, "
                f"expected {expected_match}, got {is_similar}"
            )