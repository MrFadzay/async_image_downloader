"""
Additional tests for duplicates module to improve coverage.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image

from core.duplicates import (
    handle_duplicates,
    uniquify_duplicates,
    uniquify_all_images,
    _apply_modifications_and_save_sync
)
from core.image_utils import get_file_hashes


class TestHandleDuplicates:
    """Test cases for handle_duplicates function."""

    @pytest.fixture
    def temp_dir_with_images(self):
        """Create temporary directory with test images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some test image files
            for i in range(3):
                image = Image.new('RGB', (100, 100), color=(255, 0, 0))
                image_path = temp_path / f"test_{i}.jpg"
                image.save(image_path, 'JPEG')

            yield temp_path

    @pytest.mark.asyncio
    async def test_handle_duplicates_no_duplicates(self, temp_dir_with_images):
        """Test handle_duplicates when no duplicates exist."""
        # Mock get_file_hashes to return no duplicates
        with patch('core.duplicates.get_file_hashes') as mock_get_hashes:
            mock_get_hashes.return_value = ({}, [])  # No duplicates

            with patch('core.duplicates.logger') as mock_logger:
                await handle_duplicates(temp_dir_with_images)

                # Should log that no duplicates were found
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_handle_duplicates_with_duplicates(self, temp_dir_with_images):
        """Test handle_duplicates when duplicates exist."""
        # Create mock duplicate data
        original_path = temp_dir_with_images / "original.jpg"
        duplicate_path = temp_dir_with_images / "duplicate.jpg"

        # Create the files
        for path in [original_path, duplicate_path]:
            image = Image.new('RGB', (100, 100), color=(255, 0, 0))
            image.save(path, 'JPEG')

        mock_hashes = ("hash1", "hash2", "hash3")
        duplicates = [(duplicate_path, mock_hashes, original_path)]

        with patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True) as mock_confirm:
            mock_get_hashes.return_value = (
                {mock_hashes: original_path}, duplicates)

            await handle_duplicates(temp_dir_with_images)

            # Check if duplicate was renamed
            renamed_files = list(temp_dir_with_images.glob("*_duplicate_*"))
            assert len(renamed_files) > 0
            mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_duplicates_rename_collision(self, temp_dir_with_images):
        """Test handle_duplicates when rename collision occurs."""
        # Create files that will cause naming collision
        original_path = temp_dir_with_images / "test.jpg"
        duplicate_path = temp_dir_with_images / "test_copy.jpg"
        collision_path = temp_dir_with_images / "test_copy_duplicate_1.jpg"

        for path in [original_path, duplicate_path, collision_path]:
            image = Image.new('RGB', (100, 100), color=(255, 0, 0))
            image.save(path, 'JPEG')

        mock_hashes = ("hash1", "hash2", "hash3")
        duplicates = [(duplicate_path, mock_hashes, original_path)]

        with patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True):
            mock_get_hashes.return_value = (
                {mock_hashes: original_path}, duplicates)

            await handle_duplicates(temp_dir_with_images)

            # Should handle naming collision
            renamed_files = list(temp_dir_with_images.glob("*_duplicate_*"))
            assert len(renamed_files) >= 2


class TestUniquifyDuplicates:
    """Test cases for uniquify_duplicates function."""

    @pytest.fixture
    def temp_dir_with_duplicates(self):
        """Create temporary directory with duplicate images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create original and duplicate files
            original = temp_path / "original.jpg"
            duplicate = temp_path / "image_duplicate_1.jpg"

            for path in [original, duplicate]:
                image = Image.new('RGB', (100, 100), color=(255, 0, 0))
                image.save(path, 'JPEG')

            yield temp_path

    @pytest.mark.asyncio
    async def test_uniquify_duplicates_success(self, temp_dir_with_duplicates):
        """Test successful uniquify of duplicates."""
        with patch('core.duplicates.logger') as mock_logger:
            await uniquify_duplicates(temp_dir_with_duplicates)

            # Should log processing
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_uniquify_duplicates_no_duplicates(self, temp_dir_with_duplicates):
        """Test uniquify when no duplicate files exist."""
        with patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.logger') as mock_logger:
            # Mock to return no duplicates
            mock_get_hashes.return_value = ({}, [])

            await uniquify_duplicates(temp_dir_with_duplicates)

            # Should log that no duplicates were found
            mock_logger.info.assert_any_call("Дубликаты не найдены.")

    @pytest.mark.asyncio
    async def test_uniquify_duplicates_processing_error(self, temp_dir_with_duplicates):
        """Test uniquify when processing error occurs."""
        with patch('core.duplicates._attempt_uniquification') as mock_attempt, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.get_file_hashes') as mock_get_hashes:
            # Mock to return duplicates
            mock_hashes = ("hash1", "hash2", "hash3")
            duplicate_path = temp_dir_with_duplicates / "image_duplicate_1.jpg"
            original_path = temp_dir_with_duplicates / "original.jpg"
            duplicates = [(duplicate_path, mock_hashes, original_path)]
            mock_get_hashes.return_value = (
                {mock_hashes: original_path}, duplicates)

            # Mock attempt to raise exception
            mock_attempt.side_effect = Exception("Processing error")

            await uniquify_duplicates(temp_dir_with_duplicates)

            # Should call attempt uniquification
            mock_attempt.assert_called()


class TestUniquifyAllImages:
    """Test cases for uniquify_all_images function."""

    @pytest.fixture
    def temp_dir_with_images(self):
        """Create temporary directory with test images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some test image files
            for i in range(3):
                image = Image.new('RGB', (100, 100), color=(255, 0, 0))
                image_path = temp_path / f"test_{i}.jpg"
                image.save(image_path, 'JPEG')

            yield temp_path

    @pytest.mark.asyncio
    async def test_uniquify_all_images_success(self, temp_dir_with_images):
        """Test successful uniquify all images operation."""
        with patch('core.duplicates._apply_modifications_and_save_sync') as mock_apply, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.get_image_files') as mock_get_files, \
                patch('core.duplicates.logger') as mock_logger:
            # Mock to return some image files
            image_files = [temp_dir_with_images / "image1.jpg",
                           temp_dir_with_images / "image2.jpg"]
            mock_get_files.return_value = image_files

            await uniquify_all_images(temp_dir_with_images)

            # Should apply modifications for each image
            assert mock_apply.call_count == len(image_files)
            # Should log completion
            mock_logger.info.assert_any_call(
                f"Завершено. Уникализировано {len(image_files)} изображений.")

    @pytest.mark.asyncio
    async def test_uniquify_all_images_no_images(self):
        """Test uniquify all when no images exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch('core.duplicates.logger') as mock_logger:
                await uniquify_all_images(temp_path)

                # Should log that no images were found
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_uniquify_all_images_processing_error(self, temp_dir_with_images):
        """Test uniquify all images when processing error occurs."""
        with patch('core.duplicates._apply_modifications_and_save_sync') as mock_apply, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.get_image_files') as mock_get_files, \
                patch('core.duplicates.logger') as mock_logger:
            # Mock to return some image files
            image_files = [temp_dir_with_images / "image1.jpg"]
            mock_get_files.return_value = image_files
            mock_apply.side_effect = Exception("Processing error")

            await uniquify_all_images(temp_dir_with_images)

            # Should log error for failed image
            mock_logger.error.assert_any_call(
                f"  ОШИБКА при уникализации '{image_files[0]}': Processing error")


class TestApplyModificationsAndSaveSync:
    """Test cases for _apply_modifications_and_save_sync function."""

    @pytest.fixture
    def sample_image_path(self):
        """Create a sample image file."""
        import os
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()  # Закрываем файл сразу

        try:
            # Create and save a simple image
            image = Image.new('RGB', (100, 100), color=(255, 0, 0))
            image.save(temp_path, 'JPEG')

            yield temp_path
        finally:
            # Cleanup with error handling
            try:
                if temp_path.exists():
                    os.chmod(temp_path, 0o777)  # Убираем защиту от записи
                    temp_path.unlink()
            except (PermissionError, OSError):
                pass  # Игнорируем ошибки удаления в тестах

    def test_apply_modifications_and_save_sync_success(self, sample_image_path):
        """Test successful image modification and save."""
        from core.image_utils import get_modification_functions

        modification_functions = get_modification_functions()
        func1 = modification_functions[0]
        func2 = modification_functions[1] if len(
            modification_functions) > 1 else modification_functions[0]

        # Функция не возвращает значение, только модифицирует файл
        _apply_modifications_and_save_sync(sample_image_path, func1, func2)

        assert sample_image_path.exists()

    def test_apply_modifications_and_save_sync_max_attempts(self, sample_image_path):
        """Test modification with max attempts reached."""
        from core.image_utils import get_modification_functions

        modification_functions = get_modification_functions()
        func1 = modification_functions[0]
        func2 = modification_functions[1] if len(
            modification_functions) > 1 else modification_functions[0]

        # Mock the function to always fail
        with patch('core.duplicates.Image.open', side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                _apply_modifications_and_save_sync(
                    sample_image_path, func1, func2)

    def test_apply_modifications_and_save_sync_file_error(self):
        """Test modification with file that doesn't exist."""
        from core.image_utils import get_modification_functions

        modification_functions = get_modification_functions()
        func1 = modification_functions[0]
        func2 = modification_functions[1] if len(
            modification_functions) > 1 else modification_functions[0]

        non_existent_path = Path("/nonexistent/file.jpg")
        with pytest.raises(Exception):
            _apply_modifications_and_save_sync(non_existent_path, func1, func2)

    def test_apply_modifications_and_save_sync_image_error(self, sample_image_path):
        """Test modification when image processing fails."""
        from core.image_utils import get_modification_functions

        modification_functions = get_modification_functions()
        func1 = modification_functions[0]
        func2 = modification_functions[1] if len(
            modification_functions) > 1 else modification_functions[0]

        with patch('PIL.Image.open') as mock_open:
            mock_open.side_effect = Exception("Image error")

            with pytest.raises(Exception):
                _apply_modifications_and_save_sync(
                    sample_image_path, func1, func2)


class TestIntegrationScenarios:
    """Integration test scenarios for duplicates module."""

    @pytest.mark.asyncio
    async def test_full_duplicate_workflow(self):
        """Test complete duplicate detection and processing workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create identical images
            for i in range(2):
                image = Image.new('RGB', (100, 100), color=(255, 0, 0))
                image_path = temp_path / f"image_{i}.jpg"
                image.save(image_path, 'JPEG')

            with patch('core.duplicates.confirm_destructive_operation', return_value=True):
                # Step 1: Find duplicates
                await handle_duplicates(temp_path)

                # Check that duplicate was renamed
                duplicate_files = list(temp_path.glob("*_duplicate_*"))
                assert len(duplicate_files) > 0

                # Step 2: Uniquify duplicates
                await uniquify_duplicates(temp_path)

                # Files should still exist
                all_files = list(temp_path.glob("*.jpg"))
                assert len(all_files) >= 2

    @pytest.mark.asyncio
    async def test_uniquify_all_workflow(self):
        """Test uniquify all images workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some regular images
            for i in range(3):
                image = Image.new('RGB', (100, 100), color=(i*50, i*50, i*50))
                image_path = temp_path / f"image_{i}.jpg"
                image.save(image_path, 'JPEG')

            with patch('core.duplicates.confirm_destructive_operation', return_value=True):
                # Uniquify all images
                await uniquify_all_images(temp_path)

                # All files should still exist
                all_files = list(temp_path.glob("*.jpg"))
                assert len(all_files) == 3

    @pytest.mark.asyncio
    async def test_empty_directory_handling(self):
        """Test handling of empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test all functions with empty directory
            await handle_duplicates(temp_path)
            await uniquify_duplicates(temp_path)
            await uniquify_all_images(temp_path)

            # Should complete without errors
            assert temp_path.exists()

    @pytest.mark.asyncio
    async def test_mixed_file_types_directory(self):
        """Test handling directory with mixed file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create image file
            image = Image.new('RGB', (100, 100), color=(255, 0, 0))
            image_path = temp_path / "image.jpg"
            image.save(image_path, 'JPEG')

            # Create non-image file
            text_file = temp_path / "text.txt"
            text_file.write_text("This is not an image")

            # Should process only image files
            await handle_duplicates(temp_path)
            await uniquify_all_images(temp_path)

            # Both files should still exist
            assert image_path.exists()
            assert text_file.exists()
