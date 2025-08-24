"""
Integration tests for the download workflow.

These tests verify that all components work together correctly
in realistic scenarios.
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from curl_cffi import AsyncSession

from core.downloader import (
    download_file,
    download_images,
    run_download_session,
    handle_and_save_response
)
from utils.resource_manager import get_resource_manager


class TestDownloadWorkflow:
    """Integration tests for the complete download workflow."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_file_success_flow(self, temp_dir, mock_session, sample_image_data):
        """Test successful download of a single file."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = sample_image_data
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.raise_for_status = Mock()
        
        mock_session.get = AsyncMock(return_value=mock_response)
        
        # Mock the image processing to focus on workflow testing
        with patch('core.downloader.process_and_save_image_sync') as mock_process:
            # Setup semaphore
            semaphore = asyncio.Semaphore(5)
            
            # Test download
            url = "https://example.com/test.jpg"
            result = await download_file(
                session=mock_session,
                semaphore=semaphore,
                url=url,
                target_dir=temp_dir,
                file_index=1000,
                retries=3
            )
            
            # Verify success
            assert result is True
            
            # Verify image processing was called
            mock_process.assert_called_once()
            
            # Verify session was called correctly
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert call_args[0][0] == url
            assert 'User-Agent' in call_args[1]['headers']
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_file_retry_on_429(self, temp_dir, mock_session, sample_image_data):
        """Test retry behavior on 429 rate limit response."""
        # Setup mock responses: first 429, then success
        mock_error_response = Mock()
        mock_error_response.status_code = 429
        
        mock_success_response = Mock()
        mock_success_response.content = sample_image_data
        mock_success_response.headers = {'content-type': 'image/jpeg'}
        mock_success_response.raise_for_status = Mock()
        
        from curl_cffi.requests import errors
        error_with_response = errors.RequestsError("Rate limited")
        error_with_response.response = mock_error_response
        
        # First call raises 429, second succeeds
        mock_session.get = AsyncMock(side_effect=[error_with_response, mock_success_response])
        
        semaphore = asyncio.Semaphore(5)
        
        # Test download with retry
        url = "https://example.com/test.jpg"
        result = await download_file(
            session=mock_session,
            semaphore=semaphore,
            url=url,
            target_dir=temp_dir,
            file_index=1001,
            retries=3
        )
        
        # Should succeed after retry
        assert result is True
        
        # Should have made 2 calls (first failed, second succeeded)
        assert mock_session.get.call_count == 2
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_images_multiple_files(self, temp_dir, sample_image_data):
        """Test downloading multiple images concurrently."""
        urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg", 
            "https://example.com/image3.jpg"
        ]
        
        with patch('core.downloader.AsyncSession') as mock_session_class:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Setup mock response
            mock_response = Mock()
            mock_response.content = sample_image_data
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=mock_response)
            
            # Test download
            result = await download_images(
                session=mock_session,
                urls=urls,
                target_dir=temp_dir,
                start_index=2000,
                retries=2
            )
            
            # Should have downloaded all files
            assert result == 3
            
            # Should have created files for each URL
            created_files = list(temp_dir.glob("*.jpeg"))
            assert len(created_files) == 3
            
            # Verify session was called for each URL
            assert mock_session.get.call_count == 3
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_run_download_session_end_to_end(self, temp_dir, sample_image_data):
        """Test the complete download session workflow."""
        urls = ["https://example.com/test.jpg"]
        
        with patch('core.downloader.AsyncSession') as mock_session_class, \
             patch('core.downloader.IMAGE_DIR', temp_dir), \
             patch('core.downloader.DEFAULT_DOWNLOAD_DIR_NAME', 'test_downloads'):
            
            # Setup mock session
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Setup mock response
            mock_response = Mock()
            mock_response.content = sample_image_data
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=mock_response)
            
            # Test complete session
            await run_download_session(
                urls=urls,
                start_index=3000,
                retries=2
            )
            
            # Verify download directory was created
            download_dir = temp_dir / 'test_downloads'
            assert download_dir.exists()
            
            # Verify file was downloaded
            downloaded_files = list(download_dir.glob("*.jpeg"))
            assert len(downloaded_files) == 1
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_manager_integration(self, temp_dir, sample_image_data):
        """Test integration with resource manager during download."""
        resource_manager = get_resource_manager()
        initial_memory = resource_manager.get_memory_usage()
        
        with patch('core.downloader.AsyncSession') as mock_session_class:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Setup mock response  
            mock_response = Mock()
            mock_response.content = sample_image_data
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=mock_response)
            
            with patch('core.downloader.IMAGE_DIR', temp_dir), \
                 patch('core.downloader.DEFAULT_DOWNLOAD_DIR_NAME', 'managed_downloads'):
                
                # Run download session
                await run_download_session(
                    urls=["https://example.com/test.jpg"],
                    start_index=4000,
                    retries=1
                )
        
        # Verify memory tracking worked
        final_memory = resource_manager.get_memory_usage()
        assert isinstance(initial_memory, dict)
        assert isinstance(final_memory, dict)
        assert 'rss_mb' in initial_memory
        assert 'rss_mb' in final_memory


class TestHandleAndSaveResponse:
    """Integration tests for response handling and saving."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_and_save_response_validation_chain(self, temp_dir, sample_image_data):
        """Test the complete validation chain in response handling."""
        headers = {'content-type': 'image/jpeg'}
        file_path = temp_dir / "test.jpeg"
        url = "https://example.com/test.jpg"
        
        # Test successful handling
        result = await handle_and_save_response(
            image_data=sample_image_data,
            headers=headers,
            full_path=file_path,
            url=url
        )
        
        assert result is True
        assert file_path.exists()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_and_save_response_size_validation(self, temp_dir, large_image_data):
        """Test size validation in response handling."""
        headers = {'content-type': 'image/jpeg'}
        file_path = temp_dir / "large.jpeg"
        url = "https://example.com/large.jpg"
        
        # Test rejection of large file
        result = await handle_and_save_response(
            image_data=large_image_data,
            headers=headers,
            full_path=file_path,
            url=url
        )
        
        assert result is False
        assert not file_path.exists()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_and_save_response_mime_validation(self, temp_dir, sample_image_data):
        """Test MIME type validation in response handling."""
        bad_headers = {'content-type': 'text/html'}
        file_path = temp_dir / "test.jpeg"
        url = "https://example.com/test.jpg"
        
        # Test rejection of wrong MIME type
        result = await handle_and_save_response(
            image_data=sample_image_data,
            headers=bad_headers,
            full_path=file_path,
            url=url
        )
        
        assert result is False
        assert not file_path.exists()


class TestDownloadErrorHandling:
    """Integration tests for error handling in download workflow."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_file_invalid_url_rejection(self, temp_dir):
        """Test that invalid URLs are rejected early."""
        mock_session = AsyncMock()
        semaphore = asyncio.Semaphore(5)
        
        # Test with dangerous URL
        dangerous_url = "file:///etc/passwd"
        result = await download_file(
            session=mock_session,
            semaphore=semaphore,
            url=dangerous_url,
            target_dir=temp_dir,
            file_index=5000,
            retries=3
        )
        
        # Should fail without making network request
        assert result is False
        mock_session.get.assert_not_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_file_network_error_handling(self, temp_dir):
        """Test handling of network errors."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=Exception("Network error"))
        
        semaphore = asyncio.Semaphore(5)
        
        # Test with network error
        url = "https://example.com/test.jpg"
        result = await download_file(
            session=mock_session,
            semaphore=semaphore,
            url=url,
            target_dir=temp_dir,
            file_index=5001,
            retries=1
        )
        
        # Should fail gracefully
        assert result is False
        
        # Should have attempted the request
        mock_session.get.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_url_list_handling(self, temp_dir):
        """Test handling of empty URL list."""
        with patch('core.downloader.IMAGE_DIR', temp_dir):
            # Should handle empty list gracefully
            await run_download_session(
                urls=[],
                start_index=6000,
                retries=1
            )
            
            # Should not create any files or crash
            created_files = list(temp_dir.glob("**/*"))
            downloaded_files = [f for f in created_files if f.is_file() and f.suffix == '.jpeg']
            assert len(downloaded_files) == 0


class TestConcurrencyAndSemaphores:
    """Integration tests for concurrency control and semaphore usage."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_semaphore_limits_concurrent_downloads(self, temp_dir, sample_image_data):
        """Test that semaphore correctly limits concurrent downloads."""
        # Create many URLs to test concurrency
        urls = [f"https://example.com/image{i}.jpg" for i in range(10)]
        
        # Track how many requests are active simultaneously
        active_requests = 0
        max_concurrent = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal active_requests, max_concurrent
            active_requests += 1
            max_concurrent = max(max_concurrent, active_requests)
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            active_requests -= 1
            
            # Return mock response
            mock_response = Mock()
            mock_response.content = sample_image_data
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.raise_for_status = Mock()
            return mock_response
        
        with patch('core.downloader.AsyncSession') as mock_session_class, \
             patch('core.downloader.MAX_CONCURRENT_DOWNLOADS', 3):  # Limit to 3 concurrent
            
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.get = mock_get
            
            # Test download with concurrency limit
            result = await download_images(
                session=mock_session,
                urls=urls,
                target_dir=temp_dir,
                start_index=7000,
                retries=1
            )
            
            # All downloads should succeed
            assert result == len(urls)
            
            # Should have respected concurrency limit
            assert max_concurrent <= 3