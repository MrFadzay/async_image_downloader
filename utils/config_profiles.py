"""
Предопределенные профили конфигурации для различных сценариев использования.
"""

from pathlib import Path
from typing import Dict, List
from dataclasses import replace

from utils.config_manager import (
    AppConfig,
    DownloadConfig,
    PathConfig,
    ValidationConfig,
    DuplicateConfig,
    UIConfig,
    ResourceConfig,
)
from utils.logger import logger


class ConfigProfiles:
    """Управление предопределенными профилями конфигурации."""

    @staticmethod
    def create_fast_download_profile() -> AppConfig:
        """
        Профиль для максимально быстрого скачивания.

        Оптимизирован для скорости:
        - Увеличенное количество одновременных загрузок
        - Минимальная валидация
        - Отключены подтверждения
        - Упрощенный UI

        Returns:
            AppConfig: Конфигурация для быстрого скачивания
        """
        return AppConfig(
            download=DownloadConfig(
                max_concurrent_downloads=100,  # Максимальная скорость
                download_timeout=15,  # Короткий таймаут
                default_retries=1,  # Минимум повторов
                default_start_index=1000,
                enable_pause_resume=False,  # Без пауз для скорости
                user_agent_rotation=True,
            ),
            paths=PathConfig(
                image_dir="./fast_downloads",
                download_dir_name="images",
                temp_dir="./temp",
                log_file="fast_download.log",
                session_file="fast_session.json",
            ),
            validation=ValidationConfig(
                max_download_size_mb=200,  # Больше лимиты
                max_image_size_mb=100,
                min_file_size=50,  # Меньше минимум
                allowed_schemes=["http", "https"],
                forbidden_domains=["localhost", "127.0.0.1"],
            ),
            duplicates=DuplicateConfig(
                similarity_threshold=5,  # Менее строгий
                max_uniquify_attempts=5,  # Меньше попыток
                auto_confirm_operations=True,  # Автоподтверждение
                create_backups=False,  # Без резервных копий
                backup_suffix=".bak",
            ),
            ui=UIConfig(
                show_welcome_message=False,  # Минимум сообщений
                show_operation_tips=False,
                show_safety_warnings=False,
                progress_bar_style="minimal",
                error_details_level="low",
            ),
            resources=ResourceConfig(
                memory_threshold_mb=2000,  # Больше памяти
                auto_cleanup_temp_files=True,
                max_temp_files=2000,
                gc_frequency=200,
            ),
            version="2.1.0-fast",
            created_at="",
            updated_at="",
        )

    @staticmethod
    def create_seo_optimization_profile() -> AppConfig:
        """
        Профиль для SEO-оптимизации изображений.

        Оптимизирован для качества и уникальности:
        - Строгая валидация
        - Обязательная уникализация
        - Подробные логи
        - Резервные копии

        Returns:
            AppConfig: Конфигурация для SEO-оптимизации
        """
        return AppConfig(
            download=DownloadConfig(
                max_concurrent_downloads=20,  # Умеренная скорость
                download_timeout=45,  # Больше времени
                default_retries=5,  # Больше попыток
                default_start_index=2000,  # Высокие индексы
                enable_pause_resume=True,
                user_agent_rotation=True,
            ),
            paths=PathConfig(
                image_dir="./seo_images",
                download_dir_name="optimized",
                temp_dir="./seo_temp",
                log_file="seo_optimization.log",
                session_file="seo_session.json",
            ),
            validation=ValidationConfig(
                max_download_size_mb=50,  # Строже лимиты
                max_image_size_mb=25,
                min_file_size=200,  # Больше минимум
                allowed_schemes=["https"],  # Только HTTPS
                forbidden_domains=["localhost", "127.0.0.1", "0.0.0.0", "example.com", "test.com"],
            ),
            duplicates=DuplicateConfig(
                similarity_threshold=1,  # Очень строгий
                max_uniquify_attempts=15,  # Больше попыток
                auto_confirm_operations=False,  # Ручное подтверждение
                create_backups=True,  # Обязательные бэкапы
                backup_suffix=".seo_backup",
            ),
            ui=UIConfig(
                show_welcome_message=True,
                show_operation_tips=True,
                show_safety_warnings=True,
                progress_bar_style="detailed",
                error_details_level="high",
            ),
            resources=ResourceConfig(
                memory_threshold_mb=800,  # Осторожно с памятью
                auto_cleanup_temp_files=False,  # Сохраняем временные файлы
                max_temp_files=500,
                gc_frequency=50,
            ),
            version="2.1.0-seo",
            created_at="",
            updated_at="",
        )

    @staticmethod
    def create_safe_processing_profile() -> AppConfig:
        """
        Профиль для безопасной обработки.

        Максимальная безопасность:
        - Консервативные настройки
        - Обязательные подтверждения
        - Подробное логирование
        - Резервные копии всего

        Returns:
            AppConfig: Конфигурация для безопасной обработки
        """
        return AppConfig(
            download=DownloadConfig(
                max_concurrent_downloads=10,  # Медленно но верно
                download_timeout=60,  # Много времени
                default_retries=3,
                default_start_index=5000,  # Безопасные индексы
                enable_pause_resume=True,
                user_agent_rotation=False,  # Не меняем User-Agent
            ),
            paths=PathConfig(
                image_dir="./safe_images",
                download_dir_name="verified",
                temp_dir="./safe_temp",
                log_file="safe_processing.log",
                session_file="safe_session.json",
            ),
            validation=ValidationConfig(
                max_download_size_mb=20,  # Очень строгие лимиты
                max_image_size_mb=10,
                min_file_size=500,  # Высокий минимум
                allowed_schemes=["https"],  # Только безопасный протокол
                forbidden_domains=[
                    "localhost",
                    "127.0.0.1",
                    "0.0.0.0",
                    "192.168.",
                    "10.",
                    "172.16.",
                    "172.17.",
                    "172.18.",
                    "172.19.",
                    "172.20.",
                    "172.21.",
                    "172.22.",
                    "172.23.",
                    "172.24.",
                    "172.25.",
                    "172.26.",
                    "172.27.",
                    "172.28.",
                    "172.29.",
                    "172.30.",
                    "172.31.",
                ],
            ),
            duplicates=DuplicateConfig(
                similarity_threshold=0,  # Максимально строгий
                max_uniquify_attempts=20,  # Много попыток
                auto_confirm_operations=False,  # Всегда спрашиваем
                create_backups=True,
                backup_suffix=".safe_backup",
            ),
            ui=UIConfig(
                show_welcome_message=True,
                show_operation_tips=True,
                show_safety_warnings=True,
                progress_bar_style="detailed",
                error_details_level="high",
            ),
            resources=ResourceConfig(
                memory_threshold_mb=500,  # Консервативно с памятью
                auto_cleanup_temp_files=False,  # Сохраняем все
                max_temp_files=200,
                gc_frequency=20,  # Частая очистка памяти
            ),
            version="2.1.0-safe",
            created_at="",
            updated_at="",
        )

    @staticmethod
    def create_bulk_processing_profile() -> AppConfig:
        """
        Профиль для массовой обработки больших объемов.

        Оптимизирован для пакетной обработки:
        - Балансированная скорость
        - Автоматизация процессов
        - Эффективное использование ресурсов
        - Подробные отчеты

        Returns:
            AppConfig: Конфигурация для массовой обработки
        """
        return AppConfig(
            download=DownloadConfig(
                max_concurrent_downloads=50,  # Сбалансированно
                download_timeout=30,
                default_retries=3,
                default_start_index=10000,  # Высокие индексы для массовой обработки
                enable_pause_resume=True,  # Важно для больших объемов
                user_agent_rotation=True,
            ),
            paths=PathConfig(
                image_dir="./bulk_processing",
                download_dir_name="batch_images",
                temp_dir="./bulk_temp",
                log_file="bulk_processing.log",
                session_file="bulk_session.json",
            ),
            validation=ValidationConfig(
                max_download_size_mb=75,  # Умеренные лимиты
                max_image_size_mb=40,
                min_file_size=100,
                allowed_schemes=["http", "https"],
                forbidden_domains=["localhost", "127.0.0.1"],
            ),
            duplicates=DuplicateConfig(
                similarity_threshold=2,  # Умеренная строгость
                max_uniquify_attempts=10,
                auto_confirm_operations=True,  # Автоматизация для массовой обработки
                create_backups=True,  # Безопасность важна
                backup_suffix=".bulk_backup",
            ),
            ui=UIConfig(
                show_welcome_message=False,  # Минимум отвлечений
                show_operation_tips=False,
                show_safety_warnings=True,  # Но предупреждения показываем
                progress_bar_style="default",
                error_details_level="medium",
            ),
            resources=ResourceConfig(
                memory_threshold_mb=1500,  # Много памяти для больших объемов
                auto_cleanup_temp_files=True,  # Автоочистка важна
                max_temp_files=1500,
                gc_frequency=100,
            ),
            version="2.1.0-bulk",
            created_at="",
            updated_at="",
        )

    @staticmethod
    def get_available_profiles() -> Dict[str, str]:
        """
        Возвращает словарь доступных профилей с их описаниями.

        Returns:
            Dict[str, str]: Словарь {название: описание}
        """
        return {
            "fast": "Быстрое скачивание - максимальная скорость, минимальная валидация",
            "seo": "SEO-оптимизация - строгая валидация, уникализация для веб-сайтов",
            "safe": "Безопасная обработка - максимальная безопасность и подтверждения",
            "bulk": "Массовая обработка - оптимизация для больших объемов данных",
        }

    @staticmethod
    def create_profile(profile_name: str) -> AppConfig:
        """
        Создает конфигурацию для указанного профиля.

        Args:
            profile_name: Название профиля

        Returns:
            AppConfig: Конфигурация профиля

        Raises:
            ValueError: Если профиль не найден
        """
        creators = {
            "fast": ConfigProfiles.create_fast_download_profile,
            "seo": ConfigProfiles.create_seo_optimization_profile,
            "safe": ConfigProfiles.create_safe_processing_profile,
            "bulk": ConfigProfiles.create_bulk_processing_profile,
        }

        if profile_name not in creators:
            available = ", ".join(creators.keys())
            raise ValueError(f"Неизвестный профиль '{profile_name}'. Доступны: {available}")

        return creators[profile_name]()

    @staticmethod
    def save_profile_as_config(
        profile_name: str, output_path: Path, format_type: str = "yaml"
    ) -> bool:
        """
        Сохраняет профиль как файл конфигурации.

        Args:
            profile_name: Название профиля
            output_path: Путь для сохранения
            format_type: Формат файла ('yaml' или 'json')

        Returns:
            bool: True если успешно сохранен
        """
        try:
            config = ConfigProfiles.create_profile(profile_name)

            # Импортируем ConfigManager для сохранения
            from utils.config_manager import ConfigManager

            config_manager = ConfigManager()
            config_manager.config = config

            success = config_manager.save_config(output_path, format_type)
            if success:
                logger.info(f"Профиль '{profile_name}' сохранен как {output_path}")
            return success

        except Exception as e:
            logger.error(f"Ошибка при сохранении профиля '{profile_name}': {e}")
            return False

    @staticmethod
    def list_profiles() -> None:
        """Выводит список доступных профилей с описаниями."""
        profiles = ConfigProfiles.get_available_profiles()

        print("\n📋 ДОСТУПНЫЕ ПРОФИЛИ КОНФИГУРАЦИИ:")
        print("=" * 60)

        for name, description in profiles.items():
            print(f"🔹 {name:12} - {description}")

        print("\n💡 Использование:")
        print("   python main.py --profile <название>")
        print("   Или создайте файл конфигурации: --save-profile <название>")
        print()
