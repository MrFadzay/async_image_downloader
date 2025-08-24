"""
Tests for user guidance and helper functions.
"""

import pytest
from unittest.mock import patch, mock_open
from io import StringIO
import sys

from utils.user_guidance import UserGuidance, InteractiveHelper


class TestUserGuidance:
    """Test cases for UserGuidance class."""

    def test_show_operation_tips_existing_operation(self, capsys):
        """Test showing tips for an existing operation."""
        UserGuidance.show_operation_tips("download")
        
        captured = capsys.readouterr()
        assert "ПОЛЕЗНЫЕ СОВЕТЫ - DOWNLOAD" in captured.out
        assert "💡 Совет:" in captured.out or "📋 Поддерживаемые форматы:" in captured.out

    def test_show_operation_tips_nonexistent_operation(self, capsys):
        """Test showing tips for a non-existent operation."""
        UserGuidance.show_operation_tips("nonexistent")
        
        captured = capsys.readouterr()
        # Should not print anything for non-existent operation
        assert captured.out == ""

    def test_show_welcome_message(self, capsys):
        """Test showing welcome message."""
        UserGuidance.show_welcome_message()
        
        captured = capsys.readouterr()
        assert "🌟" in captured.out
        assert "Добро пожаловать" in captured.out

    def test_show_help_for_issue_existing(self, capsys):
        """Test showing help for an existing issue."""
        UserGuidance.show_help_for_issue("no_images_found")
        
        captured = capsys.readouterr()
        assert "ПРОБЛЕМА:" in captured.out
        assert "Возможные решения:" in captured.out

    def test_show_help_for_issue_nonexistent(self, capsys):
        """Test showing help for a non-existent issue."""
        UserGuidance.show_help_for_issue("nonexistent_issue")
        
        captured = capsys.readouterr()
        # Should not print anything for non-existent issue
        assert captured.out == ""

    def test_get_operation_summary_download(self):
        """Test getting operation summary for download."""
        summary = UserGuidance.get_operation_summary("download", count=5)
        assert "📥 Скачивание 5 изображений" in summary

    def test_get_operation_summary_find_duplicates(self):
        """Test getting operation summary for find duplicates."""
        summary = UserGuidance.get_operation_summary("find_duplicates", directory="test_dir")
        assert "🔍 Поиск дубликатов в test_dir" in summary

    def test_get_operation_summary_unknown(self):
        """Test getting operation summary for unknown operation."""
        summary = UserGuidance.get_operation_summary("unknown_op")
        assert "⚙️ Выполнение операции: unknown_op" in summary

    def test_show_safety_warning_destructive_operation(self, capsys):
        """Test showing safety warning for destructive operations."""
        UserGuidance.show_safety_warning("uniquify")
        
        captured = capsys.readouterr()
        assert "ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ О БЕЗОПАСНОСТИ" in captured.out
        assert "НЕОБРАТИМЫ" in captured.out

    def test_show_safety_warning_safe_operation(self, capsys):
        """Test showing safety warning for safe operations."""
        UserGuidance.show_safety_warning("download")
        
        captured = capsys.readouterr()
        # Should not show warning for safe operations
        assert captured.out == ""

    def test_format_file_size_bytes(self):
        """Test formatting file size in bytes."""
        result = UserGuidance.format_file_size(512)
        assert "512.0 Б" in result

    def test_format_file_size_kb(self):
        """Test formatting file size in KB."""
        result = UserGuidance.format_file_size(1536)  # 1.5 KB
        assert "1.5 КБ" in result

    def test_format_file_size_mb(self):
        """Test formatting file size in MB."""
        result = UserGuidance.format_file_size(1572864)  # 1.5 MB
        assert "1.5 МБ" in result

    def test_format_file_size_gb(self):
        """Test formatting file size in GB."""
        result = UserGuidance.format_file_size(1610612736)  # 1.5 GB
        assert "1.5 ГБ" in result

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        result = UserGuidance.format_duration(45.5)
        assert "45.5 сек" in result

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        result = UserGuidance.format_duration(90)  # 1.5 minutes
        assert "1.5 мин" in result

    def test_format_duration_hours(self):
        """Test formatting duration in hours."""
        result = UserGuidance.format_duration(5400)  # 1.5 hours
        assert "1.5 ч" in result

    def test_show_performance_tips_no_items(self, capsys):
        """Test performance tips with zero items processed."""
        UserGuidance.show_performance_tips(10.0, 0)
        
        captured = capsys.readouterr()
        # Should not print anything when no items processed
        assert captured.out == ""

    def test_show_performance_tips_fast_processing(self, capsys):
        """Test performance tips with fast processing."""
        UserGuidance.show_performance_tips(5.0, 10)  # 0.5 sec per item
        
        captured = capsys.readouterr()
        assert "СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ:" in captured.out
        assert "0.50 сек" in captured.out

    def test_show_performance_tips_slow_processing(self, capsys):
        """Test performance tips with slow processing."""
        UserGuidance.show_performance_tips(30.0, 10)  # 3 sec per item
        
        captured = capsys.readouterr()
        assert "СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ:" in captured.out
        assert "СОВЕТЫ ДЛЯ УСКОРЕНИЯ:" in captured.out

    def test_get_progress_emoji_start(self):
        """Test progress emoji at start."""
        emoji = UserGuidance.get_progress_emoji(0.05)
        assert emoji == "🟦"

    def test_get_progress_emoji_low(self):
        """Test progress emoji at low progress."""
        emoji = UserGuidance.get_progress_emoji(0.2)
        assert emoji == "🟨"

    def test_get_progress_emoji_medium(self):
        """Test progress emoji at medium progress."""
        emoji = UserGuidance.get_progress_emoji(0.5)
        assert emoji == "🟧"

    def test_get_progress_emoji_high(self):
        """Test progress emoji at high progress."""
        emoji = UserGuidance.get_progress_emoji(0.8)
        assert emoji == "🟩"

    def test_get_progress_emoji_complete(self):
        """Test progress emoji at completion."""
        emoji = UserGuidance.get_progress_emoji(0.95)
        assert emoji == "✅"


class TestInteractiveHelper:
    """Test cases for InteractiveHelper class."""

    @patch('builtins.input', return_value='y')
    def test_ask_for_confirmation_with_info_yes(self, mock_input, capsys):
        """Test confirmation dialog with yes response."""
        info_lines = ["Test info 1", "Test info 2"]
        result = InteractiveHelper.ask_for_confirmation_with_info("Test message", info_lines)
        
        assert result is True
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "Test info 1" in captured.out
        assert "Test info 2" in captured.out

    @patch('builtins.input', return_value='n')
    def test_ask_for_confirmation_with_info_no(self, mock_input, capsys):
        """Test confirmation dialog with no response."""
        info_lines = ["Test info"]
        result = InteractiveHelper.ask_for_confirmation_with_info("Test message", info_lines)
        
        assert result is False

    @patch('builtins.input', return_value='yes')
    def test_ask_for_confirmation_with_info_yes_full(self, mock_input):
        """Test confirmation dialog with 'yes' response."""
        result = InteractiveHelper.ask_for_confirmation_with_info("Test", [])
        assert result is True

    @patch('builtins.input', return_value='no')
    def test_ask_for_confirmation_with_info_no_full(self, mock_input):
        """Test confirmation dialog with 'no' response."""
        result = InteractiveHelper.ask_for_confirmation_with_info("Test", [])
        assert result is False

    @patch('builtins.input', side_effect=['invalid', 'y'])
    def test_ask_for_confirmation_with_info_invalid_then_yes(self, mock_input, capsys):
        """Test confirmation dialog with invalid input then yes."""
        result = InteractiveHelper.ask_for_confirmation_with_info("Test", [])
        
        assert result is True
        captured = capsys.readouterr()
        assert "Пожалуйста, введите" in captured.out