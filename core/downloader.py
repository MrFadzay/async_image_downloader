"""
Модуль для асинхронного скачивания изображений.
"""
import asyncio
import random
from pathlib import Path
from typing import List
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
    if 'text/html' in content_type or 'application/json' in content_type:
        logger.warning(
            "Получен HTML/JSON вместо изображения для %s. "
            "Content-Type: %s",
            url,
            content_type,
        )
        return False
    if len(image_data) < min_size:
        logger.warning(
            "Слишком маленький файл для %s. Размер: %d байт.",
            url,
            len(image_data),
        )
        return False
    loop = asyncio.get_running_loop()
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

# Скачивает одно изображение


async def download_file(
    session: AsyncSession,
    semaphore: asyncio.Semaphore,
    url: str,
    target_dir: Path,
    file_index: int,
    retries: int = 3,
) -> bool:
    async with semaphore:
        if not url:
            logger.error("Получен пустой URL для скачивания.")
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
                response = await session.get(
                    url,
                    headers=headers,
                    timeout=DOWNLOAD_TIMEOUT,
                )
                response.raise_for_status()
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
                        await asyncio.sleep(wait_time)
                        continue
                logger.error("Ошибка при скачивании %s: %s", url, e)
            except Exception as e:
                logger.error("Неизвестная ошибка для %s: %s", url, e)
            attempt += 1
            if attempt < retries:
                await asyncio.sleep(1)
        return False


async def download_images(
    session: AsyncSession,
    urls: List[str],
    target_dir: Path,
    start_index: int = 1000,
    retries: int = 3,
) -> int:
    """
    Асинхронно скачивает список URL в указанную директорию.

    Возвращает количество успешно скачанных изображений.
    """
    await create_dir(target_dir)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    logger.info(
        "Начинаем скачивание %d изображений в '%s'...",
        len(urls),
        target_dir,
    )

    tasks = [
        asyncio.create_task(
            download_file(
                session,
                semaphore,
                url,
                target_dir,
                start_index + i,
                retries,
            )
        )
        for i, url in enumerate(urls)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_downloads = sum(
        1 for res in results if isinstance(res, bool) and res)

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
    """Запускает сессию скачивания изображений."""
    if not urls:
        logger.warning("Не передано ни одного URL для скачивания.")
        return

    target_dir = IMAGE_DIR / DEFAULT_DOWNLOAD_DIR_NAME
    await create_dir(target_dir)

    logger.info(
        "%d URL для обработки. Изображения будут сохранены в '%s'",
        len(urls),
        target_dir,
    )

    async with AsyncSession() as session:
        successful_count = await download_images(
            session=session,
            urls=urls,
            target_dir=target_dir,
            start_index=start_index,
            retries=retries,
        )

    if successful_count == len(urls):
        logger.info("Все запрошенные изображения успешно скачаны!")
    else:
        logger.warning(
            "Скачивание завершено. Успешно скачано %d из %d изображений",
            successful_count,
            len(urls),
        )
