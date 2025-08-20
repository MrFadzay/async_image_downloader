"""
Интерактивный CLI интерфейс для async image downloader.
"""
import re
from pathlib import Path
from typing import Any, Callable, Coroutine
from urllib.parse import urlparse

import questionary

from core.downloader import run_download_session
from core.duplicates import (
    handle_duplicates,
    uniquify_all_images,
    uniquify_duplicates,
)
from utils.logger import logger


def _clean_path_string(path_str: str) -> str:
    """
    Очищает строку пути от лишних символов.
    """
    return path_str.strip().strip('"\'')


def _validate_url(url: str) -> bool:
    """
    Проверяет корректность URL. Не требует наличия расширения изображения
    или известного хоста, так как проверка типа контента выполняется
    позже при скачивании.
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)

    except Exception:
        return False


async def _handle_new_download_session():
    """Обрабатывает скачивание изображений, запрашивая URL."""
    urls_str = await questionary.text(
        "Вставьте URL-адреса, разделенные пробелом:",
        validate=lambda text: True if len(
            text) > 0 else "Пожалуйста, введите хотя бы один URL."
    ).ask_async()

    if urls_str is None:
        logger.warning("Операция отменена.")
        return

    urls = []
    skipped_urls = []
    for url_candidate in re.split(r'[\s;,|]+', urls_str.strip()):
        if not url_candidate:
            continue

        url_candidate = url_candidate.strip()
        if _validate_url(url_candidate):
            urls.append(url_candidate)
        else:
            skipped_urls.append(url_candidate)
            logger.warning(f"Пропущен некорректный URL: '{url_candidate}'")

    if not urls:
        logger.warning("Не найдено корректных URL или все URL некорректны.")
        return

    total_urls = len(urls)
    logger.info(
        f"Найдено корректных URL: {total_urls}"
    )

    if skipped_urls:
        logger.warning(
            "Пропущено некорректных URL: %d\nПримеры: %s",
            len(skipped_urls),
            ", ".join(skipped_urls[:3])
        )
        confirm_continue = await questionary.confirm(
            "Продолжить с найденными URL?",
            default=True
        ).ask_async()
        if not confirm_continue:
            logger.info("Операция отменена.")
            return

    def validate_number(text: str, min_val: int, max_val: int) -> bool:
        """Проверяет, что введенное значение - число в заданном диапазоне."""
        if not text.isdigit():
            return False
        val = int(text)
        return min_val <= val <= max_val

    start_index_str = await questionary.text(
        "Введите начальный индекс для изображений (1-9999):",
        default="1000",
        validate=lambda text: validate_number(text, 1, 9999)
    ).ask_async()
    if start_index_str is None:
        logger.warning("Операция отменена.")
        return
    start_index = int(start_index_str)

    retries_str = await questionary.text(
        "Введите количество повторных попыток (1-10):",
        default="3",
        validate=lambda text: validate_number(text, 1, 10)
    ).ask_async()
    if retries_str is None:
        logger.warning("Операция отменена.")
        return
    retries = int(retries_str)

    logger.info("\nСводка параметров скачивания:")
    logger.info(f"* Количество URL: {total_urls}")
    logger.info(f"* Начальный индекс: {start_index}")
    logger.info(f"* Количество попыток: {retries}")

    confirm_download = await questionary.confirm(
        "Начать скачивание?",
        default=True
    ).ask_async()
    if confirm_download:
        await run_download_session(
            urls=urls,
            start_index=start_index,
            retries=retries
        )
    else:
        logger.info("Скачивание отменено пользователем.")


async def _process_directory_action(
    prompt_message: str,
    action_function: Callable[[Path], Coroutine[Any, Any, None]],
):
    """
    Универсальный обработчик для действий с директориями.
    Запрашивает путь, проверяет его и выполняет переданное действие.
    """
    dir_path_str = await questionary.path(prompt_message).ask_async()

    if dir_path_str:
        dir_path_str = _clean_path_string(dir_path_str)
        try:
            path_obj = Path(dir_path_str)
            if not path_obj.exists():
                logger.error(f"Директория '{dir_path_str}' не существует.")
                return
            await action_function(path_obj)
        except Exception as e:
            logger.error(f"Ошибка при обработке пути '{dir_path_str}': {e}")


async def _handle_duplicates_menu():
    """Обрабатывает меню работы с дубликатами."""
    action = await questionary.select(
        "Выберите действие с дубликатами:",
        choices=[
            "Найти и переименовать дубликаты",
            "Уникализировать дубликаты",
            "Назад"
        ]
    ).ask_async()

    if action == "Найти и переименовать дубликаты":
        await _process_directory_action(
            "Укажите путь к директории для проверки:",
            handle_duplicates
        )
    elif action == "Уникализировать дубликаты":
        await _process_directory_action(
            "Укажите путь к директории для уникализации дубликатов:",
            uniquify_duplicates
        )


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
            await _handle_new_download_session()
        elif command == "Работа с дубликатами":
            await _handle_duplicates_menu()
        elif command == "Уникализация":
            await _process_directory_action(
                "Укажите путь к директории для уникализации всех изображений:",
                uniquify_all_images
            )
        elif command == "Выход" or command is None:
            logger.info("Завершение работы.")
            break
