"""
Интерактивный CLI интерфейс для async image downloader.
"""
import re
from pathlib import Path
from typing import Any, Callable, Coroutine

import questionary

from core.downloader import run_download_session, run_download_session_with_pause
from core.duplicates import (
    handle_duplicates,
    uniquify_all_images,
    uniquify_duplicates,
)
from utils.logger import logger
from utils.validation import validate_download_request
from utils.user_guidance import UserGuidance, show_context_sensitive_help
from utils.error_handling import get_error_handler


def _clean_path_string(path_str: str) -> str:
    """
    Очищает строку пути от лишних символов и кавычек.
    
    Удаляет пробелы, кавычки и служебные символы, которые могут появляться
    при копировании путей из проводника или терминала.
    
    Args:
        path_str: Необработанная строка пути
        
    Returns:
        str: Очищенная строка пути
    """
    # Удаляем начальные '& ' и конечные кавычки, которые могут быть добавлены
    cleaned_path = path_str.strip()
    if cleaned_path.startswith("& '") and \
       cleaned_path.endswith("'"):
        cleaned_path = cleaned_path[3:-1]
    # Удаляем любые оставшиеся начальные/конечные кавычки
    return cleaned_path.strip().strip('"\'')


def _validate_url(url: str) -> bool:
    """
    Проверяет корректность и безопасность URL перед скачиванием.
    
    Использует комплексную валидацию включая проверку схемы, безопасности
    и соответствия поддерживаемым форматам.
    
    Args:
        url: URL для проверки
        
    Returns:
        bool: True если URL корректен и безопасен, False иначе
    """
    return validate_download_request(url)


async def _handle_new_download_session() -> None:
    """
    Обрабатывает интерактивную сессию скачивания изображений.
    
    Запрашивает у пользователя URL-адреса, параметры скачивания,
    выполняет валидацию и запускает процесс скачивания.
    Поддерживает ввод нескольких URL через различные разделители.
    """
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
        print("
🔍 Помощь по вводу URL:")
        print("   ✅ Правильные URL: https://example.com/image.jpg")
        print("   ✅ Поддерживаемые протоколы: https://, http://")
        print("   ❌ Недопустимые: file://, ftp://, локальные IP")
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

    # Спрашиваем о включении паузы/возобновления
    enable_pause_resume = await questionary.confirm(
        "Включить поддержку паузы/возобновления? (Пауза по Ctrl+C)",
        default=True
    ).ask_async()
    
    if enable_pause_resume is None:
        logger.warning("Операция отменена.")
        return

    logger.info("\nСводка параметров скачивания:")
    logger.info(f"* Количество URL: {total_urls}")
    logger.info(f"* Начальный индекс: {start_index}")
    logger.info(f"* Количество попыток: {retries}")
    logger.info(f"* Пауза/возобновление: {'Да' if enable_pause_resume else 'Нет'}")

    logger.info("\nНачинаю скачивание...")
    
    if enable_pause_resume:
        await run_download_session_with_pause(
            urls=urls,
            start_index=start_index,
            retries=retries,
            enable_pause_resume=True
        )
    else:
        await run_download_session(
            urls=urls,
            start_index=start_index,
            retries=retries
        )


async def _process_directory_action(
    prompt_message: str,
    action_function: Callable[[Path], Coroutine[Any, Any, None]],
) -> None:
    """
    Универсальный обработчик для действий с директориями.
    Запрашивает путь, проверяет его и выполняет переданное действие.
    """
    print(f"
📁 {prompt_message}")
    print("📝 Полезные советы:")
    print("   • Можно ввести как абсолютный, так и относительный путь")
    print("   • Поддерживаются пути с кириллицей и пробелами")
    print("   • Пример: ./images или C:/Users/Name/Pictures")
    
    dir_path_str = await questionary.path(prompt_message).ask_async()

    if dir_path_str:
        dir_path_str = _clean_path_string(dir_path_str)
        try:
            path_obj = Path(dir_path_str)
            if not path_obj.exists():
                print(f"
❌ Ошибка: Директория '{dir_path_str}' не существует")
                print("📝 Помощь:")
                print("   • Проверьте правописание пути")
                print("   • Убедитесь, что директория создана")
                print("   • Попробуйте использовать абсолютный путь")
                return
                
            if not path_obj.is_dir():
                print(f"
❌ Ошибка: '{dir_path_str}' не является директорией")
                print("📝 Помощь: Укажите путь к папке, а не к файлу")
                return
            
            # Показываем информацию о директории
            try:
                files = list(path_obj.glob("*"))
                image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']]
                print(f"
📊 Информация о директории:")
                print(f"   📁 Путь: {path_obj.absolute()}")
                print(f"   📄 Всего файлов: {len(files)}")
                print(f"   🖼️ Изображений: {len(image_files)}")
                
                if len(image_files) == 0:
                    UserGuidance.show_help_for_issue("no_images_found")
                    return
            except PermissionError:
                print(f"
⚠️ Предупреждение: Нет прав для чтения директории")
                UserGuidance.show_help_for_issue("permission_denied")
                return
            
            await action_function(path_obj)
        except Exception as e:
            error_handler = get_error_handler()
            error_handler.handle_file_error(e, Path(dir_path_str), "directory_processing")
    else:
        print("❌ Операция отменена")


async def _handle_duplicates_menu() -> None:
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


async def run_interactive_mode() -> None:
    """
    Запускает интерактивный режим работы с меню выбора действий.
    
    Предоставляет пользователю возможность выбрать между скачиванием изображений,
    обработкой дубликатов и уникализацией изображений.
    Циклически отображает меню до выбора пользователем опции «Выход».
    """
    # Показываем приветствие для новых пользователей
    UserGuidance.show_welcome_message()
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
            UserGuidance.show_operation_tips("download")
            await _handle_new_download_session()
        elif command == "Работа с дубликатами":
            UserGuidance.show_operation_tips("find_duplicates")
            await _handle_duplicates_menu()
        elif command == "Уникализация":
            UserGuidance.show_operation_tips("uniquify_all")
            UserGuidance.show_safety_warning("uniquify_all")
            await _process_directory_action(
                "Укажите путь к директории для уникализации всех изображений:",
                uniquify_all_images
            )
        elif command == "Выход" or command is None:
            logger.info("Завершение работы.")
            break
