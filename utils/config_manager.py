"""
Система управления конфигурацией с поддержкой JSON и YAML.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from utils.logger import logger
import sys


def get_base_dir() -> Path:
    """
    Определяет базовую директорию приложения.

    Returns:
        Path: Абсолютный путь к корневой папке приложения
        (папка скрипта или .exe файла).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


# Базовые директории
BASE_DIR = get_base_dir()
IMAGE_DIR = BASE_DIR / "images"
DEFAULT_DOWNLOAD_DIR_NAME = "downloaded_images"

# Настройки HTTP и загрузки
DOWNLOAD_TIMEOUT = 30  # seconds
MAX_CONCURRENT_DOWNLOADS = 50

# HTTP заголовки и User-Agent для запросов
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) " "Gecko/20100101 Firefox/115.0",
]

# Настройки обработки изображений
BRIGHTNESS_FACTOR_RANGE = (-0.15, 0.15)
CONTRAST_FACTOR_RANGE = (-0.15, 0.15)
MAX_UNIQUIFY_ATTEMPTS = 10
SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]

# Настройки определения дубликатов
SIMILARITY_THRESHOLD = 2

# Настройки безопасности и ограничений
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_FILE_SIZE = 100  # 100 bytes

# Разрешенные схемы URL для скачивания
ALLOWED_URL_SCHEMES = ["http", "https"]
# Запрещенные домены и адреса
FORBIDDEN_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0"]
FORBIDDEN_IP_RANGES = [
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
]

# Допустимые MIME типы для изображений
ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
]


@dataclass
class DownloadConfig:
    """Конфигурация параметров скачивания."""

    max_concurrent_downloads: int = 50
    download_timeout: int = 30
    default_retries: int = 3
    default_start_index: int = 1000
    enable_pause_resume: bool = True
    user_agent_rotation: bool = True
    user_agents: list = None

    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = USER_AGENTS.copy()


@dataclass
class PathConfig:
    """Конфигурация путей."""

    image_dir: str = "./images"
    download_dir_name: str = "downloaded_images"
    temp_dir: str = "./temp"
    log_file: str = "app.log"
    session_file: str = "download_session.json"


@dataclass
class ValidationConfig:
    """Конфигурация валидации."""

    max_download_size_mb: int = 100
    max_image_size_mb: int = 50
    min_file_size: int = 100
    allowed_schemes: list = None
    forbidden_domains: list = None

    def __post_init__(self):
        if self.allowed_schemes is None:
            self.allowed_schemes = ["http", "https"]
        if self.forbidden_domains is None:
            self.forbidden_domains = ["localhost", "127.0.0.1", "0.0.0.0"]


@dataclass
class DuplicateConfig:
    """Конфигурация обработки дубликатов."""

    similarity_threshold: int = 2
    max_uniquify_attempts: int = 10
    auto_confirm_operations: bool = False
    create_backups: bool = True
    backup_suffix: str = ".backup"


@dataclass
class UIConfig:
    """Конфигурация пользовательского интерфейса."""

    show_welcome_message: bool = True
    show_operation_tips: bool = True
    show_safety_warnings: bool = True
    progress_bar_style: str = "default"
    error_details_level: str = "medium"  # low, medium, high


@dataclass
class ResourceConfig:
    """Конфигурация управления ресурсами."""

    memory_threshold_mb: int = 1000
    auto_cleanup_temp_files: bool = True
    max_temp_files: int = 1000
    gc_frequency: int = 100  # операций между принудительными GC


@dataclass
class AppConfig:
    """Основной класс конфигурации приложения."""

    download: DownloadConfig
    paths: PathConfig
    validation: ValidationConfig
    duplicates: DuplicateConfig
    ui: UIConfig
    resources: ResourceConfig
    version: str = "2.1.0"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует конфигурацию в словарь."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Создает конфигурацию из словаря."""
        # Создаем экземпляры подконфигураций
        config_data = data.copy()

        # Обрабатываем каждую секцию
        sections = {
            "download": DownloadConfig,
            "paths": PathConfig,
            "validation": ValidationConfig,
            "duplicates": DuplicateConfig,
            "ui": UIConfig,
            "resources": ResourceConfig,
        }

        for section_name, section_class in sections.items():
            if section_name in config_data and isinstance(config_data[section_name], dict):
                config_data[section_name] = section_class(
                    **config_data[section_name])

        return cls(**config_data)


class ConfigManager:
    """Менеджер конфигурации приложения."""

    CONFIG_FILENAMES = [
        "config.yaml",
        "config.yml",
        "config.json",
        "settings.yaml",
        "settings.yml",
        "settings.json",
    ]

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd()
        self.config_file: Optional[Path] = None
        self.config: AppConfig = self._create_default_config()

    def _create_default_config(self) -> AppConfig:
        """Создает конфигурацию по умолчанию."""
        return AppConfig(
            download=DownloadConfig(),
            paths=PathConfig(),
            validation=ValidationConfig(),
            duplicates=DuplicateConfig(),
            ui=UIConfig(),
            resources=ResourceConfig(),
        )

    def find_config_file(self) -> Optional[Path]:
        """
        Ищет файл конфигурации в директории.

        Returns:
            Optional[Path]: Путь к найденному файлу конфигурации
        """
        for filename in self.CONFIG_FILENAMES:
            config_path = self.config_dir / filename
            if config_path.exists():
                logger.info(f"Найден файл конфигурации: {config_path}")
                return config_path

        return None

    def load_config(self, config_file: Optional[Path] = None) -> AppConfig:
        """
        Загружает конфигурацию из файла.

        Args:
            config_file: Путь к файлу конфигурации (опционально)

        Returns:
            AppConfig: Загруженная конфигурация или конфигурация по умолчанию
        """
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = self.find_config_file()

        if not self.config_file or not self.config_file.exists():
            logger.info(
                "Файл конфигурации не найден, используется конфигурация по умолчанию")
            return self.config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                if self.config_file.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            self.config = self._merge_config(data)
            logger.info(f"Конфигурация загружена из {self.config_file}")
            return self.config

        except Exception as e:
            logger.error(
                f"Ошибка при загрузке конфигурации из {self.config_file}: {e}")
            logger.info("Используется конфигурация по умолчанию")
            return self.config

    def _merge_config(self, data: Dict[str, Any]) -> AppConfig:
        """
        Объединяет загруженные данные с конфигурацией по умолчанию.

        Args:
            data: Загруженные данные конфигурации

        Returns:
            AppConfig: Объединенная конфигурация
        """
        try:
            # Создаем конфигурацию по умолчанию
            config = self._create_default_config()

            # Обновляем разделы конфигурации
            sections = {
                "download": DownloadConfig,
                "paths": PathConfig,
                "validation": ValidationConfig,
                "duplicates": DuplicateConfig,
                "ui": UIConfig,
                "resources": ResourceConfig,
            }

            for section_name, section_class in sections.items():
                if section_name in data:
                    section_data = data[section_name]
                    # Получаем текущую секцию
                    current_section = getattr(config, section_name)
                    current_dict = asdict(current_section)

                    # Обновляем только существующие ключи
                    for key, value in section_data.items():
                        if key in current_dict:
                            current_dict[key] = value
                        else:
                            logger.warning(
                                f"Неизвестный параметр конфигурации: {section_name}.{key}"
                            )

                    # Создаем новый объект секции
                    setattr(config, section_name,
                            section_class(**current_dict))

            # Обновляем метаданные
            if "version" in data:
                config.version = data["version"]
            if "created_at" in data:
                config.created_at = data["created_at"]

            config.updated_at = datetime.now().isoformat()

            return config

        except Exception as e:
            logger.error(f"Ошибка при объединении конфигурации: {e}")
            return self._create_default_config()

    def save_config(
        self,
        config: Optional[AppConfig] = None,
        config_file: Optional[Path] = None,
        format_type: str = "yaml",
    ) -> bool:
        """
        Сохраняет конфигурацию в файл.

        Args:
            config: Конфигурация для сохранения (опционально, по умолчанию текущая)
            config_file: Путь к файлу (опционально)
            format_type: Формат файла ('yaml' или 'json')

        Returns:
            bool: True если конфигурация успешно сохранена
        """
        # Используем переданную конфигурацию или текущую
        config_to_save = config or self.config

        if config_file:
            self.config_file = config_file
        elif not self.config_file:
            filename = f"config.{format_type}"
            self.config_file = self.config_dir / filename

        try:
            # Обновляем время изменения
            config_to_save.updated_at = datetime.now().isoformat()

            # Конвертируем в словарь
            config_dict = config_to_save.to_dict()

            # Сохраняем в файл
            with open(self.config_file, "w", encoding="utf-8") as f:
                if format_type == "yaml" or self.config_file.suffix in [".yaml", ".yml"]:
                    yaml.dump(
                        config_dict, f, default_flow_style=False, allow_unicode=True, indent=2
                    )
                else:
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"Конфигурация сохранена в {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")
            return False

    def get_config(self) -> AppConfig:
        """Возвращает текущую конфигурацию."""
        return self.config

    def update_config(self, section: str, **kwargs) -> None:
        """
        Обновляет параметры конфигурации.

        Args:
            section: Название секции конфигурации
            **kwargs: Параметры для обновления
        """
        if not hasattr(self.config, section):
            logger.error(f"Неизвестная секция конфигурации: {section}")
            return

        section_obj = getattr(self.config, section)
        section_dict = asdict(section_obj)

        for key, value in kwargs.items():
            if key in section_dict:
                section_dict[key] = value
                logger.info(f"Обновлен параметр {section}.{key} = {value}")
            else:
                logger.warning(f"Неизвестный параметр: {section}.{key}")

        # Пересоздаем объект секции
        section_class = type(section_obj)
        setattr(self.config, section, section_class(**section_dict))

        self.config.updated_at = datetime.now().isoformat()

    def create_sample_config(self, format_type: str = "yaml") -> Path:
        """
        Создает файл конфигурации-образец.

        Args:
            format_type: Формат файла ('yaml' или 'json')

        Returns:
            Path: Путь к созданному файлу
        """
        sample_file = self.config_dir / f"config-sample.{format_type}"

        # Создаем конфигурацию с комментариями
        config_dict = asdict(self._create_default_config())

        # Добавляем описания
        config_dict["_description"] = "Файл конфигурации Async Image Downloader"
        config_dict["_version"] = self.config.version
        config_dict["_sections"] = {
            "download": "Параметры скачивания изображений",
            "paths": "Пути к файлам и директориям",
            "validation": "Настройки валидации файлов и URL",
            "duplicates": "Параметры обработки дубликатов",
            "ui": "Настройки пользовательского интерфейса",
            "resources": "Управление ресурсами системы",
        }

        try:
            with open(sample_file, "w", encoding="utf-8") as f:
                if format_type == "yaml":
                    yaml.dump(
                        config_dict, f, default_flow_style=False, allow_unicode=True, indent=2
                    )
                else:
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"Создан образец конфигурации: {sample_file}")
            return sample_file

        except Exception as e:
            logger.error(f"Ошибка при создании образца конфигурации: {e}")
            raise

    def validate_config(self) -> bool:
        """
        Валидирует текущую конфигурацию.

        Returns:
            bool: True если конфигурация валидна
        """
        errors = []

        # Проверяем download секцию
        if self.config.download.max_concurrent_downloads <= 0:
            errors.append(
                "download.max_concurrent_downloads должно быть больше 0")
        if self.config.download.download_timeout <= 0:
            errors.append("download.download_timeout должно быть больше 0")

        # Проверяем validation секцию
        if self.config.validation.max_download_size_mb <= 0:
            errors.append(
                "validation.max_download_size_mb должно быть больше 0")
        if self.config.validation.min_file_size < 0:
            errors.append(
                "validation.min_file_size не может быть отрицательным")

        # Проверяем paths секцию
        try:
            Path(self.config.paths.image_dir)
        except Exception:
            errors.append("paths.image_dir содержит недопустимый путь")

        if errors:
            logger.error("Ошибки в конфигурации:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Конфигурация валидна")
        return True

    def reset_to_defaults(self) -> None:
        """Сбрасывает конфигурацию к значениям по умолчанию."""
        logger.info("Сброс конфигурации к значениям по умолчанию")
        self.config = self._create_default_config()


# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Возвращает глобальный экземпляр менеджера конфигурации."""
    return config_manager


def get_config() -> AppConfig:
    """Возвращает текущую конфигурацию приложения."""
    return config_manager.get_config()


def load_or_create_config(config_dir: Optional[Path] = None) -> AppConfig:
    """
    Загружает конфигурацию или создает новую если файл не найден.

    Args:
        config_dir: Директория с конфигурацией

    Returns:
        AppConfig: Загруженная или созданная конфигурация
    """
    global config_manager

    if config_dir:
        config_manager = ConfigManager(config_dir)

    # Пытаемся загрузить существующую конфигурацию
    loaded = config_manager.load_config()

    if not loaded:
        # Создаем образец конфигурации для пользователя
        try:
            sample_file = config_manager.create_sample_config("yaml")
            logger.info(f"Создан образец конфигурации: {sample_file}")
            logger.info(
                "Отредактируйте файл и переименуйте в 'config.yaml' для использования")
        except Exception as e:
            logger.error(f"Не удалось создать образец конфигурации: {e}")

    # Валидируем конфигурацию
    config_manager.validate_config()

    return config_manager.get_config()
