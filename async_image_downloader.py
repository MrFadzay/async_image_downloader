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
        new_filename = f"{file_index}.jpeg"
        full_path = target_dir / new_filename

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


def _calculate_perceptual_hash_sync(filepath: Path) -> str | None:
    """Синхронная функция для вычисления перцептивного хеша."""
    try:
        image = Image.open(filepath)
        # Используем phash, так как он более устойчив к мелким изменениям,
        # что делает его хорошим кандидатом для проверки дубликатов.
        return str(imagehash.phash(image))
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


async def _get_file_hashes(directory: Path) -> tuple[dict[str, Path], list[tuple[Path, str, Path]]]:
    """Асинхронно вычисляет перцептивные хеши для всех файлов в директории."""
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

    perceptual_hashes: dict[str, Path] = {}
    duplicates = []
    for path, p_hash in zip(filepaths_to_process, hashes_results):
        if not p_hash:
            continue
        if p_hash in perceptual_hashes:
            duplicates.append((path, p_hash, perceptual_hashes[p_hash]))
        else:
            perceptual_hashes[p_hash] = path

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

                modification_func = random.choice(modification_functions)
                logger.info(
                    f"  -> Попытка {attempt + 1}/{MAX_UNIQUIFY_ATTEMPTS}: "
                    f"применяем '{modification_func.__name__}'..."
                )

                modified_image = modification_func(image)

                modified_image.save(full_path, format="JPEG")

                new_p_hash = await loop.run_in_executor(
                    None, _calculate_perceptual_hash_sync, full_path
                )

                if new_p_hash and new_p_hash not in perceptual_hashes:
                    perceptual_hashes[new_p_hash] = full_path
                    uniquified_count += 1
                    logger.info(
                        f"  УСПЕХ: Изображение '{full_path}' "
                        f"успешно уникализировано."
                    )
                    is_uniquified = True
                    break
                else:
                    logger.info(
                        f"  НЕУДАЧА: Новый хеш ({new_p_hash}) все еще "
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
                f"ПРЕДУПРЕЖДЕНИЕ: Не удалось уникализировать'{full_path}' "
                f"после {MAX_UNIQUIFY_ATTEMPTS} попыток."
            )

    logger.info(f"\nЗавершено. Уникализировано {uniquified_count} дубликатов.")


async def handle_duplicates(directory: Path) -> None:
    logger.info(f"Поиск дубликатов в '{directory}'...")
    deleted_count = 0

    await create_dir(directory)

    _unique_hashes, duplicates_info = await _get_file_hashes(directory)

    for full_path, p_hash, original_path in duplicates_info:
        logger.info(
            f"Найден дубликат: '{full_path}' (оригинал: '{original_path}')")

        stem = full_path.stem
        suffix = full_path.suffix
        duplicate_count = 1
        new_full_path = full_path.with_name(
            f"{stem}_duplicate_{duplicate_count}{suffix}"
        )

        while await aiofiles.os.path.exists(new_full_path):
            duplicate_count += 1
            new_full_path = full_path.with_name(
                f"{stem}_duplicate_{duplicate_count}{suffix}"
            )

        await aiofiles.os.rename(full_path, new_full_path)
        deleted_count += 1
        logger.info(f"  -> Переименован в: '{new_full_path}'")

    logger.info(f"Обработано {deleted_count} дубликатов (переименовано).")


async def download_images_for_folder(folder_name: str, urls: list[str], start_index: int = 1):
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


async def download_images_from_file(file_path: Path) -> None:
    await create_dir(IMAGE_DIR)

    try:
        async with aiofiles.open(file_path, mode='r') as f:
            async for line in f:
                parts = re.split(r'[\s,;]+', line.strip())
                if not parts:
                    continue

                folder_name = parts[0]
                urls_in_line = [
                    url.strip() for url in parts[1:] if url.strip()
                ]
                if urls_in_line:
                    await download_images_for_folder(folder_name, urls_in_line)
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
                "Найти и переименовать дубликаты",
                "Уникализировать дубликаты",
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
                    await download_images_from_file(Path(file_path_str))

            elif download_type == "По списку URL":
                urls_str = await questionary.text(
                    "Введите URL через пробел или точку с запятой:"
                ).ask_async()
                dest_folder = await questionary.text(
                    "Введите имя папки для сохранения:",
                    default="manual_downloads"
                ).ask_async()
                if urls_str and dest_folder:
                    urls = [url for url in re.split(r'[\s;]+', urls_str.strip()) if url]
                    await download_images_for_folder(dest_folder, urls)

        elif command == "Найти и переименовать дубликаты":
            dir_path_str = await questionary.path(
                "Укажите путь к директории для проверки:"
            ).ask_async()
            if dir_path_str:
                await handle_duplicates(Path(dir_path_str))

        elif command == "Уникализировать дубликаты":
            dir_path_str = await questionary.path(
                "Укажите путь к директории для уникализации:"
            ).ask_async()
            if dir_path_str:
                await uniquify_duplicates(Path(dir_path_str))

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

        args = parser.parse_args()

        main_coro = None
        if args.command == "download":
            if args.file:
                main_coro = download_images_from_file(args.file)
            elif args.urls:
                main_coro = download_images_for_folder(args.dest, args.urls)
        elif args.command == "find-duplicates":
            main_coro = handle_duplicates(args.directory)
        elif args.command == "uniquify":
            main_coro = uniquify_duplicates(args.directory)

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
