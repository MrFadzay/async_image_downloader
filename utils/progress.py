"""
Модуль для отображения прогресса выполнения длительных операций.
"""
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from tqdm.asyncio import tqdm
from tqdm import tqdm as sync_tqdm

from utils.logger import logger


class ProgressTracker:
    """Менеджер для отслеживания прогресса различных операций."""
    
    def __init__(self) -> None:
        self._progress_bars: Dict[str, tqdm] = {}
        self._active_tasks: Dict[str, bool] = {}
    
    @asynccontextmanager
    async def track_download_progress(
        self, 
        total_urls: int, 
        description: str = "Скачивание изображений"
    ) -> AsyncGenerator[tqdm, None]:
        """
        Создает и управляет прогресс-баром для скачивания изображений.
        
        Args:
            total_urls: Общее количество URL для скачивания
            description: Описание процесса для отображения
            
        Yields:
            tqdm: Объект прогресс-бара для обновления
        """
        progress_bar = tqdm(
            total=total_urls,
            desc=description,
            unit="файл",
            unit_scale=False,
            colour="green",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        try:
            yield progress_bar
        finally:
            progress_bar.close()
    
    @asynccontextmanager 
    async def track_duplicate_progress(
        self, 
        total_files: int,
        description: str = "Поиск дубликатов"
    ) -> AsyncGenerator[tqdm, None]:
        """
        Создает и управляет прогресс-баром для поиска дубликатов.
        
        Args:
            total_files: Общее количество файлов для обработки
            description: Описание процесса для отображения
            
        Yields:
            tqdm: Объект прогресс-бара для обновления
        """
        progress_bar = tqdm(
            total=total_files,
            desc=description,
            unit="файл",
            unit_scale=False,
            colour="blue",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        try:
            yield progress_bar
        finally:
            progress_bar.close()
    
    @asynccontextmanager
    async def track_uniquify_progress(
        self, 
        total_files: int,
        description: str = "Уникализация изображений"
    ) -> AsyncGenerator[tqdm, None]:
        """
        Создает и управляет прогресс-баром для уникализации изображений.
        
        Args:
            total_files: Общее количество файлов для обработки
            description: Описание процесса для отображения
            
        Yields:
            tqdm: Объект прогресс-бара для обновления
        """
        progress_bar = tqdm(
            total=total_files,
            desc=description,
            unit="файл", 
            unit_scale=False,
            colour="yellow",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        try:
            yield progress_bar
        finally:
            progress_bar.close()
    
    def create_file_processing_bar(
        self, 
        total_files: int, 
        description: str = "Обработка файлов"
    ) -> sync_tqdm:
        """
        Создает синхронный прогресс-бар для обработки файлов.
        
        Args:
            total_files: Общее количество файлов
            description: Описание процесса
            
        Returns:
            sync_tqdm: Синхронный прогресс-бар
        """
        return sync_tqdm(
            total=total_files,
            desc=description,
            unit="файл",
            unit_scale=False,
            colour="cyan"
        )


# Глобальный экземпляр трекера прогресса
progress_tracker = ProgressTracker()


def get_progress_tracker() -> ProgressTracker:
    """Возвращает глобальный экземпляр трекера прогресса."""
    return progress_tracker


async def show_operation_summary(
    operation_name: str,
    total_processed: int,
    successful: int,
    failed: int,
    elapsed_time: float
) -> None:
    """
    Отображает сводку по завершенной операции.
    
    Args:
        operation_name: Название операции
        total_processed: Общее количество обработанных элементов
        successful: Количество успешно обработанных
        failed: Количество неудачных
        elapsed_time: Время выполнения в секундах
    """
    success_rate = (successful / total_processed * 100) if total_processed > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"📊 СВОДКА: {operation_name}")
    print(f"{'='*60}")
    print(f"🎯 Всего обработано: {total_processed}")
    print(f"✅ Успешно: {successful} ({success_rate:.1f}%)")
    print(f"❌ Неудачно: {failed}")
    print(f"⏱️  Время выполнения: {elapsed_time:.2f} сек")
    print(f"{'='*60}\n")
    
    logger.info(
        f"{operation_name} завершено: {successful}/{total_processed} успешно "
        f"за {elapsed_time:.2f} сек"
    )


async def show_download_stats(
    downloaded: int,
    skipped: int, 
    errors: int,
    total_size_mb: float,
    elapsed_time: float
) -> None:
    """
    Отображает детальную статистику скачивания.
    
    Args:
        downloaded: Количество скачанных файлов
        skipped: Количество пропущенных файлов
        errors: Количество ошибок
        total_size_mb: Общий размер скачанных файлов в МБ
        elapsed_time: Время выполнения в секундах
    """
    total_files = downloaded + skipped + errors
    download_speed = total_size_mb / elapsed_time if elapsed_time > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"📥 СТАТИСТИКА СКАЧИВАНИЯ")
    print(f"{'='*60}")
    print(f"📁 Скачано файлов: {downloaded}")
    print(f"⏭️  Пропущено: {skipped}")
    print(f"❌ Ошибок: {errors}")
    print(f"📊 Общий объем: {total_size_mb:.2f} МБ")
    print(f"🚀 Скорость: {download_speed:.2f} МБ/сек")
    print(f"⏱️  Время: {elapsed_time:.2f} сек")
    print(f"{'='*60}\n")