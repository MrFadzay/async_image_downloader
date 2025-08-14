"""
Главный файл async image downloader - точка входа для CLI и интерактивного режима.
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from utils.logger import logger
from core.downloader import download_images_from_file, download_images_for_folder
from core.duplicates import handle_duplicates, uniquify_duplicates, uniquify_all_images
from ui.cli import run_interactive_mode
from ui.gui import run_gui


def create_argument_parser():
    """Создает и настраивает парсер аргументов командной строки."""
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
        "-d", "--dest", default="manual_downloads", help="Destination folder name.")
    p_download.add_argument("-s", "--start-index", type=int, default=1000,
                            help="Starting index for image filenames (default: 1000).")

    # Команда find-duplicates
    p_find = subparsers.add_parser(
        "find-duplicates", help="Find and rename duplicate images.")
    p_find.add_argument("directory", type=Path, help="Directory to process.")

    # Команда uniquify
    p_uniq = subparsers.add_parser(
        "uniquify", help="Find and modify duplicate images to make them unique.")
    p_uniq.add_argument("directory", type=Path, help="Directory to process.")

    # Команда uniquify-all
    p_uniq_all = subparsers.add_parser(
        "uniquify-all", help="Uniquify all images in directory.")
    p_uniq_all.add_argument("directory", type=Path,
                            help="Directory to process.")

    # Команда gui
    p_gui = subparsers.add_parser(
        "gui", help="Launch graphical user interface.")

    return parser


def handle_cli_command(args):
    """
    Обрабатывает команды CLI режима.

    Args:
        args: Аргументы командной строки

    Returns:
        Корутина для выполнения или None
    """
    if args.command == "download":
        if args.file:
            return download_images_from_file(args.file, args.start_index)
        elif args.urls:
            return download_images_for_folder(args.dest, args.urls, args.start_index)
    elif args.command == "find-duplicates":
        return handle_duplicates(args.directory)
    elif args.command == "uniquify":
        return uniquify_duplicates(args.directory)
    elif args.command == "uniquify-all":
        return uniquify_all_images(args.directory)
    elif args.command == "gui":
        # GUI запускается синхронно, не возвращаем корутину
        run_gui()
        return None

    return None


def main():
    """Главная функция приложения."""
    # Проверяем, были ли переданы аргументы командной строки
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
