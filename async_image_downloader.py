import asyncio
from datetime import datetime
import io
import logging
from pathlib import Path
import random
import re
import sys

import aiofiles
import aiofiles.os
import aiohttp
import imagehash
from PIL import Image, ImageEnhance
import questionary


def get_base_dir():
    """
    Получает базовую директорию.
    Для обычного скрипта - это папка со скриптом.
    Для упакованного в .exe приложения - это папка с .exe файлом.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Мы запущены из .exe, созданного PyInstaller
        return Path(sys.executable).parent
    else:
        # Мы запущены как обычный .py скрипт
        return Path(__file__).parent


BASE_DIR = get_base_dir()
IMAGE_DIR = BASE_DIR / 'images'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Вывод в консоль
        logging.FileHandler(BASE_DIR / 'app.log')  # Вывод в файл
    ]
)
logger = logging.getLogger(__name__)


# Семафор для ограничения количества одновременных загрузок
semaphore = asyncio.Semaphore(10)


async def download_file(session: aiohttp.ClientSession, url: str, target_dir: Path, file_index: int):
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
            async with session.get(url) as response:
                response.raise_for_status()
                image_data = await response.read()
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, _process_and_save_image_sync, image_data, full_path
                )
                logger.info(f"Изображение сохранено как JPEG: {full_path}")

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при скачивании {url}: {e}")
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка или ошибка преобразования при "
                f"скачивании/сохранении {url}: {e}"
            )


def _process_and_save_image_sync(image_data: bytes, full_path: Path):
    """Синхронная функция для обработки и сохранения изображения."""
    image_stream = io.BytesIO(image_data)
    image = Image.open(image_stream).convert("RGB")
    image.save(full_path, format="JPEG")


async def create_dir(dir_name: Path) -> None:
    await aiofiles.os.makedirs(
        dir_name,
        exist_ok=True,
    )


def _calculate_perceptual_hash_sync(
    filepath: Path
) -> tuple[str, str, str] | None:
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


BRIGHTNESS_FACTOR_RANGE = (-0.02, 0.02)
CONTRAST_FACTOR_RANGE = (-0.03, 0.03)
MAX_UNIQUIFY_ATTEMPTS = 10


def _modify_brightness(image: Image.Image) -> Image.Image:
    """Слегка изменяет яркость изображения."""
    enhancer = ImageEnhance.Brightness(image)
    factor = 1 + random.uniform(*BRIGHTNESS_FACTOR_RANGE)
    return enhancer.enhance(factor)


def _modify_contrast(image: Image.Image) -> Image.Image:
    """Слегка изменяет контраст изображения."""
    enhancer = ImageEnhance.Contrast(image)
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
    width, height = image.size
    px, py = random.randint(0, width - 1), random.randint(0, height - 1)
    noise_color = (random.randint(0, 255), random.randint(
        0, 255), random.randint(0, 255))
    image.putpixel((px, py), noise_color)
    return image


async def _get_file_hashes(directory: Path) -> tuple[dict[tuple[str, str, str], Path], list[tuple[Path, tuple[str, str, str], Path]]]:
    """
    Асинхронно вычисляет перцептивные хеши для всех файлов в директории.
    Теперь использует комбинацию из трех хешей для более точного определения дубликатов.
    """
    loop = asyncio.get_running_loop()
    filepaths_to_process = []

    for filepath in await aiofiles.os.listdir(directory):
        full_path = directory / filepath
        if await aiofiles.os.path.isfile(full_path):
            filepaths_to_process.append(full_path)

    tasks = [
        loop.run_in_executor(None, _calculate_perceptual_hash_sync, fp)
        for fp in filepaths_to_process
    ]
    hashes_results = await asyncio.gather(*tasks)

    # Словарь для хранения хешей и соответствующих им путей
    perceptual_hashes: dict[tuple[str, str, str], Path] = {}
    duplicates = []

    # Порог сходства для определения дубликатов (количество совпадающих хешей)
    similarity_threshold = 2  # Если 2 из 3 хешей совпадают, считаем изображения дубликатами

    for path, hashes in zip(filepaths_to_process, hashes_results):
        if not hashes:
            continue

        # Проверяем, есть ли уже похожие хеши в нашем словаре
        is_duplicate = False
        for existing_hashes, existing_path in perceptual_hashes.items():
            # Считаем количество совпадающих хешей
            matching_hashes = sum(1 for i in range(
                3) if hashes[i] == existing_hashes[i])

            if matching_hashes >= similarity_threshold:
                # Нашли дубликат
                duplicates.append((path, hashes, existing_path))
                is_duplicate = True
                break

        if not is_duplicate:
            # Это новое уникальное изображение
            perceptual_hashes[hashes] = path

    return perceptual_hashes, duplicates


async def uniquify_duplicates(directory: Path) -> None:
    logger.info(f"Поиск и уникализация дубликатов в '{directory}'...")
    uniquified_count = 0

    await create_dir(directory)

    perceptual_hashes, duplicates_info = await _get_file_hashes(directory)

    modification_functions = [
        _modify_brightness,
        _modify_contrast,
        _modify_crop,
        _modify_add_noise,
    ]

    loop = asyncio.get_running_loop()

    for full_path, original_hash, original_path_for_hash in duplicates_info:
        logger.info(
            f"Найден дубликат: '{full_path}' "
            f"(оригинал: '{original_path_for_hash}')"
        )

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
                    similarity_threshold = 2  # Если 2 из 3 хешей совпадают, считаем изображения дубликатами

                    for existing_hashes in perceptual_hashes.keys():
                        if existing_hashes == new_hashes:
                            is_unique = False
                            break

                        # Считаем количество совпадающих хешей
                        matching_hashes = sum(1 for i in range(
                            3) if new_hashes[i] == existing_hashes[i])
                        if matching_hashes >= similarity_threshold:
                            is_unique = False
                            break

                if is_unique and new_hashes:
                    perceptual_hashes[new_hashes] = full_path
                    uniquified_count += 1
                    logger.info(
                        f"  УСПЕХ: Изображение '{full_path}' "
                        f"успешно уникализировано."
                    )
                    is_uniquified = True
                    break
                else:
                    logger.info(
                        f"  НЕУДАЧА: Новый хеш все еще "
                        f"является дубликатом. Повторная попытка..."
                    )

            except Exception as e:
                logger.error(
                    f"  ОШИБКА при уникализации '{full_path}' "
                    f"(попытка {attempt + 1}): {e}"
                )
                break

        if not is_uniquified:
            logger.warning(
                f"ПРЕДУПРЕЖДЕНИЕ: Не удалось уникализировать '{full_path}' "
                f"после {MAX_UNIQUIFY_ATTEMPTS} попыток."
            )

    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} дубликатов.")


async def uniquify_all_images(directory: Path) -> None:
    """Уникализирует все изображения в директории."""
    logger.info(f"Уникализация всех изображений в '{directory}'...")
    uniquified_count = 0

    await create_dir(directory)

    modification_functions = [
        _modify_brightness,
        _modify_contrast,
        _modify_crop,
        _modify_add_noise,
    ]

    # Получаем список всех файлов изображений в директории
    image_files = []
    for filepath in await aiofiles.os.listdir(directory):
        full_path = directory / filepath
        if await aiofiles.os.path.isfile(full_path):
            # Проверяем расширение файла
            if full_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
                image_files.append(full_path)

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

    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} изображений.")


async def handle_duplicates(directory: Path) -> None:
    logger.info(f"Поиск дубликатов в '{directory}'...")
    renamed_count = 0

    await create_dir(directory)

    _unique_hashes, duplicates_info = await _get_file_hashes(directory)

    # Словарь для отслеживания количества дубликатов для каждого оригинала
    duplicate_counters = {}

    for full_path, hash_tuple, original_path in duplicates_info:
        logger.info(
            f"Найден дубликат: '{full_path}' (оригинал: '{original_path}')")

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
            f"{stem}_duplicate_{duplicate_count}{suffix}"
        )

        # Проверяем, существует ли уже файл с таким именем
        while await aiofiles.os.path.exists(new_full_path):
            duplicate_count += 1
            new_full_path = full_path.with_name(
                f"{stem}_duplicate_{duplicate_count}{suffix}"
            )
            # Обновляем счетчик для этого оригинала
            duplicate_counters[original_stem] = duplicate_count

        await aiofiles.os.rename(full_path, new_full_path)
        renamed_count += 1
        logger.info(f"  -> Переименован в: '{new_full_path}'")

    logger.info(f"Обработано {renamed_count} дубликатов (переименовано).")


async def download_images_for_folder(folder_name: str, urls: list[str], start_index: int = 1000):
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
                        logger.info(
                            f"Обработка папки '{current_folder}' с {len(current_urls)} URL")
                        await download_images_for_folder(current_folder, current_urls, start_index)
                        logger.info(
                            f"Скачано {len(current_urls)} изображений в папку '{current_folder}'")
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
                logger.info(
                    f"Обработка последней папки '{current_folder}' с {len(current_urls)} URL")
                await download_images_for_folder(current_folder, current_urls, start_index)
                logger.info(
                    f"Скачано {len(current_urls)} изображений в папку '{current_folder}'")

    except FileNotFoundError:
        logger.error(f"Ошибка: Файл '{file_path}' не найден.")
        return
    except Exception as e:
        logger.error(f"Ошибка при чтении файла '{file_path}': {e}")
        return


async def run_interactive_mode():
    """Запускает интерактивный режим с вопросами к пользователю."""
    while True:
        command = await questionary.select(
            "Что вы хотите сделать?",
            choices=[
                "Скачать изображения",
                "Работа с дубликатами",
                "Уникализация",
                "Выход"
            ]
        ).ask_async()

        if command == "Скачать изображения":
            download_type = await questionary.select(
                "Откуда скачивать?",
                choices=["Из файла", "По списку URL"]
            ).ask_async()

            if download_type == "Из файла":
                file_path_str = await questionary.path(
                    "Укажите путь к файлу с URL:"
                ).ask_async()
                if file_path_str:
                    # Удаляем лишние пробелы в начале и конце пути
                    file_path_str = file_path_str.strip()
                    start_index_str = await questionary.text(
                        "Введите начальный индекс для изображений (по умолчанию 1000):",
                        default="1000"
                    ).ask_async()
                    start_index = int(
                        start_index_str) if start_index_str.isdigit() else 1000
                    try:
                        # Проверяем существование файла перед обработкой
                        path_obj = Path(file_path_str)
                        if not path_obj.exists():
                            logger.error(
                                f"Файл '{file_path_str}' не существует.")
                            continue
                        await download_images_from_file(path_obj, start_index)
                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке пути '{file_path_str}': {e}")

            elif download_type == "По списку URL":
                urls_str = await questionary.text(
                    "Введите URL через пробел или точку с запятой:"
                ).ask_async()
                dest_folder = await questionary.text(
                    "Введите имя папки для сохранения:",
                    default="manual_downloads"
                ).ask_async()
                start_index_str = await questionary.text(
                    "Введите начальный индекс для изображений (по умолчанию 1000):",
                    default="1000"
                ).ask_async()
                start_index = int(
                    start_index_str) if start_index_str.isdigit() else 1000
                if urls_str and dest_folder:
                    urls = [url for url in re.split(
                        r'[\s;]+', urls_str.strip()) if url]
                    await download_images_for_folder(dest_folder, urls, start_index)

        elif command == "Работа с дубликатами":
            duplicate_action = await questionary.select(
                "Выберите действие с дубликатами:",
                choices=[
                    "Найти и переименовать дубликаты",
                    "Уникализировать дубликаты",
                    "Назад"
                ]
            ).ask_async()

            if duplicate_action == "Найти и переименовать дубликаты":
                dir_path_str = await questionary.path(
                    "Укажите путь к директории для проверки:"
                ).ask_async()
                if dir_path_str:
                    # Очищаем путь от лишних кавычек, пробелов и специальных символов
                    dir_path_str = dir_path_str.strip()
                    # Удаляем кавычки и амперсанды, которые могут вызвать проблемы
                    if dir_path_str.startswith(("'", '"', '&')):
                        dir_path_str = dir_path_str.lstrip("'\"& ")
                    if dir_path_str.endswith(("'", '"')):
                        dir_path_str = dir_path_str.rstrip("'\"")

                    logger.info(f"Обрабатываем путь: '{dir_path_str}'")
                    try:
                        path_obj = Path(dir_path_str)
                        if not path_obj.exists():
                            logger.error(
                                f"Директория '{dir_path_str}' не существует.")
                            continue
                        await handle_duplicates(path_obj)
                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке пути '{dir_path_str}': {e}")

            elif duplicate_action == "Уникализировать дубликаты":
                dir_path_str = await questionary.path(
                    "Укажите путь к директории для уникализации дубликатов:"
                ).ask_async()
                if dir_path_str:
                    # Очищаем путь от лишних кавычек, пробелов и специальных символов
                    dir_path_str = dir_path_str.strip()
                    # Удаляем кавычки и амперсанды, которые могут вызвать проблемы
                    if dir_path_str.startswith(("'", '"', '&')):
                        dir_path_str = dir_path_str.lstrip("'\"& ")
                    if dir_path_str.endswith(("'", '"')):
                        dir_path_str = dir_path_str.rstrip("'\"")

                    logger.info(f"Обрабатываем путь: '{dir_path_str}'")
                    try:
                        path_obj = Path(dir_path_str)
                        if not path_obj.exists():
                            logger.error(
                                f"Директория '{dir_path_str}' не существует.")
                            continue
                        await uniquify_duplicates(path_obj)
                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке пути '{dir_path_str}': {e}")

        elif command == "Уникализация":
            dir_path_str = await questionary.path(
                "Укажите путь к директории для уникализации всех изображений:"
            ).ask_async()
            if dir_path_str:
                # Очищаем путь от лишних кавычек, пробелов и специальных символов
                dir_path_str = dir_path_str.strip()
                # Удаляем кавычки и амперсанды, которые могут вызвать проблемы
                if dir_path_str.startswith(("'", '"', '&')):
                    dir_path_str = dir_path_str.lstrip("'\"& ")
                if dir_path_str.endswith(("'", '"')):
                    dir_path_str = dir_path_str.rstrip("'\"")

                logger.info(f"Обрабатываем путь: '{dir_path_str}'")
                try:
                    path_obj = Path(dir_path_str)
                    if not path_obj.exists():
                        logger.error(
                            f"Директория '{dir_path_str}' не существует.")
                        continue
                    await uniquify_all_images(path_obj)
                except Exception as e:
                    logger.error(
                        f"Ошибка при обработке пути '{dir_path_str}': {e}")

        elif command == "Выход" or command is None:
            logger.info("Завершение работы.")
            break


if __name__ == '__main__':
    import argparse

    # Проверяем, были ли переданы аргументы командной строки
    if len(sys.argv) > 1:
        # ----- РЕЖИМ С АРГУМЕНТАМИ (ДЛЯ АВТОМАТИЗАЦИИ) -----
        parser = argparse.ArgumentParser(
            description="Async Image Downloader and Processor.")
        subparsers = parser.add_subparsers(dest="command", required=True)

        # Команда download
        p_download = subparsers.add_parser(
            "download", help="Download images from a file or URLs.")
        p_download.add_argument("-f", "--file", type=Path,
                                help="Path to a file with URLs.")
        p_download.add_argument("-u", "--urls", nargs='+',
                                help="List of URLs to download.")
        p_download.add_argument(
            "-d", "--dest", default="manual_downloads",
            help="Destination folder name."
        )
        p_download.add_argument(
            "-s", "--start-index", type=int, default=1000,
            help="Starting index for image filenames (default: 1000)."
        )

        # Команда find-duplicates
        p_find = subparsers.add_parser(
            "find-duplicates", help="Find and rename duplicate images."
        )
        p_find.add_argument("directory", type=Path,
                            help="Directory to process.")

        # Команда uniquify
        p_uniq = subparsers.add_parser(
            "uniquify", help="Find and modify duplicate images to make them unique."
        )
        p_uniq.add_argument("directory", type=Path,
                            help="Directory to process.")

        # Команда uniquify-all
        p_uniq_all = subparsers.add_parser(
            "uniquify-all", help="Uniquify all images in directory."
        )
        p_uniq_all.add_argument("directory", type=Path,
                                help="Directory to process.")

        args = parser.parse_args()

        main_coro = None
        if args.command == "download":
            if args.file:
                main_coro = download_images_from_file(
                    args.file, args.start_index
                )
            elif args.urls:
                main_coro = download_images_for_folder(
                    args.dest, args.urls, args.start_index
                )
        elif args.command == "find-duplicates":
            main_coro = handle_duplicates(args.directory)
        elif args.command == "uniquify":
            main_coro = uniquify_duplicates(args.directory)
        elif args.command == "uniquify-all":
            main_coro = uniquify_all_images(args.directory)

        if main_coro:
            start_time = datetime.now()
            asyncio.run(main_coro)
            end_time = datetime.now()
            logger.info(
                f'Время выполнения программы: {end_time - start_time}.')

    else:
        # ----- ИНТЕРАКТИВНЫЙ РЕЖИМ (ДЛЯ ЧЕЛОВЕКА) -----
        logger.info("Запуск в интерактивном режиме...")
        start_time = datetime.now()
        asyncio.run(run_interactive_mode())
        end_time = datetime.now()
        logger.info(f'Время выполнения программы: {end_time - start_time}.')
