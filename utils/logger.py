"""
Настройка логирования для async image downloader.
"""
import logging
import sys
from utils.config import BASE_DIR


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Настраивает и возвращает логгер с выводом в консоль и файл.
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Избегаем дублирования обработчиков
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для файла
    file_handler = logging.FileHandler(BASE_DIR / 'app.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Создаем основной логгер для приложения
logger = setup_logger('async_image_downloader')