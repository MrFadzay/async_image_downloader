"""
Модуль для работы с дубликатами изображений.
"""
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Tuple, Callable

import aiofiles.os  # type: ignore
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


def _apply_modifications_and_save_sync(
    file_path: Path, 
    modification_func1: Callable[[Image.Image], Image.Image], 
    modification_func2: Callable[[Image.Image], Image.Image]
) -> None:
    """Синхронная функция для применения модификаций и сохранения изображения."""
    image = Image.open(file_path).convert("RGB")
    modified_image = modification_func1(image)
    modified_image = modification_func2(modified_image)
    modified_image.save(file_path, format="JPEG")


async def _generate_unique_duplicate_name(
    file_path: Path, duplicate_counters: Dict[str, int]
) -> Path:
    """Генерирует уникальное имя для дубликата файла."""
    file_stem = file_path.stem
    suffix = file_path.suffix
    
    if file_stem not in duplicate_counters:
        duplicate_counters[file_stem] = 1
    else:
        duplicate_counters[file_stem] += 1
    
    duplicate_count = duplicate_counters[file_stem]
    new_path = file_path.with_name(f"{file_stem}_duplicate_{duplicate_count}{suffix}")
    
    while await aiofiles.os.path.exists(new_path):
        duplicate_count += 1
        new_path = file_path.with_name(f"{file_stem}_duplicate_{duplicate_count}{suffix}")
        duplicate_counters[file_stem] = duplicate_count
    
    return new_path


async def _check_hash_uniqueness(
    new_hashes: Tuple[str, str, str], 
    perceptual_hashes: Dict[Tuple[str, str, str], Path]
) -> bool:
    """Проверяет уникальность хеша относительно существующих."""
    if not new_hashes:
        return False
        
    from utils.config import SIMILARITY_THRESHOLD
    
    for existing_hashes in perceptual_hashes.keys():
        if existing_hashes == new_hashes:
            return False
        
        matching_hashes = sum(
            1 for i in range(3) if new_hashes[i] == existing_hashes[i]
        )
        if matching_hashes >= SIMILARITY_THRESHOLD:
            return False
    
    return True


async def _attempt_uniquification(
    file_path: Path, 
    modification_functions: List[Callable[[Image.Image], Image.Image]],
    perceptual_hashes: Dict[Tuple[str, str, str], Path],
    attempt: int
) -> Tuple[bool, Tuple[str, str, str]]:
    """Выполняет одну попытку уникализации изображения."""
    loop = asyncio.get_running_loop()
    
    modification_func1 = random.choice(modification_functions)
    modification_func2 = random.choice(modification_functions)
    
    logger.info(
        f"  -> Попытка {attempt + 1}/{MAX_UNIQUIFY_ATTEMPTS}: "
        f"применяем '{modification_func1.__name__}' "
        f"и '{modification_func2.__name__}'..."
    )
    
    await loop.run_in_executor(
        None, _apply_modifications_and_save_sync, 
        file_path, modification_func1, modification_func2
    )
    
    new_hashes = await loop.run_in_executor(
        None, _calculate_perceptual_hash_sync, file_path
    )
    
    is_unique = await _check_hash_uniqueness(new_hashes, perceptual_hashes)
    
    return is_unique, new_hashes


async def handle_duplicates(directory: Path) -> None:
    """
    Находит дубликаты изображений в директории и переименовывает их для идентификации.
    
    Использует перцептивное хеширование (phash, dhash, average_hash) для обнаружения 
    визуально одинаковых изображений. Дубликаты переименовываются с добавлением 
    суффикса '_duplicate_N' для последующей ручной проверки.
    
    Args:
        directory: Путь к директории с изображениями для поиска дубликатов
    
    Returns:
        None: Функция ничего не возвращает, вся информация выводится через логи
    
    Raises:
        OSError: При ошибках доступа к файлам или директориям
        PIL.UnidentifiedImageError: При ошибках обработки изображений
    
    Examples:
        >>> import asyncio
        >>> from pathlib import Path
        >>> 
        >>> async def find_dupes_example():
        ...     images_dir = Path("./downloaded_images")
        ...     await handle_duplicates(images_dir)
        ...     print("Поиск дубликатов завершён")
        >>> 
        >>> # asyncio.run(find_dupes_example())
        
        Пример с командной строки:
        >>> # python main.py find-duplicates ./my_images
        
        Пример результата:
        До обработки:
        - photo1.jpg
        - vacation.jpg  (дубликат photo1.jpg)
        - sunset.png
        
        После обработки:
        - photo1.jpg
        - vacation_duplicate_1.jpg
        - sunset.png
    
    Note:
        - Поддерживаемые форматы: JPEG, PNG, GIF, BMP, TIFF, WebP
        - Порог сходства: 2 из 3 хешей должны совпадать
        - Скрытые файлы (начинающиеся с '.') игнорируются
        - Нумерация дубликатов начинается с 1 для каждого файла
    """
    logger.info(f"Поиск дубликатов в '{directory}'...")
    renamed_count = 0
    
    await create_dir(directory)
    _unique_hashes, duplicates_info = await get_file_hashes(directory)
    duplicate_counters: Dict[str, int] = {}
    
    for full_path, hash_tuple, original_path in duplicates_info:
        logger.info(f"Найден дубликат: '{full_path}' (оригинал: '{original_path}')")
        
        new_path = await _generate_unique_duplicate_name(full_path, duplicate_counters)
        await aiofiles.os.rename(full_path, new_path)
        renamed_count += 1
        
        logger.info(f"  -> Переименован в: '{new_path}'")
    
    logger.info(f"Обработано {renamed_count} дубликатов (переименовано).")


async def uniquify_duplicates(directory: Path) -> None:
    """
    Находит дубликаты изображений и модифицирует их для уникальности.
    
    Применяет случайные модификации (яркость, контраст, обрезка, шум) к дубликатам
    для создания технически уникальных файлов, сохраняя визуальное качество.
    
    Args:
        directory: Директория для обработки дубликатов
    
    Returns:
        None: Результаты выводятся через логи
    
    Note:
        - Максимум попыток уникализации: MAX_UNIQUIFY_ATTEMPTS (обычно 10)
        - Применяется комбинация из 2 случайных модификаций за попытку
        - Если уникализация не удалась, файл остается без изменений
        - CLI: python main.py uniquify ./images
    """
    logger.info(f"Поиск и уникализация дубликатов в '{directory}'...")
    uniquified_count = 0
    
    await create_dir(directory)
    
    perceptual_hashes, duplicates_info = await get_file_hashes(directory)
    modification_functions = get_modification_functions()
    
    for full_path, original_hash, original_path_for_hash in duplicates_info:
        logger.info(
            f"Найден дубликат: '{full_path}' "
            f"(оригинал: '{original_path_for_hash}')"
        )
        
        is_uniquified = False
        
        for attempt in range(MAX_UNIQUIFY_ATTEMPTS):
            try:
                is_unique, new_hashes = await _attempt_uniquification(
                    full_path, modification_functions, perceptual_hashes, attempt
                )
                
                if is_unique and new_hashes:
                    perceptual_hashes[new_hashes] = full_path
                    uniquified_count += 1
                    logger.info(f"  УСПЕХ: Изображение '{full_path}' успешно уникализировано.")
                    is_uniquified = True
                    break
                else:
                    logger.info("  НЕУДАЧА: Новый хеш всё ещё является дубликатом. Повторная попытка...")
                
            except Exception as e:
                logger.error(f"  ОШИБКА при уникализации '{full_path}' (попытка {attempt + 1}): {e}")
                break
        
        if not is_uniquified:
            logger.warning(
                f"ПРЕДУПРЕЖДЕНИЕ: Не удалось уникализировать '{full_path}' "
                f"после {MAX_UNIQUIFY_ATTEMPTS} попыток."
            )
    
    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} дубликатов.")


async def uniquify_all_images(directory: Path) -> None:
    """
    Уникализирует все изображения в директории (не только дубликаты).
    
    Применяет случайные модификации к каждому изображению, делая все 
    файлы технически уникальными для поисковых систем.
    
    Args:
        directory: Директория с изображениями для обработки
    
    Note:
        - Обрабатываются все изображения, не только дубликаты
        - Применяется комбинация из 2 случайных модификаций
        - CLI: python main.py uniquify-all ./images
    """
    logger.info(f"Уникализация всех изображений в '{directory}'...")
    uniquified_count = 0
    
    await create_dir(directory)
    
    modification_functions = get_modification_functions()
    loop = asyncio.get_running_loop()
    
    image_files = await get_image_files(directory)
    logger.info(f"Найдено {len(image_files)} изображений для уникализации.")
    
    for full_path in image_files:
        logger.info(f"Уникализация изображения: '{full_path}'")
        
        try:
            modification_func1 = random.choice(modification_functions)
            modification_func2 = random.choice(modification_functions)
            
            logger.info(
                f"  -> Применяем '{modification_func1.__name__}' "
                f"и '{modification_func2.__name__}'..."
            )
            
            await loop.run_in_executor(
                None, _apply_modifications_and_save_sync, 
                full_path, modification_func1, modification_func2
            )
            uniquified_count += 1
            
            logger.info(f"  УСПЕХ: Изображение '{full_path}' уникализировано.")
            
        except Exception as e:
            logger.error(f"  ОШИБКА при уникализации '{full_path}': {e}")
    
    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} изображений.")
