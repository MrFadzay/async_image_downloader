"""
Конфигурация для асинхронного скачивания изображений.

Основные разделы:
- Пути и директории
- Параметры скачивания и HTTP
- Настройки обработки изображений
- Определение дубликатов
"""
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """
    Определяет базовую директорию приложения.

    Returns:
        Path: Абсолютный путь к корневой папке приложения
        (папка скрипта или .exe файла).
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


# Базовые директории
BASE_DIR = get_base_dir()
IMAGE_DIR = BASE_DIR / 'images'
DEFAULT_DOWNLOAD_DIR_NAME = "downloaded_images"

# Настройки HTTP и загрузки
DOWNLOAD_TIMEOUT = 30  # seconds

# Максимальное количество параллельных загрузок
MAX_CONCURRENT_DOWNLOADS = 50

# HTTP заголовки и User-Agent для запросов
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
    "Gecko/20100101 Firefox/115.0",
]

# Настройки обработки изображений
# Диапазоны для рандомизации при уникализации
BRIGHTNESS_FACTOR_RANGE = (-0.02, 0.02)
CONTRAST_FACTOR_RANGE = (-0.03, 0.03)
# сколько попыток предпринять для уникализации изображения
MAX_UNIQUIFY_ATTEMPTS = 10
# Поддерживаемые форматы файлов
SUPPORTED_IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'
]

# Настройки определения дубликатов
# Порог схожести: если 2 из 3 хешей совпадают
SIMILARITY_THRESHOLD = 2

# Настройки безопасности и ограничений
# Максимальный размер файла для скачивания (в байтах) - 100MB
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024
# Максимальный размер изображения для обработки (в байтах) - 50MB
MAX_IMAGE_SIZE = 50 * 1024 * 1024
# Минимальный размер файла (в байтах) - 100 bytes
MIN_FILE_SIZE = 100

# Разрешенные схемы URL для скачивания
ALLOWED_URL_SCHEMES = ['http', 'https']
# Запрещенные домены и адреса
FORBIDDEN_DOMAINS = ['localhost', '127.0.0.1', '0.0.0.0']
FORBIDDEN_IP_RANGES = ['192.168.', '10.', '172.16.', '172.17.', '172.18.',
                      '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                      '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                      '172.29.', '172.30.', '172.31.']

# Допустимые MIME типы для изображений
ALLOWED_MIME_TYPES = [
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
    'image/bmp', 'image/tiff', 'image/webp'
]
