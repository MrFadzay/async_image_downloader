"""
Улучшенная система обработки ошибок и пользовательских сообщений.
"""
import traceback
from typing import Dict, Optional, Any, Callable, List
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

from utils.logger import logger


class ErrorSeverity(Enum):
    """Уровни критичности ошибок."""
    LOW = "low"       # Предупреждения, не критичные ошибки
    MEDIUM = "medium" # Ошибки, влияющие на функциональность
    HIGH = "high"     # Критичные ошибки, прерывающие работу
    CRITICAL = "critical" # Системные ошибки


@dataclass
class ErrorContext:
    """Контекст ошибки для детального анализа."""
    operation: str
    file_path: Optional[Path] = None
    url: Optional[str] = None
    attempt: int = 1
    max_attempts: int = 1
    additional_info: Optional[Dict[str, Any]] = None


class UserFriendlyError:
    """Класс для создания понятных пользователю сообщений об ошибках."""
    
    # Словарь переводов технических ошибок в понятные сообщения
    ERROR_TRANSLATIONS = {
        # Сетевые ошибки
        "ConnectTimeout": "Превышено время ожидания подключения к серверу",
        "ReadTimeout": "Превышено время ожидания ответа от сервера",
        "ConnectionError": "Ошибка подключения к серверу",
        "SSLError": "Ошибка защищенного соединения (SSL)",
        "DNSError": "Не удалось найти сервер (DNS ошибка)",
        "HTTPError": "Ошибка HTTP запроса",
        
        # Файловые ошибки
        "FileNotFoundError": "Файл или директория не найдены",
        "PermissionError": "Недостаточно прав для доступа к файлу",
        "IsADirectoryError": "Указанный путь является директорией, а не файлом",
        "NotADirectoryError": "Указанный путь не является директорией",
        "OSError": "Системная ошибка при работе с файлом",
        
        # Ошибки изображений
        "UnidentifiedImageError": "Файл не является изображением или поврежден",
        "DecompressionBombError": "Изображение слишком большое и может быть опасным",
        "OutOfMemoryError": "Недостаточно памяти для обработки изображения",
        
        # Ошибки валидации
        "ValidationError": "Ошибка проверки данных",
        "ValueError": "Некорректное значение параметра",
        "TypeError": "Неправильный тип данных",
    }
    
    # Рекомендации по исправлению ошибок
    ERROR_SUGGESTIONS = {
        "ConnectTimeout": [
            "🌐 Проверьте подключение к интернету",
            "🔄 Попробуйте еще раз через несколько минут",
            "⚙️ Увеличьте время ожидания в настройках"
        ],
        "ReadTimeout": [
            "📡 Сервер медленно отвечает, попробуйте позже",
            "🔄 Повторите попытку",
            "⚙️ Увеличьте время ожидания"
        ],
        "FileNotFoundError": [
            "📁 Проверьте правильность пути к файлу",
            "🔍 Убедитесь, что файл существует",
            "📝 Проверьте права доступа к директории"
        ],
        "PermissionError": [
            "🔐 Запустите программу с правами администратора",
            "📝 Проверьте права доступа к файлу/директории",
            "🔓 Убедитесь, что файл не используется другой программой"
        ],
        "UnidentifiedImageError": [
            "🖼️ Убедитесь, что файл является изображением",
            "🔍 Проверьте, не поврежден ли файл",
            "📋 Поддерживаемые форматы: JPEG, PNG, WebP, GIF"
        ],
        "ValidationError": [
            "✅ Проверьте правильность введенных данных",
            "📋 Следуйте требованиям к формату",
            "❓ Обратитесь к справке для получения помощи"
        ]
    }

    @classmethod
    def get_user_friendly_message(
        cls, 
        error: Exception, 
        context: Optional[ErrorContext] = None
    ) -> str:
        """
        Преобразует техническую ошибку в понятное пользователю сообщение.
        
        Args:
            error: Исключение
            context: Контекст ошибки
            
        Returns:
            str: Понятное пользователю сообщение
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Получаем понятное описание ошибки
        friendly_msg = cls.ERROR_TRANSLATIONS.get(
            error_type, 
            f"Произошла ошибка: {error_msg}"
        )
        
        # Добавляем контекст
        if context:
            if context.file_path:
                friendly_msg += f" (файл: {context.file_path.name})"
            elif context.url:
                friendly_msg += f" (URL: {context.url})"
            
            if context.attempt > 1:
                friendly_msg += f" [попытка {context.attempt}/{context.max_attempts}]"
        
        return friendly_msg

    @classmethod
    def get_suggestions(cls, error: Exception) -> List[str]:
        """
        Возвращает список рекомендаций по исправлению ошибки.
        
        Args:
            error: Исключение
            
        Returns:
            List[str]: Список рекомендаций
        """
        error_type = type(error).__name__
        return cls.ERROR_SUGGESTIONS.get(error_type, [
            "🔄 Попробуйте выполнить операцию еще раз",
            "📋 Проверьте правильность введенных данных",
            "❓ Обратитесь за помощью если проблема повторяется"
        ])


class EnhancedErrorHandler:
    """Улучшенный обработчик ошибок с детальными сообщениями."""
    
    def __init__(self):
        self.error_stats: Dict[str, int] = {}
        self.recent_errors: List[Dict] = []
        self.max_recent_errors = 50

    def handle_error(
        self, 
        error: Exception, 
        context: Optional[ErrorContext] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        show_suggestions: bool = True
    ) -> None:
        """
        Обрабатывает ошибку с улучшенным выводом сообщений.
        
        Args:
            error: Исключение
            context: Контекст ошибки
            severity: Уровень критичности
            show_suggestions: Показывать ли рекомендации
        """
        error_type = type(error).__name__
        
        # Обновляем статистику ошибок
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        
        # Получаем понятное сообщение
        friendly_msg = UserFriendlyError.get_user_friendly_message(error, context)
        
        # Определяем уровень логирования
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"🔥 КРИТИЧЕСКАЯ ОШИБКА: {friendly_msg}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"❌ ОШИБКА: {friendly_msg}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: {friendly_msg}")
        else:
            logger.info(f"ℹ️ ИНФОРМАЦИЯ: {friendly_msg}")
        
        # Показываем рекомендации
        if show_suggestions and severity != ErrorSeverity.LOW:
            suggestions = UserFriendlyError.get_suggestions(error)
            if suggestions:
                print(f"\n💡 Возможные решения:")
                for suggestion in suggestions:
                    print(f"   {suggestion}")
                print()  # Пустая строка для разделения
        
        # Сохраняем в историю недавних ошибок
        error_record = {
            'type': error_type,
            'message': friendly_msg,
            'context': context,
            'severity': severity.value,
            'timestamp': logger.handlers[0].formatter.formatTime(None) if logger.handlers else None
        }
        
        self.recent_errors.append(error_record)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
    
    def handle_download_error(
        self, 
        error: Exception, 
        url: str, 
        attempt: int, 
        max_attempts: int
    ) -> None:
        """Специализированный обработчик ошибок скачивания."""
        context = ErrorContext(
            operation="download",
            url=url,
            attempt=attempt,
            max_attempts=max_attempts
        )
        
        # Определяем критичность на основе типа ошибки
        if isinstance(error, (ConnectionError, OSError)):
            severity = ErrorSeverity.HIGH
        elif "429" in str(error):  # Rate limiting
            severity = ErrorSeverity.LOW
            print(f"⏳ Сервер ограничивает скорость запросов. Ожидание...")
        else:
            severity = ErrorSeverity.MEDIUM
            
        self.handle_error(error, context, severity)
    
    def handle_file_error(
        self, 
        error: Exception, 
        file_path: Path, 
        operation: str
    ) -> None:
        """Специализированный обработчик файловых ошибок."""
        context = ErrorContext(
            operation=operation,
            file_path=file_path
        )
        
        # Файловые ошибки обычно критичные
        severity = ErrorSeverity.HIGH if isinstance(error, (FileNotFoundError, PermissionError)) else ErrorSeverity.MEDIUM
        
        self.handle_error(error, context, severity)
    
    def handle_image_error(
        self, 
        error: Exception, 
        file_path: Path, 
        operation: str = "image_processing"
    ) -> None:
        """Специализированный обработчик ошибок обработки изображений."""
        from PIL import Image
        
        context = ErrorContext(
            operation=operation,
            file_path=file_path
        )
        
        # Определяем критичность
        if isinstance(error, Image.UnidentifiedImageError):
            severity = ErrorSeverity.MEDIUM
            print(f"🖼️ Файл {file_path.name} не является изображением или поврежден")
        elif isinstance(error, (MemoryError, Image.DecompressionBombError)):
            severity = ErrorSeverity.HIGH
            print(f"💾 Изображение {file_path.name} слишком большое для обработки")
        else:
            severity = ErrorSeverity.MEDIUM
            
        self.handle_error(error, context, severity)
    
    def get_error_summary(self) -> str:
        """Возвращает сводку по ошибкам."""
        if not self.error_stats:
            return "✅ Ошибок не обнаружено"
        
        summary = "📊 Сводка по ошибкам:\n"
        for error_type, count in sorted(self.error_stats.items(), key=lambda x: x[1], reverse=True):
            friendly_name = UserFriendlyError.ERROR_TRANSLATIONS.get(error_type, error_type)
            summary += f"   {error_type}: {count} раз(а) - {friendly_name}\n"
        
        return summary
    
    def show_help_for_common_errors(self) -> None:
        """Показывает справку по частым ошибкам."""
        if not self.error_stats:
            return
            
        most_common = max(self.error_stats.items(), key=lambda x: x[1])
        error_type = most_common[0]
        
        print(f"\n❓ СПРАВКА ПО ЧАСТОЙ ОШИБКЕ: {error_type}")
        print("=" * 50)
        
        friendly_name = UserFriendlyError.ERROR_TRANSLATIONS.get(error_type, error_type)
        print(f"Описание: {friendly_name}")
        
        suggestions = UserFriendlyError.ERROR_SUGGESTIONS.get(error_type, [])
        if suggestions:
            print("\n💡 Рекомендации:")
            for suggestion in suggestions:
                print(f"   {suggestion}")
        print()


# Глобальный экземпляр обработчика ошибок
error_handler = EnhancedErrorHandler()


def get_error_handler() -> EnhancedErrorHandler:
    """Возвращает глобальный экземпляр обработчика ошибок."""
    return error_handler


def handle_error_with_context(
    error: Exception,
    operation: str,
    file_path: Optional[Path] = None,
    url: Optional[str] = None,
    **kwargs
) -> None:
    """
    Удобная функция для обработки ошибок с контекстом.
    
    Args:
        error: Исключение
        operation: Название операции
        file_path: Путь к файлу (опционально)
        url: URL (опционально)
        **kwargs: Дополнительные параметры контекста
    """
    context = ErrorContext(
        operation=operation,
        file_path=file_path,
        url=url,
        additional_info=kwargs
    )
    
    error_handler.handle_error(error, context)


class ProgressErrorHandler:
    """Обработчик ошибок с учетом прогресса операции."""
    
    def __init__(self, total_items: int, operation_name: str):
        self.total_items = total_items
        self.operation_name = operation_name
        self.successful_items = 0
        self.failed_items = 0
        self.errors: List[Exception] = []
    
    def report_success(self) -> None:
        """Сообщает об успешном выполнении элемента."""
        self.successful_items += 1
    
    def report_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Сообщает об ошибке выполнения элемента."""
        self.failed_items += 1
        self.errors.append(error)
        
        # Показываем прогресс ошибок
        completed = self.successful_items + self.failed_items
        if completed % 10 == 0 or self.failed_items <= 5:  # Показываем первые 5 ошибок или каждую 10-ю
            error_msg = UserFriendlyError.get_user_friendly_message(error)
            print(f"❌ [{completed}/{self.total_items}] {error_msg}")
            if context:
                print(f"   Контекст: {context}")
    
    def get_final_report(self) -> str:
        """Возвращает финальный отчет об операции."""
        success_rate = (self.successful_items / self.total_items * 100) if self.total_items > 0 else 0
        
        report = f"\n📊 ИТОГИ ОПЕРАЦИИ: {self.operation_name.upper()}\n"
        report += "=" * 50 + "\n"
        report += f"✅ Успешно: {self.successful_items} ({success_rate:.1f}%)\n"
        report += f"❌ Ошибок: {self.failed_items}\n"
        report += f"📋 Всего: {self.total_items}\n"
        
        if self.errors:
            # Группируем ошибки по типам
            error_counts = {}
            for error in self.errors:
                error_type = type(error).__name__
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            report += "\n🔍 Типы ошибок:\n"
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                friendly_name = UserFriendlyError.ERROR_TRANSLATIONS.get(error_type, error_type)
                report += f"   {error_type}: {count} раз(а) - {friendly_name}\n"
        
        return report