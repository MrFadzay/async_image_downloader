"""
Модуль для работы с дубликатами изображений.
"""
import asyncio
import random
from pathlib import Path

import aiofiles.os
from PIL import Image

from utils.config import MAX_UNIQUIFY_ATTEMPTS
from utils.logger import logger
from core.image_utils import (
    get_file_hashes,
    get_modification_functions,
    _calculate_perceptual_hash_sync,
    get_image_files
)
from core.downloader import create_dir


async def find_duplicates(directory: Path) -> list:
    """
    Находит дубликаты изображений в директории.

    Args:
        directory: Директория для поиска дубликатов

    Returns:
        list: Список кортежей (путь_к_дубликату, хеш, путь_к_оригиналу)
    """
    logger.info(f"Поиск дубликатов в '{directory}'...")
    
    await create_dir(directory)
    _unique_hashes, duplicates_info = await get_file_hashes(directory)
    
    logger.info(f"Найдено {len(duplicates_info)} дубликатов.")
    return duplicates_info


async def rename_duplicates_from_list(duplicates_list: list) -> int:
    """
    Переименовывает дубликаты из предоставленного списка.

    Args:
        duplicates_list: Список кортежей (путь_к_дубликату, хеш, путь_к_оригиналу)

    Returns:
        int: Количество переименованных файлов
    """
    logger.info(f"Переименование {len(duplicates_list)} дубликатов...")
    renamed_count = 0

    # Словарь для отслеживания количества дубликатов для каждого оригинала
    duplicate_counters = {}

    for full_path, hash_tuple, original_path in duplicates_list:
        logger.info(
            f"Переименование дубликата: '{full_path}' (оригинал: '{original_path}')")

        # Получаем имя оригинального файла для группировки дубликатов
        original_stem = original_path.stem

        # Инициализируем счетчик для этого оригинала, если его еще нет
        if original_stem not in duplicate_counters:
            duplicate_counters[original_stem] = 1
        else:
            duplicate_counters[original_stem] += 1

        # Используем счетчик для этого конкретного оригинала
        duplicate_count = duplicate_counters[original_stem]

        stem = full_path.stem
        suffix = full_path.suffix

        # Формируем новое имя с номером дубликата
        new_full_path = full_path.with_name(
            f"{stem}_duplicate_{duplicate_count}{suffix}")

        # Проверяем, существует ли уже файл с таким именем
        while await aiofiles.os.path.exists(new_full_path):
            duplicate_count += 1
            new_full_path = full_path.with_name(
                f"{stem}_duplicate_{duplicate_count}{suffix}")
            # Обновляем счетчик для этого оригинала
            duplicate_counters[original_stem] = duplicate_count

        await aiofiles.os.rename(full_path, new_full_path)
        renamed_count += 1
        logger.info(f"  -> Переименован в: '{new_full_path}'")

    logger.info(f"Обработано {renamed_count} дубликатов (переименовано).")
    return renamed_count


async def handle_duplicates(directory: Path) -> None:
    """
    Находит дубликаты изображений и переименовывает их (для CLI режима).

    Args:
        directory: Директория для поиска дубликатов
    """
    duplicates_list = await find_duplicates(directory)
    await rename_duplicates_from_list(duplicates_list)


async def uniquify_duplicates(directory: Path) -> None:
    """
    Находит дубликаты изображений и модифицирует их для уникальности.

    Args:
        directory: Директория для обработки дубликатов
    """
    logger.info(f"Поиск и уникализация дубликатов в '{directory}'...")
    uniquified_count = 0

    await create_dir(directory)

    perceptual_hashes, duplicates_info = await get_file_hashes(directory)
    modification_functions = get_modification_functions()
    loop = asyncio.get_running_loop()

    for full_path, original_hash, original_path_for_hash in duplicates_info:
        logger.info(
            f"Найден дубликат: '{full_path}' (оригинал: '{original_path_for_hash}')")

        is_uniquified = False

        for attempt in range(MAX_UNIQUIFY_ATTEMPTS):
            try:
                image = Image.open(full_path).convert("RGB")

                # Применяем несколько модификаций одновременно для большей эффективности
                modification_func1 = random.choice(modification_functions)
                modification_func2 = random.choice(modification_functions)

                logger.info(
                    f"  -> Попытка {attempt + 1}/{MAX_UNIQUIFY_ATTEMPTS}: "
                    f"применяем '{modification_func1.__name__}' и '{modification_func2.__name__}'..."
                )

                # Применяем последовательно две модификации
                modified_image = modification_func1(image)
                modified_image = modification_func2(modified_image)

                modified_image.save(full_path, format="JPEG")

                new_hashes = await loop.run_in_executor(
                    None, _calculate_perceptual_hash_sync, full_path
                )

                # Проверяем, является ли новый хеш уникальным
                is_unique = True
                if new_hashes:
                    # Проверяем, нет ли похожих хешей в нашем словаре
                    from utils.config import SIMILARITY_THRESHOLD

                    for existing_hashes in perceptual_hashes.keys():
                        if existing_hashes == new_hashes:
                            is_unique = False
                            break

                        # Считаем количество совпадающих хешей
                        matching_hashes = sum(1 for i in range(
                            3) if new_hashes[i] == existing_hashes[i])
                        if matching_hashes >= SIMILARITY_THRESHOLD:
                            is_unique = False
                            break

                if is_unique and new_hashes:
                    perceptual_hashes[new_hashes] = full_path
                    uniquified_count += 1
                    logger.info(
                        f"  УСПЕХ: Изображение '{full_path}' успешно уникализировано.")
                    is_uniquified = True
                    break
                else:
                    logger.info(
                        f"  НЕУДАЧА: Новый хеш все еще является дубликатом. Повторная попытка...")

            except Exception as e:
                logger.error(
                    f"  ОШИБКА при уникализации '{full_path}' (попытка {attempt + 1}): {e}")
                break

        if not is_uniquified:
            logger.warning(
                f"ПРЕДУПРЕЖДЕНИЕ: Не удалось уникализировать '{full_path}' "
                f"после {MAX_UNIQUIFY_ATTEMPTS} попыток."
            )

    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} дубликатов.")


async def uniquify_all_images(directory: Path) -> None:
    """
    Уникализирует все изображения в директории.

    Args:
        directory: Директория для обработки
    """
    logger.info(f"Уникализация всех изображений в '{directory}'...")
    uniquified_count = 0

    await create_dir(directory)

    modification_functions = get_modification_functions()

    # Получаем список всех файлов изображений в директории
    image_files = await get_image_files(directory)
    logger.info(f"Найдено {len(image_files)} изображений для уникализации.")

    for full_path in image_files:
        logger.info(f"Уникализация изображения: '{full_path}'")

        try:
            image = Image.open(full_path).convert("RGB")

            # Применяем случайные модификации
            modification_func1 = random.choice(modification_functions)
            modification_func2 = random.choice(modification_functions)

            logger.info(
                f"  -> Применяем '{modification_func1.__name__}' и '{modification_func2.__name__}'..."
            )

            # Применяем последовательно две модификации
            modified_image = modification_func1(image)
            modified_image = modification_func2(modified_image)

            modified_image.save(full_path, format="JPEG")
            uniquified_count += 1

            logger.info(f"  УСПЕХ: Изображение '{full_path}' уникализировано.")

        except Exception as e:
            logger.error(f"  ОШИБКА при уникализации '{full_path}': {e}")

    logger.info(
        f"\nЗавершено. Уникализировано {uniquified_count} изображений.")
