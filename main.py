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

# --- Настройка для PyInstaller ---
if getattr(sys, 'frozen', False):
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from core.downloader import run_download_session
from core.duplicates import (
    handle_duplicates,
    uniquify_all_images,
    uniquify_duplicates,
)
from ui.cli import run_interactive_mode
from utils.logger import logger


def create_argument_parser():
    """Создает и настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Async Image Downloader and Processor."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    p_find = subparsers.add_parser(
        "find-duplicates",
        help="Find and rename duplicate images."
    )
    p_find.add_argument("directory", type=Path, help="Directory to process.")

    p_uniq = subparsers.add_parser(
        "uniquify",
        help=(
            "Find and modify duplicate images to make them unique."
        ),
    )
    p_uniq.add_argument("directory", type=Path, help="Directory to process.")

    p_uniq_all = subparsers.add_parser(
        "uniquify-all", help="Uniquify all images in directory."
    )
    p_uniq_all.add_argument(
        "directory",
        type=Path,
        help="Directory to process."
    )

    return parser


def handle_cli_command(args):
    """
    Обрабатывает команды CLI режима.
    """
    if args.command == "download":
        return run_download_session(
            urls=args.urls,
            start_index=args.start_index,
            retries=args.retries
        )
    elif args.command == "find-duplicates":
        return handle_duplicates(args.directory)
    elif args.command == "uniquify":
        return uniquify_duplicates(args.directory)
    elif args.command == "uniquify-all":
        return uniquify_all_images(args.directory)

    return None


def main():
    """Главная функция приложения."""
    if len(sys.argv) > 1:
        # ----- РЕЖИМ С АРГУМЕНТАМИ (ДЛЯ АВТОМАТИЗАЦИИ) -----
        parser = create_argument_parser()
        args = parser.parse_args()
        main_coro = handle_cli_command(args)

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


if __name__ == '__main__':
    main()
