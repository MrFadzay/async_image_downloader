"""
Модуль для асинхронного скачивания изображений.
"""
import asyncio
import random
from pathlib import Path
from typing import List, Tuple
import time
import aiofiles.os
from curl_cffi import AsyncSession
from curl_cffi.requests import errors

from core.image_utils import process_and_save_image_sync
from utils.config import (
    DEFAULT_DOWNLOAD_DIR_NAME,
    DOWNLOAD_TIMEOUT,
    USER_AGENTS,
    IMAGE_DIR,
    MAX_CONCURRENT_DOWNLOADS,
)
from utils.logger import logger
from utils.validation import (
    validate_download_request,
    validate_file_size,
    validate_mime_type,
)
from utils.resource_manager import get_resource_manager
from utils.progress import get_progress_tracker, show_download_stats


async def create_dir(dir_name: Path) -> None:
    """Создает директорию если она не существует."""
    await aiofiles.os.makedirs(dir_name, exist_ok=True)


# Генерирует уникальное имя файла в целевой директории
async def generate_unique_filename(
        target_dir: Path, base_filename: str) -> Path:
    new_filename = f"{base_filename}.jpeg"
    full_path = target_dir / new_filename
    counter = 1
    while await aiofiles.os.path.exists(full_path):
        new_filename = f"{base_filename}.{counter}.jpeg"
        full_path = target_dir / new_filename
        counter += 1
    return full_path

# Обработчик для проверки и сохранения данных изображения


async def handle_and_save_response(
    image_data: bytes,
    headers: dict,
    full_path: Path,
    url: str,
    min_size: int = 100,
) -> bool:
    content_type = headers.get('content-type', '').lower()
    
    # Проверяем MIME-тип
    if not validate_mime_type(content_type):
        return False
        
    # Проверяем на HTML/JSON ответы
    if 'text/html' in content_type or 'application/json' in content_type:
        logger.warning(
            "Получен HTML/JSON вместо изображения для %s. "
            "Content-Type: %s",
            url,
            content_type,
        )
        return False
        
    # Проверяем размер файла
    if not validate_file_size(len(image_data)):
        return False
        
    if len(image_data) < min_size:
        logger.warning(
            "Слишком маленький файл для %s. Размер: %d байт.",
            url,
            len(image_data),
        )
        return False
        
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            process_and_save_image_sync,
            image_data,
            full_path,
            content_type,
        )
        logger.info(
            "Сохранено: %s (%d байт)",
            full_path,
            len(image_data),
        )
        return True
    except Exception as e:
        logger.error(
            "Ошибка при обработке и сохранении изображения %s: %s",
            url,
            e,
        )
        return False

# Скачивает одно изображение


async def download_file(
    session: AsyncSession,
    semaphore: asyncio.Semaphore,
    url: str,
    target_dir: Path,
    file_index: int,
    retries: int = 3,
) -> bool:
    """
    Асинхронно скачивает одно изображение по URL и сохраняет его в указанную директорию.
    
    Функция обеспечивает безопасное скачивание с валидацией URL, автоматическими 
    повторными попытками при ошибках, и использованием семафора для ограничения 
    количества одновременных подключений.
    
    Args:
        session: Асинхронная HTTP-сессия для выполнения запросов
        semaphore: Семафор для ограничения количества одновременных загрузок
        url: URL изображения для скачивания
        target_dir: Директория для сохранения скачанного файла
        file_index: Индекс файла, используемый для генерации имени
        retries: Количество повторных попыток при ошибках (по умолчанию 3)
    
    Returns:
        bool: True при успешном скачивании, False при ошибке
    
    Raises:
        Функция не выбрасывает исключения, все ошибки логируются
    
    Examples:
        >>> import asyncio
        >>> from curl_cffi import AsyncSession
        >>> from pathlib import Path
        >>> 
        >>> async def download_example():
        ...     semaphore = asyncio.Semaphore(5)
        ...     target = Path("./downloads")
        ...     async with AsyncSession() as session:
        ...         success = await download_file(
        ...             session=session,
        ...             semaphore=semaphore,
        ...             url="https://example.com/image.jpg",
        ...             target_dir=target,
        ...             file_index=1001,
        ...             retries=3
        ...         )
        ...         print(f"Скачивание завершено: {success}")
        >>> 
        >>> # asyncio.run(download_example())
    
    Note:
        - Функция автоматически валидирует URL на безопасность
        - При получении 429 (Rate Limit) выполняется экспоненциальная задержка
        - Семафор используется только для сетевых операций, не блокируя повторы
        - Поддерживаются различные форматы изображений (JPEG, PNG, WebP, GIF)
    """
    if not url:
        logger.error("Получен пустой URL для скачивания.")
        return False
    
    # Проверяем безопасность URL
    if not validate_download_request(url):
        logger.error(f"Опасный или недопустимый URL: {url}")
        return False
    
    base_filename = f"{file_index}"
    full_path = await generate_unique_filename(target_dir, base_filename)
    attempt = 0
    
    while attempt < retries:
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            
            # Используем семафор только для сетевой операции
            async with semaphore:
                response = await session.get(
                    url,
                    headers=headers,
                    timeout=DOWNLOAD_TIMEOUT,
                )
                response.raise_for_status()
            
            # Обработка ответа вне семафора
            if await handle_and_save_response(
                response.content,
                response.headers,
                full_path,
                url,
            ):
                return True
                
        except errors.RequestsError as e:
            if e.response and e.response.status_code == 429:
                attempt += 1
                if attempt < retries:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Статус 429 для %s. "
                        "Попытка %d/%d через %.2f сек.",
                        url, attempt, retries, wait_time,
                    )
                    # Ожидание вне семафора
                    await asyncio.sleep(wait_time)
                    continue
            logger.error("Ошибка при скачивании %s: %s", url, e)
        except Exception as e:
            logger.error("Неизвестная ошибка для %s: %s", url, e)
        
        attempt += 1
        if attempt < retries:
            # Ожидание перед повтором вне семафора
            await asyncio.sleep(1)
    
    return False


async def download_file_with_progress(
    session: AsyncSession,
    semaphore: asyncio.Semaphore,
    url: str,
    target_dir: Path,
    file_index: int,
    retries: int,
    progress_bar
) -> Tuple[bool, float]:
    """
    Асинхронно скачивает одно изображение с обновлением прогресс-бара.
    
    Args:
        session: HTTP сессия
        semaphore: Семафор для ограничения подключений
        url: URL для скачивания
        target_dir: Директория для сохранения
        file_index: Индекс файла
        retries: Количество повторных попыток
        progress_bar: Объект прогресс-бара для обновления
        
    Returns:
        Tuple[bool, float]: (успех, размер_в_мб)
    """
    success = await download_file(
        session, semaphore, url, target_dir, file_index, retries
    )
    
    # Определяем размер файла для статистики
    size_mb = 0.0
    if success:
        try:
            base_filename = f"{file_index}"
            full_path = await generate_unique_filename(target_dir, base_filename)
            # Пытаемся найти реальный файл (может иметь суффикс .1, .2 и т.д.)
            for potential_path in target_dir.glob(f"{file_index}*.jpeg"):
                if await aiofiles.os.path.exists(potential_path):
                    stat_info = await aiofiles.os.stat(potential_path)
                    size_mb = stat_info.st_size / (1024 * 1024)
                    break
        except Exception as e:
            logger.debug(f"Не удалось получить размер файла для {url}: {e}")
    
    # Обновляем прогресс
    progress_bar.update(1)
    
    return success, size_mb


async def download_images(
    session: AsyncSession,
    urls: List[str],
    target_dir: Path,
    start_index: int = 1000,
    retries: int = 3,
) -> int:
    """
    Асинхронно скачивает список URL в указанную директорию с прогресс-баром.

    Возвращает количество успешно скачанных изображений.
    """
    await create_dir(target_dir)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    logger.info(
        "Начинаем скачивание %d изображений в '%s'...",
        len(urls),
        target_dir,
    )

    # Инициализируем прогресс-трекер
    progress_tracker = get_progress_tracker()
    successful_downloads = 0
    failed_downloads = 0
    total_size_mb = 0.0
    
    async with progress_tracker.track_download_progress(
        len(urls), "Скачивание изображений"
    ) as progress_bar:
        tasks = []
        for i, url in enumerate(urls):
            task = asyncio.create_task(
                download_file_with_progress(
                    session,
                    semaphore,
                    url,
                    target_dir,
                    start_index + i,
                    retries,
                    progress_bar
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Подсчитываем статистику
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                success, size_mb = result
                if success:
                    successful_downloads += 1
                    total_size_mb += size_mb
                else:
                    failed_downloads += 1
            elif isinstance(result, Exception):
                failed_downloads += 1
                logger.error(f"Исключение при скачивании: {result}")
            else:
                failed_downloads += 1

    logger.info(
        "Всего успешно скачано: %d из %d изображений.",
        successful_downloads,
        len(urls),
    )
    return successful_downloads


async def run_download_session(
    urls: List[str],
    start_index: int = 1000,
    retries: int = 3,
) -> None:
    """
    Запускает полную сессию скачивания изображений с мониторингом ресурсов.
    
    Основная функция для массового скачивания изображений. Автоматически 
    создаёт целевую директорию, мониторит использование памяти и 
    выполняет очистку ресурсов после завершения.
    
    Args:
        urls: Список URL-адресов изображений для скачивания
        start_index: Начальный индекс для нумерации файлов (по умолчанию 1000)
        retries: Количество повторных попыток при ошибках (по умолчанию 3)
    
    Returns:
        None: Функция ничего не возвращает, вся информация выводится через логи
    
    Examples:
        >>> import asyncio
        >>> 
        >>> urls = [
        ...     "https://example.com/image1.jpg",
        ...     "https://example.com/image2.png",
        ...     "https://example.com/image3.webp"
        ... ]
        >>> 
        >>> async def example_session():
        ...     await run_download_session(
        ...         urls=urls,
        ...         start_index=1000,
        ...         retries=3
        ...     )
        >>> 
        >>> # asyncio.run(example_session())
        
        Пример с командной строки:
        >>> # python main.py download --start-index 2000 --retries 5 \
        >>> #   "https://site1.com/pic.jpg" "https://site2.com/photo.png"
    
    Note:
        - Файлы сохраняются в {IMAGE_DIR}/{DEFAULT_DOWNLOAD_DIR_NAME}/
        - Имена файлов: start_index.jpeg, start_index+1.jpeg, и т.д.
        - Мониторинг памяти и автоматическая очистка ресурсов
        - Статистика успешно скачанных файлов выводится в логи
    """
    if not urls:
        logger.warning("Не передано ни одного URL для скачивания.")
        return

    # Инициализация менеджера ресурсов
    resource_manager = get_resource_manager()
    initial_memory = resource_manager.get_memory_usage()
    logger.info(
        f"Начальное использование памяти: {initial_memory.get('rss_mb', 0):.1f} MB"
    )

    target_dir = IMAGE_DIR / DEFAULT_DOWNLOAD_DIR_NAME
    await create_dir(target_dir)

    logger.info(
        "%d URL для обработки. Изображения будут сохранены в '%s'",
        len(urls),
        target_dir,
    )

    try:
        async with AsyncSession() as session:
            successful_count = await download_images(
                session=session,
                urls=urls,
                target_dir=target_dir,
                start_index=start_index,
                retries=retries,
            )
    finally:
        # Очистка ресурсов после завершения
        final_memory = resource_manager.get_memory_usage()
        memory_used = final_memory.get('rss_mb', 0) - initial_memory.get('rss_mb', 0)
        
        if memory_used > 50:  # Логируем только значительные изменения
            logger.info(f"Использовано памяти за сессию: {memory_used:.1f} MB")
            
        # Выполняем очистку временных файлов
        cleanup_stats = await resource_manager.cleanup_all()
        logger.debug(f"Статистика очистки: {cleanup_stats}")

    if successful_count == len(urls):
        logger.info("Все запрошенные изображения успешно скачаны!")
    else:
        logger.warning(
            "Скачивание завершено. Успешно скачано %d из %d изображений",
            successful_count,
            len(urls),
        )
