"""
Модуль для отображения прогресса выполнения длительных операций.
"""
import asyncio
import threading
from typing import Optional, AsyncGenerator, Dict, Any, TYPE_CHECKING
from contextlib import asynccontextmanager

from tqdm.asyncio import tqdm
from tqdm import tqdm as sync_tqdm

from utils.logger import logger

if TYPE_CHECKING:
    from utils.session_manager import DownloadSessionManager


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
    
    def create_pausable_progress_bar(
        self, 
        total: int, 
        description: str = "Обработка",
        session_manager: Optional["DownloadSessionManager"] = None
    ) -> "PausableProgressBar":
        """
        Создает приостанавливаемый прогресс-бар.
        
        Args:
            total: Общее количество элементов
            description: Описание процесса
            session_manager: Менеджер сессий для управления паузой
            
        Returns:
            PausableProgressBar: Прогресс-бар с поддержкой паузы
        """
        return PausableProgressBar(total, description, session_manager)


class PausableProgressBar:
    """Прогресс-бар с поддержкой паузы/возобновления."""
    
    def __init__(
        self, 
        total: int, 
        description: str = "Обработка",
        session_manager: Optional["DownloadSessionManager"] = None
    ):
        self.total = total
        self.description = description
        self.session_manager = session_manager
        self.progress_bar: Optional[tqdm] = None
        self.completed = 0
        self.is_paused = False
        
        # Регистрируем коллбэки для паузы/возобновления
        if self.session_manager:
            self.session_manager.add_pause_callback(self._on_pause)
            self.session_manager.add_resume_callback(self._on_resume)
    
    def __enter__(self):
        """Контекстный менеджер - вход."""
        self.progress_bar = tqdm(
            total=self.total,
            desc=self.description,
            unit="файл",
            unit_scale=False,
            colour="green",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход."""
        if self.progress_bar:
            self.progress_bar.close()
    
    def update(self, n: int = 1) -> None:
        """Обновляет прогресс."""
        if self.progress_bar and not self.is_paused:
            self.progress_bar.update(n)
            self.completed += n
    
    def set_description(self, desc: str) -> None:
        """Устанавливает описание прогресс-бара."""
        if self.progress_bar:
            self.progress_bar.set_description(desc)
    
    def _on_pause(self) -> None:
        """Коллбэк при паузе."""
        self.is_paused = True
        if self.progress_bar:
            self.progress_bar.set_description(f"⏸️  ПАУЗА - {self.description}")
    
    def _on_resume(self) -> None:
        """Коллбэк при возобновлении."""
        self.is_paused = False
        if self.progress_bar:
            self.progress_bar.set_description(self.description)
    
    async def wait_if_paused(self) -> bool:
        """Ждет если на паузе."""
        if self.session_manager:
            return await self.session_manager.wait_if_paused()
        return True


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