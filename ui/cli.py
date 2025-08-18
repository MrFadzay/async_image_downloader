"""
Интерактивный CLI интерфейс для async image downloader.
"""
import re
from pathlib import Path

import questionary

from core.downloader import download_images_for_folder, download_images_from_file
from core.duplicates import handle_duplicates, uniquify_all_images, uniquify_duplicates
from utils.logger import logger


def _clean_path_string(path_str: str) -> str:
    """
    Очищает строку пути от лишних символов.

    Args:
        path_str: Исходная строка пути

    Returns:
        Очищенная строка пути
    """
    # Удаляем лишние пробелы в начале и конце пути
    path_str = path_str.strip()
    # Удаляем кавычки и амперсанды, которые могут вызвать проблемы
    if path_str.startswith(("'", '"', '&')):
        path_str = path_str.lstrip("'\"& ")
    if path_str.endswith(("'", '"')):
        path_str = path_str.rstrip("'\"")
    return path_str


async def _handle_download_from_file():
    """Обрабатывает скачивание изображений из файла."""
    file_path_str = await questionary.path(
        "Укажите путь к файлу с URL:"
    ).ask_async()

    if file_path_str:
        file_path_str = _clean_path_string(file_path_str)
        start_index_str = await questionary.text(
            "Введите начальный индекс для изображений (по умолчанию 1000):",
            default="1000"
        ).ask_async()
        start_index = int(
            start_index_str) if start_index_str.isdigit() else 1000

        delay_str = await questionary.text(
            "Введите задержку между запросами в секундах "
            "(по умолчанию 0, рекомендуется 1-3 для Авито):",
            default="0",
        ).ask_async()
        try:
            delay = float(delay_str) if delay_str else 0
        except ValueError:
            delay = 0

        browser_mode = await questionary.confirm(
            "Использовать браузерный режим? "
            "(медленнее, но обходит блокировки Avito и подобных сайтов)",
            default=False,
        ).ask_async()

        try:
            # Проверяем существование файла перед обработкой
            path_obj = Path(file_path_str)
            if not path_obj.exists():
                logger.error(f"Файл '{file_path_str}' не существует.")
                return
            await download_images_from_file(
                path_obj, start_index, delay, browser_mode
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке пути '{file_path_str}': {e}")


async def _handle_download_from_urls():
    """Обрабатывает скачивание изображений по списку URL."""
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
    start_index = int(start_index_str) if start_index_str.isdigit() else 1000

    delay_str = await questionary.text(
        "Введите задержку между запросами в секундах "
        "(по умолчанию 0, рекомендуется 1-3 для Авито):",
        default="0",
    ).ask_async()
    try:
        delay = float(delay_str) if delay_str else 0
    except ValueError:
        delay = 0

    browser_mode = await questionary.confirm(
        "Использовать браузерный режим? "
        "(медленнее, но обходит блокировки Avito и подобных сайтов)",
        default=False,
    ).ask_async()

    if urls_str and dest_folder:
        urls = [url for url in re.split(r'[\s;]+', urls_str.strip()) if url]
        await download_images_for_folder(
            dest_folder, urls, start_index, delay, browser_mode
        )


async def _handle_download_menu():
    """Обрабатывает меню скачивания изображений."""
    download_type = await questionary.select(
        "Откуда скачивать?",
        choices=["Из файла", "По списку URL"]
    ).ask_async()

    if download_type == "Из файла":
        await _handle_download_from_file()
    elif download_type == "По списку URL":
        await _handle_download_from_urls()


async def _handle_duplicates_menu():
    """Обрабатывает меню работы с дубликатами."""
    duplicate_action = await questionary.select(
        "Выберите действие с дубликатами:",
        choices=[
            "Найти и переименовать дубликаты",
            "Уникализировать дубликаты",
            "Назад"
        ]
    ).ask_async()

    if duplicate_action == "Найти и переименовать дубликаты":
        await _handle_find_and_rename_duplicates()
    elif duplicate_action == "Уникализировать дубликаты":
        await _handle_uniquify_duplicates()


async def _handle_find_and_rename_duplicates():
    """Обрабатывает поиск и переименование дубликатов."""
    dir_path_str = await questionary.path(
        "Укажите путь к директории для проверки:"
    ).ask_async()

    if dir_path_str:
        dir_path_str = _clean_path_string(dir_path_str)
        logger.info(f"Обрабатываем путь: '{dir_path_str}'")

        try:
            path_obj = Path(dir_path_str)
            if not path_obj.exists():
                logger.error(f"Директория '{dir_path_str}' не существует.")
                return
            await handle_duplicates(path_obj)
        except Exception as e:
            logger.error(f"Ошибка при обработке пути '{dir_path_str}': {e}")


async def _handle_uniquify_duplicates():
    """Обрабатывает уникализацию дубликатов."""
    dir_path_str = await questionary.path(
        "Укажите путь к директории для уникализации дубликатов:"
    ).ask_async()

    if dir_path_str:
        dir_path_str = _clean_path_string(dir_path_str)
        logger.info(f"Обрабатываем путь: '{dir_path_str}'")

        try:
            path_obj = Path(dir_path_str)
            if not path_obj.exists():
                logger.error(f"Директория '{dir_path_str}' не существует.")
                return
            await uniquify_duplicates(path_obj)
        except Exception as e:
            logger.error(f"Ошибка при обработке пути '{dir_path_str}': {e}")


async def _handle_uniquify_all():
    """Обрабатывает уникализацию всех изображений."""
    dir_path_str = await questionary.path(
        "Укажите путь к директории для уникализации всех изображений:"
    ).ask_async()

    if dir_path_str:
        dir_path_str = _clean_path_string(dir_path_str)
        logger.info(f"Обрабатываем путь: '{dir_path_str}'")

        try:
            path_obj = Path(dir_path_str)
            if not path_obj.exists():
                logger.error(f"Директория '{dir_path_str}' не существует.")
                return
            await uniquify_all_images(path_obj)
        except Exception as e:
            logger.error(f"Ошибка при обработке пути '{dir_path_str}': {e}")


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
            await _handle_download_menu()
        elif command == "Работа с дубликатами":
            await _handle_duplicates_menu()
        elif command == "Уникализация":
            await _handle_uniquify_all()
        elif command == "Выход" or command is None:
            logger.info("Завершение работы.")
            break
