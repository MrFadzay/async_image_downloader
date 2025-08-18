"""
Конфигурация и константы для async image downloader.
"""
import sys
from pathlib import Path


def get_base_dir():
    """
    Получает базовую директорию.
    Для обычного скрипта - это папка со скриптом.
    Для упакованного в .exe приложения - это папка с .exe файлом.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Мы запущены из .exe, созданного PyInstaller
        return Path(sys.executable).parent
    else:
        # Мы запущены как обычный .py скрипт
        return Path(__file__).parent.parent


# Базовые директории
BASE_DIR = get_base_dir()
IMAGE_DIR = BASE_DIR / 'images'

# Настройки для скачивания
DOWNLOAD_TIMEOUT = 30

# Настройки скачивания (curl_cffi)
FAST_SEMAPHORE_LIMIT = 10
FAST_DEFAULT_DELAY = 0.1

# Настройки для уникализации
BRIGHTNESS_FACTOR_RANGE = (-0.02, 0.02)
CONTRAST_FACTOR_RANGE = (-0.03, 0.03)
MAX_UNIQUIFY_ATTEMPTS = 10

# Примечание: curl_cffi автоматически управляет заголовками при использовании impersonate

# Поддерживаемые расширения изображений
SUPPORTED_IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'
]

# Настройки для определения дубликатов
# Если 2 из 3 хешей совпадают, считаем изображения дубликатами
SIMILARITY_THRESHOLD = 2
