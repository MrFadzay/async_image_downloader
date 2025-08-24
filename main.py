"""
Async Image Downloader - инструмент для быстрого скачивания изображений.

Поддерживает:
- Скачивание изображений по списку URL
- Поиск и обработку дубликатов
- Уникализацию изображений
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Coroutine, Any

# --- Настройка для PyInstaller ---
if getattr(sys, 'frozen', False):
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from core.downloader import (
    run_download_session, 
    run_download_session_with_pause
)
from core.duplicates import (
    handle_duplicates,
    uniquify_all_images,
    uniquify_duplicates,
)
from ui.cli import run_interactive_mode
from utils.logger import logger
from utils.config_manager import (
    load_or_create_config, 
    ConfigManager
)
from utils.config_profiles import ConfigProfiles

# Глобальный флаг для пропуска подтверждений
_SKIP_CONFIRMATIONS = False


def set_skip_confirmations(skip: bool) -> None:
    """Устанавливает глобальный флаг пропуска подтверждений."""
    global _SKIP_CONFIRMATIONS
    _SKIP_CONFIRMATIONS = skip


def get_skip_confirmations() -> bool:
    """Возвращает текущее состояние флага пропуска подтверждений."""
    return _SKIP_CONFIRMATIONS


async def _handle_duplicates_with_confirm(
    directory: Path, skip_confirm: bool
) -> None:
    """Обработчик поиска дубликатов с учетом флага подтверждения."""
    set_skip_confirmations(skip_confirm)
    await handle_duplicates(directory)


async def _handle_uniquify_duplicates_with_confirm(
    directory: Path, skip_confirm: bool
) -> None:
    """Обработчик уникализации дубликатов с учетом флага подтверждения."""
    set_skip_confirmations(skip_confirm)
    await uniquify_duplicates(directory)


async def _handle_uniquify_all_with_confirm(
    directory: Path, skip_confirm: bool
) -> None:
    """Обработчик уникализации всех изображений с учетом флага подтверждения."""
    set_skip_confirmations(skip_confirm)
    await uniquify_all_images(directory)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Создает и настраивает парсер аргументов командной строки.
    
    Определяет команды download, find-duplicates, uniquify и uniquify-all
    с соответствующими параметрами для автоматизации работы.
    
    Returns:
        argparse.ArgumentParser: Настроенный парсер аргументов
    """
    parser = argparse.ArgumentParser(
        description="Async Image Downloader and Processor."
    )
    
    # Глобальные аргументы
    parser.add_argument(
        "--profile", 
        choices=["fast", "seo", "safe", "bulk"],
        help="Использовать предопределенный профиль конфигурации"
    )
    parser.add_argument(
        "--save-profile", 
        metavar="PROFILE",
        choices=["fast", "seo", "safe", "bulk"],
        help="Сохранить профиль как config.yaml и выйти"
    )
    parser.add_argument(
        "--list-profiles", 
        action="store_true",
        help="Показать список доступных профилей"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=False)

    # --- Команда download ---
    p_download = subparsers.add_parser(
        "download",
        help="Скачать изображения по списку URL."
    )
    p_download.add_argument(
        "urls",
        nargs='+',
        help=(
            "Список URL для скачивания, разделенных пробелами."
        ),
    )
    p_download.add_argument(
        "-s",
        "--start-index",
        type=int,
        default=1000,
        help="Начальный индекс для именования файлов (по умолчанию: 1000).",
    )
    p_download.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Количество повторных попыток при ошибках (по умолчанию: 3).",
    )
    p_download.add_argument(
        "--enable-pause-resume",
        action="store_true",
        help="Включить поддержку паузы/возобновления (пауза по Ctrl+C).",
    )

    p_find = subparsers.add_parser(
        "find-duplicates",
        help="Find and rename duplicate images."
    )
    p_find.add_argument("directory", type=Path, help="Directory to process.")
    p_find.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Автоматически подтвердить все вопросы (без интерактивных диалогов)."
    )

    p_uniq = subparsers.add_parser(
        "uniquify",
        help=(
            "Find and modify duplicate images to make them unique."
        ),
    )
    p_uniq.add_argument("directory", type=Path, help="Directory to process.")
    p_uniq.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Автоматически подтвердить все вопросы (без интерактивных диалогов)."
    )

    p_uniq_all = subparsers.add_parser(
        "uniquify-all", help="Uniquify all images in directory."
    )
    p_uniq_all.add_argument(
        "directory",
        type=Path,
        help="Directory to process."
    )
    p_uniq_all.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Автоматически подтвердить все вопросы (без интерактивных диалогов)."
    )

    return parser


def handle_cli_command(
    args: argparse.Namespace
) -> Optional[Coroutine[Any, Any, None]]:
    """
    Обрабатывает команды CLI режима и возвращает соответствующую корутину.
    
    Маршрутизирует запросы на соответствующие функции основных модулей
    на основе выбранной команды и переданных параметров.
    
    Args:
        args: Объект с параметрами командной строки от argparse
        
    Returns:
        Coroutine или None: Корутина для выполнения или 
            None для неизвестных команд
    """
    if args.command == "download":
        if hasattr(args, 'enable_pause_resume') and args.enable_pause_resume:
            return run_download_session_with_pause(
                urls=args.urls,
                start_index=args.start_index,
                retries=args.retries,
                enable_pause_resume=True
            )
        else:
            return run_download_session(
                urls=args.urls,
                start_index=args.start_index,
                retries=args.retries
            )
    elif args.command == "find-duplicates":
        # Устанавливаем флаг пропуска подтверждения
        skip_confirm = getattr(args, 'yes', False)
        return _handle_duplicates_with_confirm(args.directory, skip_confirm)
    elif args.command == "uniquify":
        skip_confirm = getattr(args, 'yes', False)
        return _handle_uniquify_duplicates_with_confirm(
            args.directory, skip_confirm
        )
    elif args.command == "uniquify-all":
        skip_confirm = getattr(args, 'yes', False)
        return _handle_uniquify_all_with_confirm(args.directory, skip_confirm)

    return None


def main() -> None:
    """
    Главная функция приложения, определяющая режим работы.
    
    Автоматически выбирает между CLI режимом (при наличии аргументов)
    и интерактивным режимом (без аргументов). Отслеживает время выполнения.
    """
    # Парсим аргументы для проверки глобальных опций
    parser = create_argument_parser()
    
    # Если нет аргументов, запускаем интерактивный режим
    if len(sys.argv) == 1:
        # Загружаем конфигурацию приложения
        config = load_or_create_config()
        logger.info(f"Используется конфигурация версии {config.version}")
        
        # ----- ИНТЕРАКТИВНЫЙ РЕЖИМ (ДЛЯ ЧЕЛОВЕКА) -----
        logger.info("Запуск в интерактивном режиме...")
        start_time = datetime.now()
        asyncio.run(run_interactive_mode())
        end_time = datetime.now()
        logger.info(f'Время выполнения программы: {end_time - start_time}.')
        return
    
    args = parser.parse_args()
    
    # Обрабатываем глобальные опции
    if args.list_profiles:
        ConfigProfiles.list_profiles()
        return
        
    if args.save_profile:
        output_file = Path(f"config-{args.save_profile}.yaml")
        success = ConfigProfiles.save_profile_as_config(
            args.save_profile, output_file
        )
        if success:
            print(f"✅ Профиль '{args.save_profile}' сохранен в {output_file}")
            print(
                "💡 Переименуйте в 'config.yaml' для использования по умолчанию"
            )
        else:
            print(f"❌ Ошибка при сохранении профиля '{args.save_profile}'")
        return
    
    # Загружаем конфигурацию (профиль или обычную)
    if args.profile:
        logger.info(f"Загружается профиль: {args.profile}")
        try:
            config = ConfigProfiles.create_profile(args.profile)
            # Временно устанавливаем профильную конфигурацию
            config_manager = ConfigManager()
            config_manager.config = config
            logger.info(
                f"Используется профиль '{args.profile}' "
                f"(версия {config.version})"
            )
        except ValueError as e:
            logger.error(f"Ошибка профиля: {e}")
            return
    else:
        config = load_or_create_config()
        logger.info(f"Используется конфигурация версии {config.version}")
    
    # Обрабатываем команды
    if not args.command:
        logger.error("Не указана команда. Используйте --help для справки.")
        return
        
    main_coro = handle_cli_command(args)
    if main_coro:
        start_time = datetime.now()
        asyncio.run(main_coro)
        end_time = datetime.now()
        logger.info(f'Время выполнения программы: {end_time - start_time}.')


if __name__ == '__main__':
    main()
