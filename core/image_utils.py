"""
Утилиты для работы с изображениями: хеширование и модификации.
"""

import asyncio
import io
import random
from pathlib import Path
from typing import Optional, Tuple, List, Callable, Dict

import aiofiles
import aiofiles.os
import imagehash
from PIL import Image, ImageEnhance

from utils.config_manager import (
    BRIGHTNESS_FACTOR_RANGE,
    CONTRAST_FACTOR_RANGE,
    SIMILARITY_THRESHOLD,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from utils.logger import logger
from utils.error_handling import get_error_handler
from utils.validation import validate_image_size, validate_file_extension


def _calculate_perceptual_hash_sync(
    filepath: Path,
) -> Optional[Tuple[str, str, str]]:
    """
    Синхронная функция для вычисления нескольких перцептивных хешей.
    Возвращает кортеж из трех хешей: phash, dhash и average_hash для более
    точного определения дубликатов.
    """
    try:
        image = Image.open(filepath).convert("RGB")
        # Используем комбинацию из трех разных алгоритмов хеширования
        # для повышения точности определения дубликатов
        p_hash = str(imagehash.phash(image))
        d_hash = str(imagehash.dhash(image))
        a_hash = str(imagehash.average_hash(image))
        return (p_hash, d_hash, a_hash)
    except Exception as e:
        logger.error(f"Ошибка при вычислении хеша для '{filepath}': {e}")
        return None


async def get_file_hashes(
    directory: Path,
) -> Tuple[dict[Tuple[str, str, str], Path], List[Tuple[Path, Tuple[str, str, str], Path]]]:
    """
    Асинхронно вычисляет перцептивные хеши для всех изображений в директории.

    Оптимизированная версия с O(n log n) сложностью для поиска дубликатов.
    Использует комбинацию phash, dhash и average_hash для точности.

    Args:
        directory: Путь к директории с изображениями

    Returns:
        Tuple содержащий:
        - Словарь уникальных хешей и путей к файлам
        - Список дубликатов (путь, хеш, путь к оригиналу)

    Note:
        - Порог сходства: SIMILARITY_THRESHOLD (обычно 2 из 3 хешей)
        - Игнорирует скрытые файлы и неподдерживаемые форматы
        - Использует индексы для быстрого поиска потенциальных совпадений
    """
    loop = asyncio.get_running_loop()
    filepaths_to_process = []

    for filepath_name in await aiofiles.os.listdir(directory):
        full_path = directory / filepath_name
        if await aiofiles.os.path.isfile(full_path):
            # Игнорируем скрытые файлы, такие как .DS_Store
            if filepath_name.startswith("."):
                continue
            # Игнорируем файлы без расширений изображений
            if not any(
                filepath_name.lower().endswith(ext)
                for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
            ):
                continue
            filepaths_to_process.append(full_path)

    tasks = [
        loop.run_in_executor(None, _calculate_perceptual_hash_sync, fp)
        for fp in filepaths_to_process
    ]
    hashes_results = await asyncio.gather(*tasks)

    # Оптимизированная структура данных для быстрого поиска дубликатов
    perceptual_hashes: dict[Tuple[str, str, str], Path] = {}
    duplicates = []

    # Создаем индексы для быстрого поиска по отдельным хешам
    hash_index: Dict[str, Dict[str, List[Tuple[Tuple[str, str, str], Path]]]] = {
        "phash": {},  # phash -> [(full_hashes, path), ...]
        "dhash": {},  # dhash -> [(full_hashes, path), ...]
        "ahash": {},  # ahash -> [(full_hashes, path), ...]
    }

    for path, hashes in zip(filepaths_to_process, hashes_results):
        if not hashes:
            continue

        phash, dhash, ahash = hashes
        is_duplicate = False

        # Быстрый поиск потенциальных дубликатов через индексы
        potential_matches = set()

        # Добавляем все файлы с совпадающими отдельными хешами
        for hash_value, hash_type in [(phash, "phash"), (dhash, "dhash"), (ahash, "ahash")]:
            if hash_value in hash_index[hash_type]:
                potential_matches.update(hash_index[hash_type][hash_value])

        # Проверяем только потенциальные совпадения
        for existing_hashes, existing_path in potential_matches:
            # Считаем количество совпадающих хешей
            matching_hashes = sum(1 for i in range(
                3) if hashes[i] == existing_hashes[i])

            if matching_hashes >= SIMILARITY_THRESHOLD:
                # Нашли дубликат
                duplicates.append((path, hashes, existing_path))
                is_duplicate = True
                break

        if not is_duplicate:
            # Это новое уникальное изображение
            perceptual_hashes[hashes] = path

            # Обновляем индексы для будущих поисков
            for i, hash_type in enumerate(["phash", "dhash", "ahash"]):
                hash_value = hashes[i]
                if hash_value not in hash_index[hash_type]:
                    hash_index[hash_type][hash_value] = []
                hash_index[hash_type][hash_value].append((hashes, path))

    return perceptual_hashes, duplicates


def _modify_brightness(image: Image.Image) -> Image.Image:
    """Слегка изменяет яркость изображения."""
    image_copy = image.copy()
    enhancer = ImageEnhance.Brightness(image_copy)
    factor = 1 + random.uniform(*BRIGHTNESS_FACTOR_RANGE)
    return enhancer.enhance(factor)


def _modify_contrast(image: Image.Image) -> Image.Image:
    """Слегка изменяет контраст изображения."""
    image_copy = image.copy()
    enhancer = ImageEnhance.Contrast(image_copy)
    factor = 1 + random.uniform(*CONTRAST_FACTOR_RANGE)
    return enhancer.enhance(factor)


def _modify_crop(image: Image.Image) -> Image.Image:
    """Обрезает изображение на 1 пиксель с каждой стороны."""
    width, height = image.size
    if width > 2 and height > 2:
        return image.crop((1, 1, width - 1, height - 1))
    return image  # Не обрезаем, если изображение слишком маленькое


def _modify_add_noise(image: Image.Image) -> Image.Image:
    """Добавляет один 'шумный' пиксель в случайном месте."""
    image_copy = image.copy()
    width, height = image_copy.size
    px, py = random.randint(0, width - 1), random.randint(0, height - 1)
    noise_color = (random.randint(0, 255), random.randint(
        0, 255), random.randint(0, 255))
    image_copy.putpixel((px, py), noise_color)
    return image_copy


def get_modification_functions() -> List[Callable[[Image.Image], Image.Image]]:
    """Возвращает список доступных функций модификации изображений."""
    return [
        _modify_brightness,
        _modify_contrast,
        _modify_crop,
        _modify_add_noise,
    ]


def process_and_save_image_sync(image_data: bytes, full_path: Path, content_type: str = "") -> None:
    """
    Синхронная обработка и сохранение изображения с поддержкой разных форматов.

    Определяет формат по заголовкам, конвертирует в RGB и сохраняет как JPEG.
    При ошибках обработки сохраняет файл с расширением .unknown.

    Args:
        image_data: Байты изображения
        full_path: Полный путь для сохранения
        content_type: MIME-тип для отладки (опционально)

    Raises:
        ValueError: При превышении ограничений размера или неподдерживаемом расширении

    Note:
        - Поддерживаемые форматы: JPEG, PNG, WebP, GIF
        - Прозрачные изображения конвертируются на белый фон
        - Все изображения сохраняются как JPEG с качеством 95%
        - Нераспознанные файлы сохраняются с расширением .unknown
    """
    # Проверяем размер для обработки изображения
    if not validate_image_size(len(image_data)):
        raise ValueError(
            f"Размер изображения превышает ограничения: {len(image_data)} байт")

    # Проверяем расширение файла
    if not validate_file_extension(full_path):
        raise ValueError(
            f"Неподдерживаемое расширение файла: {full_path.suffix}")

    try:
        image_stream = io.BytesIO(image_data)
        image: Image.Image

        # Определяем формат по заголовкам файла
        if image_data.startswith(b"\xff\xd8\xff"):
            # JPEG
            image = Image.open(image_stream)
        elif image_data.startswith(b"\x89PNG"):
            # PNG
            image = Image.open(image_stream)
        elif image_data.startswith(b"RIFF") and b"WEBP" in image_data[:20]:
            # WebP
            image = Image.open(image_stream)
        elif image_data.startswith(b"GIF"):
            # GIF
            image = Image.open(image_stream)
        else:
            # Пробуем открыть как есть
            image = Image.open(image_stream)

        # Конвертируем в RGB если нужно
        if image.mode in ("RGBA", "LA", "P"):
            # Создаем белый фон для прозрачных изображений
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(
                image, mask=image.split(
                )[-1] if image.mode in ("RGBA", "LA") else None
            )
            image = background.copy()  # Добавлено .copy() для избежания проблем с ссылками
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Сохраняем как JPEG
        image.save(full_path, format="JPEG", quality=95)

    except Exception as e:
        # Обрабатываем ошибку с помощью улучшенного обработчика
        error_handler = get_error_handler()
        error_handler.handle_image_error(e, full_path, "image_processing")

        # Дополнительная информация для отладки
        logger.error(
            f"Ошибка при обработке изображения '{full_path.name}': {e}. "
            f"Content-Type: '{content_type}'. Первые байты: {image_data[:50]!r}"
        )
        # Если не удалось обработать как изображение, сохраняем с расширением .unknown
        # для последующего анализа.
        unknown_path = full_path.parent / f"{full_path.name}.unknown"
        try:
            with open(unknown_path, "wb") as f:
                f.write(image_data)
            logger.warning(
                f"Неидентифицированный файл сохранен как: {unknown_path}")
        except Exception as save_e:
            logger.error(
                f"Не удалось сохранить неидентифицированный файл {unknown_path}: {save_e}")


async def get_image_files(directory: Path) -> List[Path]:
    """Возвращает список всех файлов изображений в директории."""
    image_files = []
    for filepath_name in await aiofiles.os.listdir(directory):
        full_path = directory / filepath_name
        if await aiofiles.os.path.isfile(full_path):
            # Игнорируем скрытые файлы, такие как .DS_Store
            if filepath_name.startswith("."):
                continue
            # Проверяем расширение файла
            if full_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                image_files.append(full_path)
    return image_files
