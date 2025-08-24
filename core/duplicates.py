"""
Модуль для работы с дубликатами изображений.
"""

import asyncio
import random
from pathlib import Path
from typing import Dict, List, Tuple, Callable
import time

import aiofiles.os  # type: ignore
from PIL import Image

from utils.config_manager import MAX_UNIQUIFY_ATTEMPTS
from utils.logger import logger
from utils.progress import get_progress_tracker, show_operation_summary
from utils.confirmation import confirm_destructive_operation
from utils.error_handling import get_error_handler, ProgressErrorHandler
from core.image_utils import (
    get_file_hashes,
    get_modification_functions,
    _calculate_perceptual_hash_sync,
    get_image_files,
)
from core.downloader import create_dir


def _apply_modifications_and_save_sync(
    file_path: Path,
    modification_func1: Callable[[Image.Image], Image.Image],
    modification_func2: Callable[[Image.Image], Image.Image],
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
    new_hashes: Tuple[str, str, str], perceptual_hashes: Dict[Tuple[str, str, str], Path]
) -> bool:
    """Проверяет уникальность хеша относительно существующих."""
    if not new_hashes:
        return False

    from utils.config_manager import SIMILARITY_THRESHOLD

    for existing_hashes in perceptual_hashes.keys():
        if existing_hashes == new_hashes:
            return False

        matching_hashes = sum(1 for i in range(3) if new_hashes[i] == existing_hashes[i])
        if matching_hashes >= SIMILARITY_THRESHOLD:
            return False

    return True


async def _attempt_uniquification(
    file_path: Path,
    modification_functions: List[Callable[[Image.Image], Image.Image]],
    perceptual_hashes: Dict[Tuple[str, str, str], Path],
    attempt: int,
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
        None, _apply_modifications_and_save_sync, file_path, modification_func1, modification_func2
    )

    new_hashes = await loop.run_in_executor(None, _calculate_perceptual_hash_sync, file_path)

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
    start_time = time.time()
    renamed_count = 0

    await create_dir(directory)

    # Получаем список файлов для прогресс-бара
    image_files = await get_image_files(directory)
    total_files = len(image_files)

    if total_files == 0:
        logger.warning("В директории не найдено изображений для обработки.")
        return

    logger.info(f"Найдено {total_files} изображений для анализа.")

    progress_tracker = get_progress_tracker()

    # Анализируем файлы с прогресс-баром
    async with progress_tracker.track_duplicate_progress(
        total_files, "Анализ изображений на дубликаты"
    ) as progress_bar:
        _unique_hashes, duplicates_info = await get_file_hashes(directory)
        # Обновляем прогресс после завершения анализа
        progress_bar.update(total_files)

    duplicate_counters: Dict[str, int] = {}

    # Запрашиваем подтверждение перед переименованием дубликатов
    if duplicates_info:
        confirmed = await confirm_destructive_operation(
            "rename_duplicates", duplicates_info=duplicates_info, directory=directory
        )

        if not confirmed:
            logger.info("Операция переименования отменена пользователем.")
            return

    # Обрабатываем найденные дубликаты
    if duplicates_info:
        async with progress_tracker.track_duplicate_progress(
            len(duplicates_info), "Переименование дубликатов"
        ) as rename_progress:
            for full_path, hash_tuple, original_path in duplicates_info:
                logger.info(f"Найден дубликат: '{full_path}' (оригинал: '{original_path}')")

                new_path = await _generate_unique_duplicate_name(full_path, duplicate_counters)
                await aiofiles.os.rename(full_path, new_path)
                renamed_count += 1

                logger.info(f"  -> Переименован в: '{new_path}'")
                rename_progress.update(1)

    elapsed_time = time.time() - start_time

    # Показываем сводку операции
    await show_operation_summary(
        "Поиск дубликатов",
        total_files,
        total_files - renamed_count,  # успешно обработано
        0,  # ошибок при анализе
        elapsed_time,
    )

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
    start_time = time.time()
    uniquified_count = 0
    failed_count = 0

    await create_dir(directory)

    # Получаем список файлов для прогресс-бара
    image_files = await get_image_files(directory)
    total_files = len(image_files)

    if total_files == 0:
        logger.warning("В директории не найдено изображений для обработки.")
        return

    logger.info(f"Найдено {total_files} изображений для анализа.")

    progress_tracker = get_progress_tracker()

    # Анализируем файлы на дубликаты
    async with progress_tracker.track_duplicate_progress(
        total_files, "Поиск дубликатов"
    ) as analysis_progress:
        perceptual_hashes, duplicates_info = await get_file_hashes(directory)
        analysis_progress.update(total_files)

    modification_functions = get_modification_functions()

    if not duplicates_info:
        logger.info("Дубликаты не найдены.")
        await show_operation_summary(
            "Уникализация дубликатов",
            total_files,
            total_files,  # все уникальны
            0,
            time.time() - start_time,
        )
        return

    logger.info(f"Найдено {len(duplicates_info)} дубликатов для уникализации.")

    # Запрашиваем подтверждение перед модификацией
    confirmed = await confirm_destructive_operation(
        "modify_duplicates", duplicates_info=duplicates_info, directory=directory
    )

    if not confirmed:
        logger.info("Операция уникализации отменена пользователем.")
        return

    # Инициализируем обработчик ошибок с прогрессом
    progress_error_handler = ProgressErrorHandler(len(duplicates_info), "Уникализация дубликатов")

    # Обрабатываем найденные дубликаты
    async with progress_tracker.track_uniquify_progress(
        len(duplicates_info), "Уникализация дубликатов"
    ) as uniquify_progress:
        for full_path, original_hash, original_path_for_hash in duplicates_info:
            logger.info(
                f"Найден дубликат: '{full_path}' " f"(оригинал: '{original_path_for_hash}')"
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
                        progress_error_handler.report_success()
                        logger.info(f"  ✅ Успешно: '{full_path.name}' уникализирован")
                        is_uniquified = True
                        break
                    else:
                        if attempt < MAX_UNIQUIFY_ATTEMPTS - 1:
                            print(
                                f"   🔄 Попытка {attempt + 1}: хеш все еще не уникален, повторяем..."
                            )

                except Exception as e:
                    progress_error_handler.report_error(e, f"уникализация {full_path.name}")
                    break

            if not is_uniquified:
                failed_count += 1
                progress_error_handler.report_error(
                    Exception(f"Не удалось уникализировать за {MAX_UNIQUIFY_ATTEMPTS} попыток"),
                    f"{full_path.name}",
                )
                print(
                    f"   ⚠️  Не удалось уникализировать '{full_path.name}' за {MAX_UNIQUIFY_ATTEMPTS} попыток"
                )

            uniquify_progress.update(1)

    elapsed_time = time.time() - start_time

    # Показываем сводку операции
    await show_operation_summary(
        "Уникализация дубликатов",
        len(duplicates_info),
        uniquified_count,
        failed_count,
        elapsed_time,
    )

    logger.info(f"Завершено. Уникализировано {uniquified_count} дубликатов.")

    # Показываем детальный отчет об ошибках
    print(progress_error_handler.get_final_report())


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
    start_time = time.time()
    uniquified_count = 0
    failed_count = 0

    await create_dir(directory)

    modification_functions = get_modification_functions()
    loop = asyncio.get_running_loop()

    image_files = await get_image_files(directory)
    total_files = len(image_files)

    if total_files == 0:
        logger.warning("В директории не найдено изображений для обработки.")
        return

    logger.info(f"Найдено {total_files} изображений для уникализации.")

    # Запрашиваем подтверждение перед модификацией всех файлов
    confirmed = await confirm_destructive_operation(
        "modify_all", image_files=image_files, directory=directory
    )

    if not confirmed:
        logger.info("Операция уникализации всех изображений отменена.")
        return

    progress_tracker = get_progress_tracker()

    # Обрабатываем все изображения с прогресс-баром
    async with progress_tracker.track_uniquify_progress(
        total_files, "Уникализация всех изображений"
    ) as progress_bar:
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
                    None,
                    _apply_modifications_and_save_sync,
                    full_path,
                    modification_func1,
                    modification_func2,
                )
                uniquified_count += 1

                logger.info(f"  УСПЕХ: Изображение '{full_path}' уникализировано.")

            except Exception as e:
                failed_count += 1
                logger.error(f"  ОШИБКА при уникализации '{full_path}': {e}")

            progress_bar.update(1)

    elapsed_time = time.time() - start_time

    # Показываем сводку операции
    await show_operation_summary(
        "Уникализация всех изображений", total_files, uniquified_count, failed_count, elapsed_time
    )

    logger.info(f"Завершено. Уникализировано {uniquified_count} изображений.")
