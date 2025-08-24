"""
Менеджер сессий для управления паузой/возобновлением загрузок.
"""

import asyncio
import json
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import aiofiles

from utils.logger import logger
from utils.config_manager import IMAGE_DIR


@dataclass
class DownloadSessionState:
    """Состояние сессии загрузки."""

    session_id: str
    urls: List[str]
    start_index: int
    retries: int
    target_dir: str
    completed_urls: List[str]
    failed_urls: List[str]
    current_index: int
    is_paused: bool
    created_at: str
    last_updated: str
    total_urls: int
    completed_count: int


class DownloadSessionManager:
    """Менеджер сессий загрузки с поддержкой паузы/возобновления."""

    def __init__(self):
        self.session_file = IMAGE_DIR / "download_session.json"
        self.current_session: Optional[DownloadSessionState] = None
        self.is_paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Изначально не на паузе
        self.cancel_event = asyncio.Event()
        self.pause_callbacks: List[Callable] = []
        self.resume_callbacks: List[Callable] = []
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Настраивает обработчики сигналов для паузы по Ctrl+C."""

        def signal_handler(sig, frame):
            logger.info(
                "Получен сигнал прерывания. Приостанавливаем загрузку...")
            self.pause()

        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except AttributeError:
            # Windows compatibility
            pass

    async def create_session(
        self,
        urls: List[str],
        start_index: int = 1000,
        retries: int = 3,
        target_dir: Optional[Path] = None,
    ) -> str:
        """
        Создает новую сессию загрузки.

        Args:
            urls: Список URL для загрузки
            start_index: Начальный индекс файлов
            retries: Количество повторов
            target_dir: Целевая директория

        Returns:
            str: ID созданной сессии
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if target_dir is None:
            from utils.config_manager import DEFAULT_DOWNLOAD_DIR_NAME

            target_dir = IMAGE_DIR / DEFAULT_DOWNLOAD_DIR_NAME

        self.current_session = DownloadSessionState(
            session_id=session_id,
            urls=urls,
            start_index=start_index,
            retries=retries,
            target_dir=str(target_dir),
            completed_urls=[],
            failed_urls=[],
            current_index=0,
            is_paused=False,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            total_urls=len(urls),
            completed_count=0,
        )

        await self.save_session()
        logger.info(f"Создана новая сессия загрузки: {session_id}")
        return session_id

    async def save_session(self) -> None:
        """Сохраняет текущую сессию в файл."""
        if not self.current_session:
            return

        self.current_session.last_updated = datetime.now().isoformat()

        try:
            # Создаем директорию если не существует
            self.session_file.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(self.session_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(asdict(self.current_session),
                               ensure_ascii=False, indent=2)
                )
            logger.debug(
                f"Сессия сохранена: {self.current_session.session_id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении сессии: {e}")

    async def load_session(
        self, session_id: Optional[str] = None
    ) -> Optional[DownloadSessionState]:
        """
        Загружает сессию из файла.

        Args:
            session_id: ID сессии для загрузки (если None, загружает последнюю)

        Returns:
            Optional[DownloadSessionState]: Загруженная сессия или None
        """
        try:
            if not self.session_file.exists():
                return None

            async with aiofiles.open(self.session_file, "r", encoding="utf-8") as f:
                content = await f.read()
                session_data = json.loads(content)

            session = DownloadSessionState(**session_data)

            if session_id is None or session.session_id == session_id:
                self.current_session = session
                logger.info(f"Загружена сессия: {session.session_id}")
                return session

        except Exception as e:
            logger.error(f"Ошибка при загрузке сессии: {e}")

        return None

    async def update_progress(self, url: str, success: bool) -> None:
        """
        Обновляет прогресс сессии.

        Args:
            url: URL который был обработан
            success: Успешно ли завершилась загрузка
        """
        if not self.current_session:
            return

        if success:
            self.current_session.completed_urls.append(url)
            self.current_session.completed_count += 1
        else:
            self.current_session.failed_urls.append(url)

        self.current_session.current_index += 1
        await self.save_session()

    def pause(self) -> None:
        """Приостанавливает загрузку."""
        if not self.is_paused:
            self.is_paused = True
            self.pause_event.clear()

            if self.current_session:
                self.current_session.is_paused = True
                # Асинхронно сохраняем состояние
                asyncio.create_task(self.save_session())

            logger.info("⏸️  Загрузка приостановлена")

            # Вызываем коллбэки паузы
            for callback in self.pause_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Ошибка в коллбэке паузы: {e}")

    def resume(self) -> None:
        """Возобновляет загрузку."""
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()

            if self.current_session:
                self.current_session.is_paused = False
                # Асинхронно сохраняем состояние
                asyncio.create_task(self.save_session())

            logger.info("▶️  Загрузка возобновлена")

            # Вызываем коллбэки возобновления
            for callback in self.resume_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Ошибка в коллбэке возобновления: {e}")

    def cancel(self) -> None:
        """Отменяет загрузку."""
        self.cancel_event.set()
        logger.info("❌ Загрузка отменена")

    async def wait_if_paused(self) -> bool:
        """
        Ожидает, если загрузка на паузе.

        Returns:
            bool: True если операция должна продолжаться, False если отменена
        """
        if self.cancel_event.is_set():
            return False

        if self.is_paused:
            logger.debug("Ожидание возобновления загрузки...")
            await self.pause_event.wait()

        return not self.cancel_event.is_set()

    def get_remaining_urls(self) -> List[str]:
        """
        Возвращает список URL которые еще не были обработаны.

        Returns:
            List[str]: Необработанные URL
        """
        if not self.current_session:
            return []

        processed_urls = set(
            self.current_session.completed_urls + self.current_session.failed_urls)
        return [url for url in self.current_session.urls if url not in processed_urls]

    def get_session_stats(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает статистику текущей сессии.

        Returns:
            Optional[Dict[str, Any]]: Статистика сессии или None если сессии нет
        """
        if not self.current_session:
            return None

        completed_count = len(self.current_session.completed_urls)
        failed_count = len(self.current_session.failed_urls)
        remaining_count = len(self.get_remaining_urls())

        return {
            "session_id": self.current_session.session_id,
            "total_urls": self.current_session.total_urls,
            "completed": completed_count,
            "completed_count": completed_count,
            "failed": failed_count,
            "failed_count": failed_count,
            "remaining": remaining_count,
            "remaining_count": remaining_count,
            "progress_percent": (
                (completed_count / self.current_session.total_urls * 100)
                if self.current_session.total_urls > 0
                else 0
            ),
            "is_paused": self.current_session.is_paused,
            "created_at": self.current_session.created_at,
            "last_updated": self.current_session.last_updated,
        }

    def add_pause_callback(self, callback: Callable) -> None:
        """Добавляет коллбэк для вызова при паузе."""
        self.pause_callbacks.append(callback)

    def add_resume_callback(self, callback: Callable) -> None:
        """Добавляет коллбэк для вызова при возобновлении."""
        self.resume_callbacks.append(callback)

    def cleanup_session(self) -> None:
        """Очищает завершенную сессию."""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                logger.debug("Файл сессии удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла сессии: {e}")

        self.current_session = None
        self.is_paused = False
        self.pause_event.set()
        self.cancel_event.clear()


# Глобальный экземпляр менеджера сессий
session_manager = DownloadSessionManager()


def get_session_manager() -> DownloadSessionManager:
    """Возвращает глобальный экземпляр менеджера сессий."""
    return session_manager
