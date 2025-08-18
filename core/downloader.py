"""
Модуль для асинхронного скачивания изображений.
"""
import asyncio
import platform
import random
import re
from pathlib import Path
from typing import List

import aiofiles
import aiofiles.os
import aiohttp

from utils.config import (
    BROWSER_DEFAULT_DELAY,
    DOWNLOAD_TIMEOUT,
    FAST_DEFAULT_DELAY,
    FAST_HEADERS,
    FAST_SEMAPHORE_LIMIT,
    IMAGE_DIR,
    USER_AGENTS,
)
from utils.logger import logger
from core.image_utils import process_and_save_image_sync
from core.browser_downloader import download_images_browser

# Семафор для ограничения одновременных соединений в быстром режиме
fast_semaphore = asyncio.Semaphore(FAST_SEMAPHORE_LIMIT)


async def create_dir(dir_name: Path) -> None:
    """Создает директорию если она не существует."""
    await aiofiles.os.makedirs(dir_name, exist_ok=True)


async def download_file_fast(
    session: aiohttp.ClientSession,
    url: str,
    target_dir: Path,
    file_index: int,
    delay: float = FAST_DEFAULT_DELAY,
) -> None:
    """
    Быстрое скачивание файла для обычных сайтов.

    Args:
        session: HTTP сессия
        url: URL для скачивания
        target_dir: Директория для сохранения
        file_index: Индекс файла для именования
        delay: Задержка между запросами в секундах
    """
    async with fast_semaphore:
        # Базовое имя файла
        base_filename = f"{file_index}"
        new_filename = f"{base_filename}.jpeg"
        full_path = target_dir / new_filename

        # Проверка на существование файла и изменение имени при необходимости
        counter = 1
        while await aiofiles.os.path.exists(full_path):
            new_filename = f"{base_filename}.{counter}.jpeg"
            full_path = target_dir / new_filename
            counter += 1

        # Простая задержка
        if delay > 0:
            await asyncio.sleep(delay + random.uniform(0, 0.1))

        # Простые заголовки
        headers = FAST_HEADERS.copy()
        headers['User-Agent'] = random.choice(USER_AGENTS)

        try:
            # Простой запрос
            timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            async with session.get(
                url, headers=headers, allow_redirects=True, timeout=timeout
            ) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status} для {url}")
                    return

                # Проверяем Content-Type
                content_type = response.headers.get(
                    'content-type', ''
                ).lower()
                if not content_type.startswith('image/'):
                    logger.warning(f"URL {url} не содержит изображение")
                    return

                # Читаем и сохраняем
                image_data = await response.read()
                if len(image_data) < 100:
                    logger.warning(f"Слишком маленький файл для {url}")
                    return

                # Обрабатываем и сохраняем изображение
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    process_and_save_image_sync,
                    image_data,
                    full_path,
                    content_type,
                )

                logger.info(f"Сохранено: {full_path} ({len(image_data)} байт)")

        except Exception as e:
            logger.error(f"Ошибка при скачивании {url}: {e}")


async def download_images_for_folder(
    folder_name: str,
    urls: List[str],
    start_index: int = 1000,
    delay: float = FAST_DEFAULT_DELAY,
    browser_mode: bool = False,
) -> None:
    """
    Скачивает изображения по списку URL в указанную папку.

    Args:
        folder_name: Имя папки для сохранения
        urls: Список URL для скачивания
        start_index: Начальный индекс для именования файлов
        delay: Задержка между запросами в секундах
        browser_mode: Использовать браузерный режим (медленнее, но надежнее)
    """
    folder_path = IMAGE_DIR / folder_name
    await create_dir(folder_path)

    if browser_mode:
        try:
            # Используем браузерный режим
            await download_images_browser(
                urls, folder_path, start_index, delay or BROWSER_DEFAULT_DELAY
            )
        except Exception as e:
            logger.error(f"Ошибка браузерного режима: {e}")
            logger.info("Переключаемся на быстрый режим...")
            browser_mode = False

    if not browser_mode:
        # Используем быстрый режим
        logger.info(f"Быстрый режим: скачивание {len(urls)} изображений")

        tasks = []
        # На Mac отключаем проверку SSL для совместимости
        if platform.system() == 'Darwin':  # macOS
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                for i, url in enumerate(urls):
                    tasks.append(
                        asyncio.create_task(
                            download_file_fast(
                                session,
                                url,
                                folder_path,
                                start_index + i,
                                delay,
                            )
                        )
                    )
                await asyncio.gather(*tasks)
        else:
            async with aiohttp.ClientSession() as session:
                for i, url in enumerate(urls):
                    tasks.append(
                        asyncio.create_task(
                            download_file_fast(
                                session,
                                url,
                                folder_path,
                                start_index + i,
                                delay,
                            )
                        )
                    )
                await asyncio.gather(*tasks)


async def download_images_from_file(
    file_path: Path,
    start_index: int = 1000,
    delay: float = FAST_DEFAULT_DELAY,
    browser_mode: bool = False,
) -> None:
    """
    Скачивает изображения из файла, содержащего URL и имена папок.

    Формат файла:
    - Строки с именами папок (могут содержать пробелы)
    - Строки с URL (начинающиеся с http:// или https://)

    Args:
        file_path: Путь к файлу с URL
        start_index: Начальный индекс для именования файлов
        delay: Задержка между запросами в секундах
        browser_mode: Использовать браузерный режим (медленнее, но надежнее)
    """
    await create_dir(IMAGE_DIR)

    try:
        current_folder = None
        current_urls = []

        # Открываем файл с указанием кодировки UTF-8
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            lines = content.splitlines()

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Проверяем, является ли строка именем папки или URL
                if line.startswith(("http://", "https://")):
                    # Это URL, добавляем к текущей папке
                    if current_folder:
                        current_urls.append(line)
                else:
                    # Это новое имя папки
                    # Если у нас уже есть папка с URL, сначала обрабатываем их
                    if current_folder and current_urls:
                        logger.info(
                            f"Обработка папки '{current_folder}' "
                            f"с {len(current_urls)} URL"
                        )
                        await download_images_for_folder(
                            current_folder,
                            current_urls,
                            start_index,
                            delay,
                            browser_mode,
                        )
                        logger.info(
                            f"Скачано {len(current_urls)} изображений "
                            f"в папку '{current_folder}'"
                        )
                        # Очищаем список URL для новой папки
                        current_urls = []

                    # Начинаем новую папку
                    parts = re.split(r'[\s,;]+', line)
                    # Если имя папки содержит пробелы, берем первые два слова
                    if (
                        len(parts) > 1
                        and not parts[1].startswith(("http://", "https://"))
                    ):
                        current_folder = f"{parts[0]} {parts[1]}"
                        # Пропускаем первые два слова (имя папки)
                        parts = parts[2:]
                    else:
                        current_folder = parts[0]
                        # Пропускаем первое слово (имя папки)
                        parts = parts[1:]

                    logger.info(f"Новая папка: '{current_folder}'")

                    # Добавляем URL из текущей строки
                    current_urls = [
                        url.strip()
                        for url in parts
                        if url.strip() and url.startswith(("http://", "https://"))
                    ]

            # Обрабатываем последнюю папку, если она есть
            if current_folder and current_urls:
                logger.info(
                    f"Обработка последней папки '{current_folder}' "
                    f"с {len(current_urls)} URL"
                )
                await download_images_for_folder(
                    current_folder, current_urls, start_index, delay, browser_mode
                )
                logger.info(
                    f"Скачано {len(current_urls)} изображений "
                    f"в папку '{current_folder}'"
                )

    except FileNotFoundError:
        logger.error(f"Ошибка: Файл '{file_path}' не найден.")
        return
    except Exception as e:
        logger.error(f"Ошибка при чтении файла '{file_path}': {e}")
        return
