"""
Модуль для мониторинга ресурсов и управления памятью.
"""

import gc
import psutil
import tempfile

try:
    import resource  # Unix only
except ImportError:
    resource = None  # Windows compatibility
from pathlib import Path
from typing import Set, Callable
import asyncio
import aiofiles.os

from utils.logger import logger


class ResourceManager:
    """Менеджер ресурсов для мониторинга памяти и очистки временных файлов."""

    def __init__(self):
        self.temp_files: Set[Path] = set()
        self.temp_dirs: Set[Path] = set()
        self.memory_threshold_mb = 1024  # 1GB warning threshold
        self.cleanup_callbacks = []
        self._process = psutil.Process()
        self.open_files: Set[object] = set()  # Отслеживаем открытые файлы
        self.fd_limit_warning = 900  # Предупреждение при приближении к лимиту

    def register_temp_file(self, filepath: Path) -> None:
        """
        Регистрирует временный файл для автоматической очистки при завершении работы.

        Файлы, зарегистрированные через этот метод, будут удалены при вызове cleanup_all().

        Args:
            filepath: Путь к временному файлу
        """
        self.temp_files.add(filepath)
        logger.debug(f"Зарегистрирован временный файл: {filepath}")

    def register_temp_dir(self, dirpath: Path) -> None:
        """
        Регистрирует временную директорию для автоматической очистки при завершении работы.

        Директории, зарегистрированные через этот метод, будут полностью удалены
        со всем содержимым при вызове cleanup_all().

        Args:
            dirpath: Путь к временной директории
        """
        self.temp_dirs.add(dirpath)
        logger.debug(f"Зарегистрирована временная директория: {dirpath}")

    def add_cleanup_callback(self, callback):
        """
        Добавляет callback-функцию для выполнения при очистке ресурсов.

        Колбэки вызываются перед очисткой временных файлов и могут использоваться
        для закрытия открытых ресурсов или сохранения состояния.

        Args:
            callback: Функция, которая будет вызвана при очистке (может быть async)
        """
        self.cleanup_callbacks.append(callback)

    def get_memory_usage(self) -> dict:
        """
        Возвращает детальную информацию об использовании памяти процессом.

        Использует psutil для получения реальных метрик памяти, включая RSS,
        VMS и процент использования общей памяти системы.

        Returns:
            dict: Словарь с ключами 'rss_mb', 'vms_mb', 'percent', 'available_mb'
        """
        try:
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()

            return {
                "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size
                "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                "percent": memory_percent,
                "available_mb": psutil.virtual_memory().available / (1024 * 1024),
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о памяти: {e}")
            return {}

    def check_memory_usage(self) -> bool:
        """
        Проверяет использование памяти и предупреждает о превышении порога.

        Returns:
            bool: True если использование памяти в норме, False если превышен порог
        """
        memory_info = self.get_memory_usage()
        if not memory_info:
            return True

        rss_mb = memory_info.get("rss_mb", 0)

        if rss_mb > self.memory_threshold_mb:
            logger.warning(
                f"Высокое использование памяти: {rss_mb:.1f} MB "
                f"(порог: {self.memory_threshold_mb} MB)"
            )
            logger.info(f"Детали памяти: {memory_info}")
            return False

        return True

    async def cleanup_temp_files(self) -> int:
        """
        Очищает все зарегистрированные временные файлы.

        Returns:
            int: Количество удаленных файлов
        """
        cleaned_count = 0

        for filepath in self.temp_files.copy():
            try:
                if await aiofiles.os.path.exists(filepath):
                    await aiofiles.os.remove(filepath)
                    cleaned_count += 1
                    logger.debug(f"Удален временный файл: {filepath}")
                self.temp_files.discard(filepath)
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла {filepath}: {e}")

        return cleaned_count

    async def cleanup_temp_dirs(self) -> int:
        """
        Очищает все зарегистрированные временные директории.

        Returns:
            int: Количество удаленных директорий
        """
        cleaned_count = 0

        for dirpath in self.temp_dirs.copy():
            try:
                if await aiofiles.os.path.exists(dirpath):
                    # Удаляем все файлы в директории
                    for item in await aiofiles.os.listdir(dirpath):
                        item_path = dirpath / item
                        if await aiofiles.os.path.isfile(item_path):
                            await aiofiles.os.remove(item_path)

                    # Удаляем саму директорию
                    await aiofiles.os.rmdir(dirpath)
                    cleaned_count += 1
                    logger.debug(f"Удалена временная директория: {dirpath}")

                self.temp_dirs.discard(dirpath)
            except Exception as e:
                logger.error(f"Ошибка при удалении временной директории {dirpath}: {e}")

        return cleaned_count

    def force_garbage_collection(self) -> dict:
        """
        Принудительно запускает сборку мусора и возвращает статистику.

        Returns:
            dict: Статистика сборки мусора
        """
        before_memory = self.get_memory_usage()

        # Запускаем сборку мусора для всех поколений
        collected = {"gen0": gc.collect(0), "gen1": gc.collect(1), "gen2": gc.collect(2)}

        after_memory = self.get_memory_usage()

        freed_mb = before_memory.get("rss_mb", 0) - after_memory.get("rss_mb", 0)

        stats = {
            "collected_objects": sum(collected.values()),
            "freed_memory_mb": freed_mb,
            "before_memory": before_memory,
            "after_memory": after_memory,
        }

        if freed_mb > 1:  # Логируем только если освободили больше 1 MB
            logger.info(f"Сборка мусора освободила {freed_mb:.1f} MB памяти")

        return stats

    async def cleanup_all(self) -> dict:
        """
        Выполняет полную очистку всех ресурсов.

        Returns:
            dict: Статистика очистки
        """
        logger.info("Начинается полная очистка ресурсов...")

        # Вызываем зарегистрированные callbacks
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Ошибка в callback очистки: {e}")

        # Очищаем временные файлы и директории
        files_cleaned = await self.cleanup_temp_files()
        dirs_cleaned = await self.cleanup_temp_dirs()

        # Закрываем отслеживаемые файлы (файловые дескрипторы)
        closed_files = 0
        for file_handle in self.open_files.copy():
            try:
                if hasattr(file_handle, "close"):
                    if asyncio.iscoroutinefunction(file_handle.close):
                        await file_handle.close()
                    else:
                        file_handle.close()
                    closed_files += 1
            except Exception as e:
                logger.error(f"Ошибка при закрытии файла: {e}")
        self.open_files.clear()

        # Принудительная сборка мусора
        gc_stats = self.force_garbage_collection()

        stats = {
            "temp_files_cleaned": files_cleaned,
            "temp_dirs_cleaned": dirs_cleaned,
            "garbage_collection": gc_stats,
            "final_memory": self.get_memory_usage(),
        }

        logger.info(
            f"Очистка ресурсов завершена: {files_cleaned} файлов, "
            f"{dirs_cleaned} директорий, {gc_stats['collected_objects']} объектов"
        )

        return stats


# Глобальный экземпляр менеджера ресурсов
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Возвращает глобальный экземпляр менеджера ресурсов."""
    return resource_manager


def monitor_memory_usage(func: Callable) -> Callable:
    """Декоратор для мониторинга использования памяти функцией."""

    def wrapper(*args, **kwargs):
        before_memory = resource_manager.get_memory_usage()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            after_memory = resource_manager.get_memory_usage()
            memory_diff = after_memory.get("rss_mb", 0) - before_memory.get("rss_mb", 0)

            if memory_diff > 10:  # Логируем только значительные изменения
                logger.debug(
                    f"Функция {func.__name__} изменила использование памяти на {memory_diff:.1f} MB"
                )

            # Проверяем превышение порога
            resource_manager.check_memory_usage()

    return wrapper


async def create_temp_file(suffix: str = "", prefix: str = "async_img_") -> Path:
    """
    Создает временный файл и регистрирует его для автоматической очистки.

    Args:
        suffix: Суффикс для имени файла
        prefix: Префикс для имени файла

    Returns:
        Path: Путь к созданному временному файлу
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()

    resource_manager.register_temp_file(temp_path)
    return temp_path


async def create_temp_dir(prefix: str = "async_img_") -> Path:
    """
    Создает временную директорию и регистрирует ее для автоматической очистки.

    Args:
        prefix: Префикс для имени директории

    Returns:
        Path: Путь к созданной временной директории
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    resource_manager.register_temp_dir(temp_dir)
    return temp_dir
