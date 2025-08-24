"""
Tests for download session manager.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from utils.session_manager import DownloadSessionManager, DownloadSessionState


class TestDownloadSessionState:
    """Test cases for DownloadSessionState dataclass."""

    def test_session_state_creation(self):
        """Test creating a session state object."""
        state = DownloadSessionState(
            session_id="test_session",
            urls=["http://example.com/1.jpg"],
            start_index=1000,
            retries=3,
            target_dir="/test/dir",
            completed_urls=[],
            failed_urls=[],
            current_index=0,
            is_paused=False,
            created_at="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00",
            total_urls=1,
            completed_count=0
        )

        assert state.session_id == "test_session"
        assert len(state.urls) == 1
        assert state.start_index == 1000


@pytest.fixture
def temp_session_file():
    """Create a temporary session file path for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=True) as f:
        temp_path = Path(f.name)
    # File is automatically deleted, we just use the path
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


class TestDownloadSessionManager:
    """Test cases for DownloadSessionManager class."""

    @pytest.fixture
    def manager(self, temp_session_file):
        """Create a session manager with temporary file."""
        manager = DownloadSessionManager()
        manager.session_file = temp_session_file
        return manager

    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        """Test creating a new download session."""
        urls = ["http://example.com/1.jpg", "http://example.com/2.jpg"]
        session_id = await manager.create_session(urls, start_index=1000, retries=3)

        assert session_id.startswith("session_")
        assert manager.current_session is not None
        assert manager.current_session.urls == urls
        assert manager.current_session.start_index == 1000
        assert manager.current_session.total_urls == 2

    @pytest.mark.asyncio
    async def test_save_session(self, manager):
        """Test saving session to file."""
        # Create a session first
        urls = ["http://example.com/test.jpg"]
        await manager.create_session(urls)

        # Save should work without errors
        await manager.save_session()

        # File should exist and contain session data
        assert manager.session_file.exists()

        with open(manager.session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['urls'] == urls

    @pytest.mark.asyncio
    async def test_save_session_no_current_session(self, manager):
        """Test saving when no current session exists."""
        # Should not create file when no current session
        await manager.save_session()
        assert not manager.session_file.exists()

    @pytest.mark.asyncio
    async def test_load_session_existing_file(self, manager):
        """Test loading session from existing file."""
        # Create and save a session first
        urls = ["http://example.com/test.jpg"]
        session_id = await manager.create_session(urls)
        await manager.save_session()

        # Clear current session and load
        manager.current_session = None
        loaded_session = await manager.load_session()

        assert loaded_session is not None
        assert loaded_session.session_id == session_id
        assert loaded_session.urls == urls

    @pytest.mark.asyncio
    async def test_load_session_no_file(self, manager):
        """Test loading session when file doesn't exist."""
        result = await manager.load_session()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_session_specific_id(self, manager):
        """Test loading session with specific ID."""
        # Create and save a session
        urls = ["http://example.com/test.jpg"]
        session_id = await manager.create_session(urls)
        await manager.save_session()

        # Load with correct ID
        loaded_session = await manager.load_session(session_id)
        assert loaded_session is not None
        assert loaded_session.session_id == session_id

    @pytest.mark.asyncio
    async def test_load_session_wrong_id(self, manager):
        """Test loading session with wrong ID."""
        # Create and save a session
        await manager.create_session(["http://example.com/test.jpg"])
        await manager.save_session()

        # Try to load with wrong ID
        loaded_session = await manager.load_session("wrong_id")
        assert loaded_session is None

    @pytest.mark.asyncio
    async def test_update_progress_success(self, manager):
        """Test updating progress for successful download."""
        urls = ["http://example.com/1.jpg", "http://example.com/2.jpg"]
        await manager.create_session(urls)

        await manager.update_progress("http://example.com/1.jpg", True)

        assert "http://example.com/1.jpg" in manager.current_session.completed_urls
        assert manager.current_session.completed_count == 1
        assert manager.current_session.current_index == 1

    @pytest.mark.asyncio
    async def test_update_progress_failure(self, manager):
        """Test updating progress for failed download."""
        urls = ["http://example.com/1.jpg"]
        await manager.create_session(urls)

        await manager.update_progress("http://example.com/1.jpg", False)

        assert "http://example.com/1.jpg" in manager.current_session.failed_urls
        assert manager.current_session.completed_count == 0
        assert manager.current_session.current_index == 1

    @pytest.mark.asyncio
    async def test_update_progress_no_session(self, manager):
        """Test updating progress when no session exists."""
        # Should not raise error
        await manager.update_progress("http://example.com/test.jpg", True)

    def test_pause(self, manager):
        """Test pausing download session."""
        manager.pause()

        assert manager.is_paused is True
        assert not manager.pause_event.is_set()

    def test_pause_already_paused(self, manager):
        """Test pausing when already paused."""
        manager.is_paused = True
        manager.pause()

        assert manager.is_paused is True

    def test_resume(self, manager):
        """Test resuming download session."""
        manager.is_paused = True
        manager.pause_event.clear()

        manager.resume()

        assert manager.is_paused is False
        assert manager.pause_event.is_set()

    def test_resume_not_paused(self, manager):
        """Test resuming when not paused."""
        manager.resume()

        assert manager.is_paused is False

    def test_cancel(self, manager):
        """Test canceling download session."""
        manager.cancel()

        assert manager.cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_wait_if_paused_not_paused(self, manager):
        """Test wait_if_paused when not paused."""
        result = await manager.wait_if_paused()
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_if_paused_canceled(self, manager):
        """Test wait_if_paused when canceled."""
        manager.cancel_event.set()

        result = await manager.wait_if_paused()
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_if_paused_resumed(self, manager):
        """Test wait_if_paused when paused then resumed."""
        manager.pause()

        # Resume after a short delay
        async def resume_later():
            await asyncio.sleep(0.1)
            manager.resume()

        # Start resume task
        asyncio.create_task(resume_later())

        # Wait should return True after resume
        result = await manager.wait_if_paused()
        assert result is True

    def test_add_pause_callback(self, manager):
        """Test adding pause callback."""
        callback = MagicMock()
        manager.add_pause_callback(callback)

        assert callback in manager.pause_callbacks

    def test_add_resume_callback(self, manager):
        """Test adding resume callback."""
        callback = MagicMock()
        manager.add_resume_callback(callback)

        assert callback in manager.resume_callbacks

    def test_pause_callback_execution(self, manager):
        """Test that pause callbacks are executed."""
        callback = MagicMock()
        manager.add_pause_callback(callback)

        manager.pause()

        callback.assert_called_once()

    def test_resume_callback_execution(self, manager):
        """Test that resume callbacks are executed."""
        callback = MagicMock()
        manager.add_resume_callback(callback)

        manager.is_paused = True
        manager.resume()

        callback.assert_called_once()

    def test_pause_callback_error_handling(self, manager):
        """Test error handling in pause callbacks."""
        def failing_callback():
            raise Exception("Test error")

        manager.add_pause_callback(failing_callback)

        # Should not raise exception
        manager.pause()
        assert manager.is_paused is True

    def test_resume_callback_error_handling(self, manager):
        """Test error handling in resume callbacks."""
        def failing_callback():
            raise Exception("Test error")

        manager.add_resume_callback(failing_callback)
        manager.is_paused = True

        # Should not raise exception
        manager.resume()
        assert manager.is_paused is False

    def test_get_session_stats_no_session(self, manager):
        """Test getting session stats when no session exists."""
        stats = manager.get_session_stats()
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_session_stats_with_session(self, manager):
        """Test getting session stats with active session."""
        urls = ["http://example.com/1.jpg", "http://example.com/2.jpg"]
        await manager.create_session(urls)
        await manager.update_progress("http://example.com/1.jpg", True)

        stats = manager.get_session_stats()

        assert stats is not None
        assert stats['total_urls'] == 2
        assert stats['completed_count'] == 1
        assert stats['failed_count'] == 0
        assert stats['remaining_count'] == 1

    def test_cleanup_session(self, manager):
        """Test cleaning up session."""
        manager.current_session = MagicMock()
        manager.is_paused = True

        manager.cleanup_session()

        assert manager.current_session is None
        assert manager.is_paused is False
        assert manager.pause_event.is_set()
        assert not manager.cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_save_session_file_error(self, manager):
        """Test save session with file write error."""
        await manager.create_session(["http://example.com/test.jpg"])

        # Set an invalid path to cause error
        manager.session_file = Path("/invalid/path/session.json")

        # Should not raise exception
        await manager.save_session()

    @pytest.mark.asyncio
    async def test_load_session_invalid_json(self, manager):
        """Test loading session with invalid JSON."""
        # Write invalid JSON to file
        with open(manager.session_file, 'w') as f:
            f.write("invalid json content")

        result = await manager.load_session()
        assert result is None
