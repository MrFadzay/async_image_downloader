"""
Модуль для асинхронного скачивания изображений.
"""
import asyncio
import re
from pathlib import Path
from typing import List

import aiofiles
import aiofiles.os
import aiohttp

from utils.config import (
    SEMAPHORE_LIMIT,
    DOWNLOAD_TIMEOUT,
    DEFAULT_HEADERS,
    IMAGE_DIR
)
from utils.logger import logger
from core.image_utils import process_and_save_image_sync


# Семафор для ограничения количества одновременных загрузок
semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)


async def create_dir(dir_name: Path) -> None:
    """Создает директорию если она не существует."""
    await aiofiles.os.makedirs(dir_name, exist_ok=True)


async def download_file(session: aiohttp.ClientSession, url: str, target_dir: Path, file_index: int) -> None:
    """
    Скачивает один файл по URL и сохраняет в указанную директорию.
    
    Args:
        session: HTTP сессия
        url: URL для скачивания
        target_dir: Директория для сохранения
        file_index: Индекс файла для именования
    """
    async with semaphore:
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

        try:
            # Делаем запрос с заголовками и обработкой редиректов
            async with session.get(url, headers=DEFAULT_HEADERS, allow_redirects=True, timeout=DOWNLOAD_TIMEOUT) as response:
                # Проверяем статус ответа
                if response.status != 200:
                    logger.error(f"Ошибка HTTP {response.status} для {url}")
                    return

                # Проверяем Content-Type
                content_type = response.headers.get('content-type', '').lower()
                if not content_type.startswith('image/'):
                    logger.warning(f"URL {url} не содержит изображение. Content-Type: {content_type}")
                    return

                # Читаем содержимое
                image_data = await response.read()

                # Проверяем размер
                if len(image_data) < 100:
                    logger.warning(f"Слишком маленький файл ({len(image_data)} байт) для {url}")
                    return

                # Обрабатываем и сохраняем изображение
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, process_and_save_image_sync, image_data, full_path, content_type
                )
                logger.info(f"Изображение сохранено как JPEG: {full_path} ({len(image_data)} байт)")

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при скачивании {url}")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при скачивании {url}: {e}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при скачивании/сохранении {url}: {e}")


async def download_images_for_folder(folder_name: str, urls: List[str], start_index: int = 1000) -> None:
    """
    Скачивает изображения по списку URL в указанную папку.
    
    Args:
        folder_name: Имя папки для сохранения
        urls: Список URL для скачивания
        start_index: Начальный индекс для именования файлов
    """
    folder_path = IMAGE_DIR / folder_name
    await create_dir(folder_path)

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(urls):
            tasks.append(
                asyncio.create_task(
                    download_file(session, url, folder_path, start_index + i)
                )
            )
        await asyncio.gather(*tasks)


async def download_images_from_file(file_path: Path, start_index: int = 1000) -> None:
    """
    Скачивает изображения из файла, содержащего URL и имена папок.
    
    Формат файла:
    - Строки с именами папок (могут содержать пробелы)
    - Строки с URL (начинающиеся с http:// или https://)
    
    Args:
        file_path: Путь к файлу с URL
        start_index: Начальный индекс для именования файлов
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
                if line.startswith("http://") or line.startswith("https://"):
                    # Это URL, добавляем к текущей папке
                    if current_folder:
                        current_urls.append(line)
                else:
                    # Это новое имя папки
                    # Если у нас уже есть папка с URL, сначала обрабатываем их
                    if current_folder and current_urls:
                        logger.info(f"Обработка папки '{current_folder}' с {len(current_urls)} URL")
                        await download_images_for_folder(current_folder, current_urls, start_index)
                        logger.info(f"Скачано {len(current_urls)} изображений в папку '{current_folder}'")
                        # Очищаем список URL для новой папки
                        current_urls = []

                    # Начинаем новую папку
                    parts = re.split(r'[\s,;]+', line)
                    # Если имя папки содержит пробелы, берем первые два слова
                    if len(parts) > 1 and not (parts[1].startswith("http://") or parts[1].startswith("https://")):
                        current_folder = f"{parts[0]} {parts[1]}"
                        # Пропускаем первые два слова (имя папки)
                        parts = parts[2:]
                    else:
                        current_folder = parts[0]
                        # Пропускаем первое слово (имя папки)
                        parts = parts[1:]

                    logger.info(f"Новая папка: '{current_folder}'")

                    # Добавляем URL из текущей строки
                    current_urls = [url.strip() for url in parts if url.strip() and (
                        url.startswith("http://") or url.startswith("https://"))]

            # Обрабатываем последнюю папку, если она есть
            if current_folder and current_urls:
                logger.info(f"Обработка последней папки '{current_folder}' с {len(current_urls)} URL")
                await download_images_for_folder(current_folder, current_urls, start_index)
                logger.info(f"Скачано {len(current_urls)} изображений в папку '{current_folder}'")

    except FileNotFoundError:
        logger.error(f"Ошибка: Файл '{file_path}' не найден.")
        return
    except Exception as e:
        logger.error(f"Ошибка при чтении файла '{file_path}': {e}")
        return