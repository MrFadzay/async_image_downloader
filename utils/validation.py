"""
Модуль валидации для обеспечения безопасности и ограничения ресурсов.
"""
import ipaddress
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse

from utils.config import (
    MAX_DOWNLOAD_SIZE,
    MAX_IMAGE_SIZE,
    MIN_FILE_SIZE,
    ALLOWED_URL_SCHEMES,
    FORBIDDEN_DOMAINS,
    FORBIDDEN_IP_RANGES,
    ALLOWED_MIME_TYPES,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from utils.logger import logger


def validate_file_size(file_size: int, max_size: int = MAX_DOWNLOAD_SIZE) -> bool:
    """
    Проверяет размер файла на соответствие ограничениям.
    
    Args:
        file_size: Размер файла в байтах
        max_size: Максимально допустимый размер (по умолчанию MAX_DOWNLOAD_SIZE)
        
    Returns:
        bool: True если размер допустим, False иначе
    """
    if file_size < MIN_FILE_SIZE:
        logger.warning(f"Файл слишком маленький: {file_size} байт (минимум {MIN_FILE_SIZE})")
        return False
    
    if file_size > max_size:
        logger.warning(
            f"Файл слишком большой: {file_size} байт "
            f"(максимум {max_size / (1024*1024):.1f} MB)"
        )
        return False
    
    return True


def validate_image_size(file_size: int) -> bool:
    """
    Проверяет размер изображения для обработки.
    
    Args:
        file_size: Размер файла в байтах
        
    Returns:
        bool: True если размер допустим для обработки, False иначе
    """
    return validate_file_size(file_size, MAX_IMAGE_SIZE)


def validate_url_security(url: str) -> bool:
    """
    Проверяет URL на безопасность для предотвращения SSRF атак.
    
    Блокирует доступ к локальным IP-адресам, приватным сетям, опасным схемам
    и запрещенным доменам. Обеспечивает защиту от атак через подделку запросов.
    
    Args:
        url: URL для проверки безопасности
        
    Returns:
        bool: True если URL безопасен для использования, False иначе
    """
    try:
        parsed = urlparse(url)
        
        # Проверяем схему URL
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            logger.warning(f"Запрещенная схема URL: {parsed.scheme}")
            return False
        
        # Проверяем наличие хоста
        if not parsed.netloc:
            logger.warning("URL не содержит доменного имени")
            return False
        
        # Извлекаем хост (без порта)
        host = parsed.hostname or parsed.netloc.split(':')[0]
        
        # Проверяем запрещенные домены
        if host.lower() in FORBIDDEN_DOMAINS:
            logger.warning(f"Запрещенный домен: {host}")
            return False
        
        # Проверяем IP-адреса
        try:
            ip = ipaddress.ip_address(host)
            # Блокируем приватные и локальные IP
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                logger.warning(f"Запрещенный IP-адрес: {host}")
                return False
        except ValueError:
            # Не IP-адрес, это нормально
            pass
        
        # Проверяем запрещенные диапазоны IP
        for forbidden_range in FORBIDDEN_IP_RANGES:
            if host.startswith(forbidden_range):
                logger.warning(f"IP-адрес из запрещенного диапазона: {host}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при валидации URL {url}: {e}")
        return False


def validate_mime_type(content_type: str) -> bool:
    """
    Проверяет MIME-тип файла на соответствие поддерживаемым форматам изображений.
    
    Очищает content-type от дополнительных параметров и проверяет соответствие
    списку разрешенных типов изображений из конфигурации.
    
    Args:
        content_type: MIME-тип из HTTP заголовков (например, 'image/jpeg; charset=utf-8')
        
    Returns:
        bool: True если MIME-тип разрешен, False иначе
    """
    # Очищаем content-type от дополнительных параметров
    mime_type = content_type.split(';')[0].strip().lower()
    
    if mime_type in ALLOWED_MIME_TYPES:
        return True
    
    logger.warning(f"Неразрешенный MIME-тип: {mime_type}")
    return False


def validate_file_extension(filename: Union[str, Path]) -> bool:
    """
    Проверяет расширение файла на соответствие поддерживаемым форматам изображений.
    
    Извлекает расширение файла и сравнивает его со списком поддерживаемых
    форматов из конфигурации (jpg, png, gif, webp и др.).
    
    Args:
        filename: Имя файла или объект Path
        
    Returns:
        bool: True если расширение поддерживается, False иначе
    """
    if isinstance(filename, str):
        filename = Path(filename)
    
    extension = filename.suffix.lower()
    
    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return True
    
    logger.warning(f"Неподдерживаемое расширение файла: {extension}")
    return False


def validate_download_request(url: str, expected_size: Optional[int] = None) -> bool:
    """
    Комплексная валидация запроса на скачивание с проверкой безопасности и размеров.
    
    Выполняет полную проверку URL на безопасность и, при наличии информации,
    проверяет ожидаемый размер файла на соответствие ограничениям.
    
    Args:
        url: URL для скачивания
        expected_size: Ожидаемый размер файла в байтах (опционально)
        
    Returns:
        bool: True если запрос прошел все проверки, False иначе
    """
    # Проверяем безопасность URL
    if not validate_url_security(url):
        return False
    
    # Проверяем размер файла если известен
    if expected_size is not None:
        if not validate_file_size(expected_size):
            return False
    
    return True