"""
Модуль для скачивания изображений через браузер (Playwright).
Используется для сайтов с защитой от ботов, таких как Avito.
"""
import asyncio
import random
from pathlib import Path
from typing import List, Optional

import aiofiles

# Опциональный импорт Playwright
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None

from utils.config import (
    BROWSER_DEFAULT_DELAY,
    BROWSER_SEMAPHORE_LIMIT,
    DOWNLOAD_TIMEOUT,
)
from utils.logger import logger
from core.image_utils import process_and_save_image_sync

# Семафор для ограничения одновременных браузерных соединений
browser_semaphore = asyncio.Semaphore(BROWSER_SEMAPHORE_LIMIT)

# Глобальные переменные для переиспользования браузера
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None


async def install_browser():
    """Автоматически устанавливает браузер Chromium."""
    import subprocess
    import sys

    logger.info("Устанавливаю браузер для защищенных сайтов...")
    logger.info("Это займет ~2-3 минуты и скачает ~150MB")

    try:
        # Запускаем установку браузера
        import shutil
        playwright_path = shutil.which("playwright")
        if not playwright_path:
            # Пробуем через python -m
            process = subprocess.run([
                sys.executable, "-m", "playwright", "install", "chromium"
            ], capture_output=True, text=True, timeout=300)
        else:
            # Используем прямой путь к playwright
            process = subprocess.run([
                playwright_path, "install", "chromium"
            ], capture_output=True, text=True, timeout=300)

        if process.returncode == 0:
            logger.info("Браузер успешно установлен!")
            return True
        else:
            logger.error(f"Ошибка установки браузера: {process.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Превышено время ожидания установки браузера")
        return False
    except Exception as e:
        logger.error(f"Ошибка при установке браузера: {e}")
        return False


async def get_browser_context():
    """Получает или создает браузерный контекст."""
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright не установлен")
    
    global _browser, _context

    if _browser is None or _context is None:
        try:
            playwright = await async_playwright().start()
            _browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            _context = await _browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            )
        except Exception as e:
            if ("Executable doesn't exist" in str(e) or
                    "Browser is not installed" in str(e)):
                # Браузер не установлен, предлагаем автоустановку
                logger.warning("Браузер для защищенных сайтов не найден")

                # В интерактивном режиме спрашиваем пользователя
                try:
                    import questionary
                    install_browser_choice = await questionary.confirm(
                        "Установить браузер автоматически? "
                        "(нужен для Авито и подобных сайтов)"
                    ).ask_async()

                    if install_browser_choice:
                        success = await install_browser()
                        if success:
                            # Повторная попытка запуска после установки
                            playwright = await async_playwright().start()
                            _browser = await playwright.chromium.launch(
                                headless=True,
                                args=[
                                    '--no-sandbox',
                                    '--disable-blink-features=AutomationControlled',
                                    '--disable-web-security',
                                    '--disable-features=VizDisplayCompositor'
                                ]
                            )
                            _context = await _browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent=(
                                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                                    'Chrome/120.0.0.0 Safari/537.36'
                                )
                            )
                        else:
                            raise Exception("Не удалось установить браузер")
                    else:
                        raise Exception(
                            "Пользователь отказался от установки браузера"
                        )

                except ImportError:
                    # Не интерактивный режим - автоматически устанавливаем
                    logger.info("Автоматическая установка браузера...")
                    success = await install_browser()
                    if success:
                        playwright = await async_playwright().start()
                        _browser = await playwright.chromium.launch(
                            headless=True,
                            args=[
                                '--no-sandbox',
                                '--disable-blink-features=AutomationControlled',
                                '--disable-web-security',
                                '--disable-features=VizDisplayCompositor'
                            ]
                        )
                        _context = await _browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=(
                                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/120.0.0.0 Safari/537.36'
                            )
                        )
                    else:
                        raise Exception("Не удалось установить браузер")
            else:
                raise e

    return _context


async def close_browser():
    """Закрывает браузер и освобождает ресурсы."""
    global _browser, _context

    if _context:
        await _context.close()
        _context = None

    if _browser:
        await _browser.close()
        _browser = None


async def download_file_browser(
    url: str,
    target_dir: Path,
    file_index: int,
    delay: float = BROWSER_DEFAULT_DELAY,
) -> None:
    """
    Скачивание файла через браузер для защищенных сайтов.

    Args:
        url: URL для скачивания
        target_dir: Директория для сохранения
        file_index: Индекс файла для именования
        delay: Задержка между запросами в секундах
    """
    async with browser_semaphore:
        # Базовое имя файла
        base_filename = f"{file_index}"
        new_filename = f"{base_filename}.jpeg"
        full_path = target_dir / new_filename

        # Проверка на существование файла
        counter = 1
        while await aiofiles.os.path.exists(full_path):
            new_filename = f"{base_filename}.{counter}.jpeg"
            full_path = target_dir / new_filename
            counter += 1

        # Задержка
        if delay > 0:
            await asyncio.sleep(delay + random.uniform(0, 0.2))

        try:
            context = await get_browser_context()
            page = await context.new_page()

            # Настройки страницы
            await page.set_extra_http_headers({
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            })

            # Переходим на страницу с изображением
            response = await page.goto(
                url,
                wait_until='networkidle',
                timeout=DOWNLOAD_TIMEOUT * 1000
            )

            if not response or response.status != 200:
                logger.error(
                    f"HTTP {response.status if response else 'None'} "
                    f"для {url}"
                )
                await page.close()
                return

            # Проверяем Content-Type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"URL {url} не содержит изображение")
                await page.close()
                return

            # Получаем содержимое изображения
            image_data = await response.body()

            if len(image_data) < 100:
                logger.warning(f"Слишком маленький файл для {url}")
                await page.close()
                return

            # Обрабатываем и сохраняем изображение
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                process_and_save_image_sync,
                image_data,
                full_path,
                content_type,
            )

            logger.info(
                f"Сохранено (браузер): {full_path} ({len(image_data)} байт)"
            )
            await page.close()

        except Exception as e:
            logger.error(f"Ошибка при скачивании через браузер {url}: {e}")


async def download_images_browser(
    urls: List[str],
    target_dir: Path,
    start_index: int = 1000,
    delay: float = BROWSER_DEFAULT_DELAY,
) -> None:
    """
    Скачивает изображения через браузер.

    Args:
        urls: Список URL для скачивания
        target_dir: Директория для сохранения
        start_index: Начальный индекс для именования файлов
        delay: Задержка между запросами в секундах
    """
    logger.info(f"Браузерный режим: скачивание {len(urls)} изображений")

    try:
        tasks = []
        for i, url in enumerate(urls):
            tasks.append(
                asyncio.create_task(
                    download_file_browser(
                        url,
                        target_dir,
                        start_index + i,
                        delay,
                    )
                )
            )
        await asyncio.gather(*tasks)
    finally:
        # Закрываем браузер после завершения всех задач
        await close_browser()
