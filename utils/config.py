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

# Быстрый режим (aiohttp)
FAST_SEMAPHORE_LIMIT = 10
FAST_DEFAULT_DELAY = 0.1

# Браузерный режим (Playwright) 
BROWSER_SEMAPHORE_LIMIT = 2
BROWSER_DEFAULT_DELAY = 1.0

# Настройки для уникализации
BRIGHTNESS_FACTOR_RANGE = (-0.02, 0.02)
CONTRAST_FACTOR_RANGE = (-0.03, 0.03)
MAX_UNIQUIFY_ATTEMPTS = 10

# Простые заголовки для быстрого режима
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Базовые заголовки для быстрого режима
FAST_HEADERS = {
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
}

# Поддерживаемые расширения изображений
SUPPORTED_IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'
]

# Настройки для определения дубликатов
# Если 2 из 3 хешей совпадают, считаем изображения дубликатами
SIMILARITY_THRESHOLD = 2
