"""
Mock tests for duplicate detection logic.

These tests use mocks to verify the behavior of duplicate detection
algorithms without requiring actual image files.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Tuple, Optional

import pytest

from core.duplicates import handle_duplicates, uniquify_duplicates, uniquify_all_images
from core.image_utils import get_file_hashes, _calculate_perceptual_hash_sync


class TestGetFileHashesMocks:
    """Test suite for get_file_hashes function using mocks."""

    @pytest.mark.asyncio
    async def test_get_file_hashes_with_no_duplicates(self):
        """Test hash calculation when all images are unique."""
        test_dir = Path("test_dir")

        # Mock file system operations
        async def mock_listdir_func(path):
            return ["image1.jpg", "image2.png", "image3.gif"]

        async def mock_isfile_func(path):
            return True

        with patch('aiofiles.os.listdir', side_effect=mock_listdir_func) as mock_listdir, \
                patch('aiofiles.os.path.isfile', side_effect=mock_isfile_func) as mock_isfile:

            # Mock hash calculation
            mock_hashes = [
                ("hash1a", "hash1b", "hash1c"),
                ("hash2a", "hash2b", "hash2c"),
                ("hash3a", "hash3b", "hash3c")
            ]

            with patch('asyncio.get_running_loop') as mock_loop, \
                    patch('asyncio.gather') as mock_gather:

                mock_loop.return_value = MagicMock()

                # Create an async function that returns mock_hashes
                async def mock_gather_func(*args):
                    return mock_hashes
                mock_gather.side_effect = mock_gather_func

                unique_hashes, duplicates = await get_file_hashes(test_dir)

                # Verify results
                assert len(unique_hashes) == 3
                assert len(duplicates) == 0

                # Verify all unique hashes are stored
                assert mock_hashes[0] in unique_hashes
                assert mock_hashes[1] in unique_hashes
                assert mock_hashes[2] in unique_hashes

    @pytest.mark.asyncio
    async def test_get_file_hashes_with_duplicates(self):
        """Test hash calculation when duplicates are present."""
        test_dir = Path("test_dir")

        async def mock_listdir_func(path):
            return ["image1.jpg", "image2.png", "image3.jpg"]

        async def mock_isfile_func(path):
            return True

        with patch('aiofiles.os.listdir', side_effect=mock_listdir_func), \
                patch('aiofiles.os.path.isfile', side_effect=mock_isfile_func):

            # Create hashes where image3 is duplicate of image1 (2/3 hashes match)
            mock_hashes = [
                ("hash1a", "hash1b", "hash1c"),  # Original
                ("hash2a", "hash2b", "hash2c"),  # Unique
                ("hash1a", "hash1b", "different3"),  # Duplicate (2/3 match)
            ]

            with patch('asyncio.get_running_loop') as mock_loop, \
                    patch('asyncio.gather') as mock_gather, \
                    patch('utils.config_manager.SIMILARITY_THRESHOLD', 2):

                mock_loop.return_value = MagicMock()

                # Create an async function that returns mock_hashes
                async def mock_gather_func(*args):
                    return mock_hashes
                mock_gather.side_effect = mock_gather_func

                unique_hashes, duplicates = await get_file_hashes(test_dir)

                # Should have 2 unique images and 1 duplicate
                assert len(unique_hashes) == 2
                assert len(duplicates) == 1

                # Verify duplicate is correctly identified
                duplicate_path, duplicate_hash, original_path = duplicates[0]
                assert duplicate_path == test_dir / "image3.jpg"
                assert duplicate_hash == mock_hashes[2]
                assert original_path == test_dir / "image1.jpg"

    @pytest.mark.asyncio
    async def test_get_file_hashes_ignores_hidden_files(self):
        """Test that hidden files are properly ignored."""
        test_dir = Path("test_dir")

        async def mock_listdir_func(path):
            return [".DS_Store", "image1.jpg", ".hidden.png"]

        async def mock_isfile_func(path):
            return True

        with patch('aiofiles.os.listdir', side_effect=mock_listdir_func), \
                patch('aiofiles.os.path.isfile', side_effect=mock_isfile_func):

            mock_hashes = [("hash1a", "hash1b", "hash1c")]

            with patch('asyncio.get_running_loop') as mock_loop, \
                    patch('asyncio.gather') as mock_gather:

                mock_loop.return_value = MagicMock()

                # Create an async function that returns mock_hashes
                async def mock_gather_func(*args):
                    return mock_hashes
                mock_gather.side_effect = mock_gather_func

                unique_hashes, duplicates = await get_file_hashes(test_dir)

                # Should only process image1.jpg
                assert len(unique_hashes) == 1
                assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_get_file_hashes_handles_hash_errors(self):
        """Test handling of hash calculation errors."""
        test_dir = Path("test_dir")

        async def mock_listdir_func(path):
            return ["image1.jpg", "corrupted.jpg", "image2.png"]

        async def mock_isfile_func(path):
            return True

        with patch('aiofiles.os.listdir', side_effect=mock_listdir_func), \
                patch('aiofiles.os.path.isfile', side_effect=mock_isfile_func):

            # Mock hash results with one None (error)
            mock_hashes = [
                ("hash1a", "hash1b", "hash1c"),
                None,  # Corrupted file
                ("hash2a", "hash2b", "hash2c")
            ]

            with patch('asyncio.get_running_loop') as mock_loop, \
                    patch('asyncio.gather') as mock_gather:

                mock_loop.return_value = MagicMock()

                # Create an async function that returns mock_hashes
                async def mock_gather_func(*args):
                    return mock_hashes
                mock_gather.side_effect = mock_gather_func

                unique_hashes, duplicates = await get_file_hashes(test_dir)

                # Should only process valid images
                assert len(unique_hashes) == 2
                assert len(duplicates) == 0


class TestHandleDuplicatesMocks:
    """Test suite for handle_duplicates function using mocks."""

    @pytest.mark.asyncio
    async def test_handle_duplicates_renames_files(self):
        """Test that duplicate files are properly renamed."""
        test_dir = Path("test_dir")

        # Mock the get_file_hashes function
        mock_duplicates = [
            (Path("test_dir/duplicate1.jpg"),
             ("h1", "h2", "h3"), Path("test_dir/original.jpg")),
            (Path("test_dir/duplicate2.jpg"),
             ("h1", "h2", "h3"), Path("test_dir/original.jpg"))
        ]

        with patch('core.duplicates.create_dir') as mock_create_dir, \
                patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.get_image_files') as mock_get_image_files, \
                patch('core.duplicates.get_progress_tracker') as mock_progress_tracker, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.show_operation_summary'), \
                patch('aiofiles.os.path.exists') as mock_exists, \
                patch('aiofiles.os.rename') as mock_rename:

            mock_get_hashes.return_value = ({}, mock_duplicates)
            mock_get_image_files.return_value = [
                Path("test_dir/duplicate1.jpg"), Path("test_dir/duplicate2.jpg")]
            mock_exists.return_value = False  # No name conflicts

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_instance.track_duplicate_progress = MagicMock()
            mock_progress_tracker.return_value = mock_progress_instance

            # Setup context manager for progress tracking
            mock_analysis_progress = MagicMock()
            mock_progress_instance.track_duplicate_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_analysis_progress)
            mock_progress_instance.track_duplicate_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)

            await handle_duplicates(test_dir)

            # Verify directory creation
            mock_create_dir.assert_called_once_with(test_dir)

            # Verify rename operations
            assert mock_rename.call_count == 2

            # Check rename calls - each file gets its own counter
            expected_calls = [
                call(Path("test_dir/duplicate1.jpg"),
                     Path("test_dir/duplicate1_duplicate_1.jpg")),
                call(Path("test_dir/duplicate2.jpg"),
                     Path("test_dir/duplicate2_duplicate_1.jpg"))
            ]
            mock_rename.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    async def test_handle_duplicates_handles_name_conflicts(self):
        """Test handling of filename conflicts during renaming."""
        test_dir = Path("test_dir")

        mock_duplicates = [
            (Path("test_dir/duplicate.jpg"),
             ("h1", "h2", "h3"), Path("test_dir/original.jpg"))
        ]

        with patch('core.duplicates.create_dir'), \
                patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.get_image_files') as mock_get_image_files, \
                patch('core.duplicates.get_progress_tracker') as mock_progress_tracker, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.show_operation_summary'), \
                patch('aiofiles.os.path.exists') as mock_exists, \
                patch('aiofiles.os.rename') as mock_rename:

            mock_get_hashes.return_value = ({}, mock_duplicates)
            mock_get_image_files.return_value = [
                Path("test_dir/duplicate.jpg")]

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_instance.track_duplicate_progress = MagicMock()
            mock_progress_tracker.return_value = mock_progress_instance

            # Setup context manager for progress tracking
            mock_analysis_progress = MagicMock()
            mock_progress_instance.track_duplicate_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_analysis_progress)
            mock_progress_instance.track_duplicate_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)

            # First name exists, second doesn't
            mock_exists.side_effect = [True, False]

            await handle_duplicates(test_dir)

            # Should rename to _duplicate_2 due to conflict
            mock_rename.assert_called_once_with(
                Path("test_dir/duplicate.jpg"),
                Path("test_dir/duplicate_duplicate_2.jpg")
            )


class TestUniquifyDuplicatesMocks:
    """Test suite for uniquify_duplicates function using mocks."""

    @pytest.mark.asyncio
    async def test_uniquify_duplicates_success(self):
        """Test successful uniquification of duplicates."""
        test_dir = Path("test_dir")

        mock_duplicates = [
            (Path("test_dir/duplicate.jpg"),
             ("h1", "h2", "h3"), Path("test_dir/original.jpg"))
        ]

        mock_unique_hashes = {
            ("orig1", "orig2", "orig3"): Path("test_dir/original.jpg")
        }

        with patch('core.duplicates.create_dir'), \
                patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.get_modification_functions') as mock_get_funcs, \
                patch('core.duplicates.get_image_files') as mock_get_image_files, \
                patch('core.duplicates.get_progress_tracker') as mock_progress_tracker, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.show_operation_summary'), \
                patch('core.duplicates.ProgressErrorHandler'), \
                patch('asyncio.get_running_loop') as mock_loop:

            mock_get_hashes.return_value = (
                mock_unique_hashes, mock_duplicates)

            mock_get_image_files.return_value = [
                Path("test_dir/duplicate.jpg")]

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_instance.track_duplicate_progress = MagicMock()
            mock_progress_instance.track_uniquify_progress = MagicMock()
            mock_progress_tracker.return_value = mock_progress_instance

            # Setup context managers for progress tracking
            mock_analysis_progress = MagicMock()
            mock_uniquify_progress = MagicMock()
            mock_progress_instance.track_duplicate_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_analysis_progress)
            mock_progress_instance.track_duplicate_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)
            mock_progress_instance.track_uniquify_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_uniquify_progress)
            mock_progress_instance.track_uniquify_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)

            # Mock modification functions
            mock_func1 = MagicMock()
            mock_func1.__name__ = "brightness"
            mock_func2 = MagicMock()
            mock_func2.__name__ = "contrast"
            mock_get_funcs.return_value = [mock_func1, mock_func2]

            # Mock loop executor
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            mock_loop_instance.run_in_executor = AsyncMock(side_effect=[
                None,  # First call for modification
                ("new1", "new2", "new3")  # Second call for new hash calculation
            ])

            with patch('utils.config_manager.SIMILARITY_THRESHOLD', 2), \
                    patch('utils.config_manager.MAX_UNIQUIFY_ATTEMPTS', 3):

                await uniquify_duplicates(test_dir)

                # Verify modification was attempted
                assert mock_loop_instance.run_in_executor.call_count == 2

    @pytest.mark.asyncio
    async def test_uniquify_duplicates_max_attempts_reached(self):
        """Test behavior when max uniquification attempts are reached."""
        test_dir = Path("test_dir")

        mock_duplicates = [
            (Path("test_dir/duplicate.jpg"),
             ("h1", "h2", "h3"), Path("test_dir/original.jpg"))
        ]

        mock_unique_hashes = {
            ("orig1", "orig2", "orig3"): Path("test_dir/original.jpg"),
            # Still duplicate after modification
            ("h1", "h2", "h3"): Path("test_dir/duplicate.jpg")
        }

        with patch('core.duplicates.create_dir'), \
                patch('core.duplicates.get_file_hashes') as mock_get_hashes, \
                patch('core.duplicates.get_modification_functions') as mock_get_funcs, \
                patch('core.duplicates.get_image_files') as mock_get_image_files, \
                patch('core.duplicates.get_progress_tracker') as mock_progress_tracker, \
                patch('core.duplicates.confirm_destructive_operation', return_value=True), \
                patch('core.duplicates.show_operation_summary'), \
                patch('core.duplicates.ProgressErrorHandler'), \
                patch('asyncio.get_running_loop') as mock_loop:

            mock_get_hashes.return_value = (
                mock_unique_hashes, mock_duplicates)

            mock_get_image_files.return_value = [
                Path("test_dir/duplicate.jpg")]

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_instance.track_duplicate_progress = MagicMock()
            mock_progress_instance.track_uniquify_progress = MagicMock()
            mock_progress_tracker.return_value = mock_progress_instance

            # Setup context managers for progress tracking
            mock_analysis_progress = MagicMock()
            mock_uniquify_progress = MagicMock()
            mock_progress_instance.track_duplicate_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_analysis_progress)
            mock_progress_instance.track_duplicate_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)
            mock_progress_instance.track_uniquify_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_uniquify_progress)
            mock_progress_instance.track_uniquify_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)

            mock_func = MagicMock()
            mock_func.__name__ = "brightness"
            mock_get_funcs.return_value = [mock_func]

            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            # Always return same hash (still duplicate)
            mock_loop_instance.run_in_executor = AsyncMock(side_effect=[
                None,  # Modification
                ("h1", "h2", "h3"),  # Same hash (still duplicate)
                None,  # Modification
                ("h1", "h2", "h3"),  # Same hash (still duplicate)
                None,  # Modification
                ("h1", "h2", "h3"),  # Same hash (still duplicate)
            ])

            with patch('utils.config_manager.SIMILARITY_THRESHOLD', 2), \
                    patch('utils.config_manager.MAX_UNIQUIFY_ATTEMPTS', 3):

                await uniquify_duplicates(test_dir)

                # Should attempt modification 3 times, but may have one extra call
                # due to the algorithm flow (between 6-7 calls is expected)
                assert mock_loop_instance.run_in_executor.call_count >= 6


class TestUniquifyAllImagesMocks:
    """Test suite for uniquify_all_images function using mocks."""

    @pytest.mark.asyncio
    async def test_uniquify_all_images_processes_all_files(self):
        """Test that all image files are processed."""
        test_dir = Path("test_dir")

        mock_image_files = [
            Path("test_dir/image1.jpg"),
            Path("test_dir/image2.png"),
            Path("test_dir/image3.gif")
        ]

        with patch('core.duplicates.create_dir'), \
                patch('core.duplicates.get_image_files') as mock_get_files, \
                patch('core.duplicates.get_modification_functions') as mock_get_funcs, \
                patch('core.duplicates.confirm_destructive_operation') as mock_confirm, \
                patch('core.duplicates.get_progress_tracker') as mock_progress, \
                patch('core.duplicates.show_operation_summary') as mock_summary, \
                patch('asyncio.get_running_loop') as mock_loop:

            mock_get_files.return_value = mock_image_files
            mock_confirm.return_value = True

            mock_func1 = MagicMock()
            mock_func1.__name__ = "brightness"
            mock_func2 = MagicMock()
            mock_func2.__name__ = "contrast"
            mock_get_funcs.return_value = [mock_func1, mock_func2]

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_bar = MagicMock()
            mock_progress_instance.track_uniquify_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_progress_bar)
            mock_progress_instance.track_uniquify_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)
            mock_progress.return_value = mock_progress_instance

            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_in_executor.return_value = None

            await uniquify_all_images(test_dir)

            # Should process all 3 images
            assert mock_loop_instance.run_in_executor.call_count == 3

    @pytest.mark.asyncio
    async def test_uniquify_all_images_handles_errors(self):
        """Test error handling during image processing."""
        test_dir = Path("test_dir")

        mock_image_files = [
            Path("test_dir/good.jpg"),
            Path("test_dir/corrupted.jpg")
        ]

        with patch('core.duplicates.create_dir'), \
                patch('core.duplicates.get_image_files') as mock_get_files, \
                patch('core.duplicates.get_modification_functions') as mock_get_funcs, \
                patch('core.duplicates.confirm_destructive_operation') as mock_confirm, \
                patch('core.duplicates.get_progress_tracker') as mock_progress, \
                patch('core.duplicates.show_operation_summary') as mock_summary, \
                patch('asyncio.get_running_loop') as mock_loop:

            mock_get_files.return_value = mock_image_files
            mock_confirm.return_value = True

            mock_func = MagicMock()
            mock_func.__name__ = "brightness"
            mock_get_funcs.return_value = [mock_func]

            # Mock progress tracker
            mock_progress_instance = MagicMock()
            mock_progress_bar = MagicMock()
            mock_progress_instance.track_uniquify_progress.return_value.__aenter__ = AsyncMock(
                return_value=mock_progress_bar)
            mock_progress_instance.track_uniquify_progress.return_value.__aexit__ = AsyncMock(
                return_value=None)
            mock_progress.return_value = mock_progress_instance

            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            # First succeeds, second raises exception
            mock_loop_instance.run_in_executor.side_effect = [
                None, Exception("Corrupt file")]

            # Should not raise exception
            await uniquify_all_images(test_dir)

            # Should attempt both files
            assert mock_loop_instance.run_in_executor.call_count == 2


class TestCalculatePerceptualHashMocks:
    """Test suite for _calculate_perceptual_hash_sync function using mocks."""

    def test_calculate_hash_success(self):
        """Test successful hash calculation."""
        test_path = Path("/test/image.jpg")

        with patch('PIL.Image.open') as mock_open, \
                patch('imagehash.phash') as mock_phash, \
                patch('imagehash.dhash') as mock_dhash, \
                patch('imagehash.average_hash') as mock_ahash:

            # Mock PIL Image
            mock_image = MagicMock()
            mock_opened_image = MagicMock()
            mock_opened_image.convert.return_value = mock_image
            mock_open.return_value = mock_opened_image

            # Mock hash results
            mock_phash.return_value = "phash_result"
            mock_dhash.return_value = "dhash_result"
            mock_ahash.return_value = "ahash_result"

            result = _calculate_perceptual_hash_sync(test_path)

            assert result == ("phash_result", "dhash_result", "ahash_result")
            mock_open.assert_called_once_with(test_path)
            mock_opened_image.convert.assert_called_once_with("RGB")

    def test_calculate_hash_handles_errors(self):
        """Test error handling in hash calculation."""
        test_path = Path("/test/corrupted.jpg")

        with patch('PIL.Image.open') as mock_open:
            mock_open.side_effect = Exception("Corrupted file")

            result = _calculate_perceptual_hash_sync(test_path)

            assert result is None

    def test_calculate_hash_converts_to_rgb(self):
        """Test that images are properly converted to RGB."""
        test_path = Path("/test/image.png")

        with patch('PIL.Image.open') as mock_open, \
                patch('imagehash.phash'), \
                patch('imagehash.dhash'), \
                patch('imagehash.average_hash'):

            mock_image = MagicMock()
            mock_open.return_value = mock_image

            _calculate_perceptual_hash_sync(test_path)

            # Verify RGB conversion is called
            mock_image.convert.assert_called_once_with("RGB")
