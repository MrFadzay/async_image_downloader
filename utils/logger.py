"""
Настройка логирования для async image downloader.
"""

import logging
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """
    Определяет базовую директорию приложения.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


BASE_DIR = get_base_dir()


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Настраивает и возвращает логгер с выводом в консоль и файл.

    Конфигурирует логгер с двумя обработчиками: один для вывода в консоль,
    второй для записи в файл app.log. Предотвращает дублирование обработчиков.

    Args:
        name: Имя логгера (по умолчанию имя модуля)

    Returns:
        logging.Logger: Настроенный логгер с уровнем INFO
    """
    logger = logging.getLogger(name)

    # Избегаем дублирования обработчиков
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Формат сообщений
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Обработчик для файла с UTF-8 кодировкой
    file_handler = logging.FileHandler(BASE_DIR / "app.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Создаем основной логгер для приложения
logger = setup_logger("async_image_downloader")
