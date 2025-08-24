"""
Утилиты для подтверждения деструктивных операций.
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import questionary

from utils.logger import logger


def _should_skip_confirmation() -> bool:
    """Проверяет, нужно ли пропустить подтверждение."""
    try:
        from main import get_skip_confirmations
        return get_skip_confirmations()
    except (ImportError, AttributeError):
        return False


class ConfirmationDialog:
    """Класс для создания диалогов подтверждения деструктивных операций."""
    
    @staticmethod
    async def confirm_rename_duplicates(
        duplicates_info: List[tuple], 
        directory: Path
    ) -> bool:
        """
        Запрашивает подтверждение для переименования дубликатов.
        
        Args:
            duplicates_info: Список информации о дубликатах
            directory: Директория обработки
            
        Returns:
            bool: True если пользователь подтверждает операцию
        """
        if not duplicates_info:
            return True
        
        # Проверяем флаг пропуска подтверждений
        if _should_skip_confirmation():
            logger.info("🚀 Пропускаем подтверждение (--yes)")
            return True
            
        count = len(duplicates_info)
        
        print(f"\n{'='*60}")
        print(f"🔍 ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР ПЕРЕИМЕНОВАНИЯ")
        print(f"{'='*60}")
        print(f"📁 Директория: {directory}")
        print(f"🔄 Файлов для переименования: {count}")
        print(f"{'='*60}")
        
        # Показываем первые несколько файлов для примера
        preview_count = min(5, count)
        print(f"\n📋 Примеры переименования (показано {preview_count} из {count}):")
        
        for i, (file_path, _, original_path) in enumerate(duplicates_info[:preview_count]):
            file_stem = file_path.stem
            suffix = file_path.suffix
            new_name = f"{file_stem}_duplicate_1{suffix}"
            
            print(f"  {i+1}. {file_path.name}")
            print(f"     ➜ {new_name}")
            print(f"     (дубликат: {original_path.name})")
            print()
        
        if count > preview_count:
            print(f"  ... и еще {count - preview_count} файлов")
        
        print(f"\n⚠️  ВНИМАНИЕ: Операция изменит имена {count} файлов!")
        print("   Файлы получат суффикс '_duplicate_N' где N - номер дубликата")
        
        return await questionary.confirm(
            "Продолжить переименование дубликатов?",
            default=False
        ).ask_async()
    
    @staticmethod
    async def confirm_modify_duplicates(
        duplicates_info: List[tuple], 
        directory: Path
    ) -> bool:
        """
        Запрашивает подтверждение для модификации дубликатов.
        
        Args:
            duplicates_info: Список информации о дубликатах
            directory: Директория обработки
            
        Returns:
            bool: True если пользователь подтверждает операцию
        """
        if not duplicates_info:
            return True
        
        # Проверяем флаг пропуска подтверждений
        if _should_skip_confirmation():
            logger.info("🚀 Пропускаем подтверждение (--yes)")
            return True
            
        count = len(duplicates_info)
        
        print(f"\n{'='*60}")
        print(f"🎨 ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР МОДИФИКАЦИИ")
        print(f"{'='*60}")
        print(f"📁 Директория: {directory}")
        print(f"🖼️  Файлов для модификации: {count}")
        print(f"{'='*60}")
        
        # Показываем файлы которые будут модифицированы
        preview_count = min(10, count)
        print(f"\n📋 Файлы для модификации (показано {preview_count} из {count}):")
        
        for i, (file_path, _, original_path) in enumerate(duplicates_info[:preview_count]):
            print(f"  {i+1}. {file_path.name} (дубликат: {original_path.name})")
        
        if count > preview_count:
            print(f"  ... и еще {count - preview_count} файлов")
        
        print(f"\n⚠️  ВНИМАНИЕ: Операция НЕОБРАТИМО изменит содержимое {count} файлов!")
        print("   Будут применены случайные модификации:")
        print("   • Изменение яркости и контраста")
        print("   • Случайная обрезка краев")
        print("   • Добавление шума")
        print("   • Другие визуальные изменения")
        print(f"\n💾 Рекомендуется создать резервную копию директории перед операцией!")
        
        return await questionary.confirm(
            "Продолжить необратимую модификацию файлов?",
            default=False
        ).ask_async()
    
    @staticmethod
    async def confirm_modify_all_images(
        image_files: List[Path], 
        directory: Path
    ) -> bool:
        """
        Запрашивает подтверждение для модификации всех изображений.
        
        Args:
            image_files: Список всех изображений для модификации
            directory: Директория обработки
            
        Returns:
            bool: True если пользователь подтверждает операцию
        """
        if not image_files:
            return True
        
        # Проверяем флаг пропуска подтверждений
        if _should_skip_confirmation():
            logger.info("🚀 Пропускаем подтверждение (--yes)")
            return True
            
        count = len(image_files)
        
        print(f"\n{'='*60}")
        print(f"🎨 ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР УНИКАЛИЗАЦИИ ВСЕХ ИЗОБРАЖЕНИЙ")
        print(f"{'='*60}")
        print(f"📁 Директория: {directory}")
        print(f"🖼️  Всего изображений: {count}")
        print(f"{'='*60}")
        
        # Показываем файлы которые будут модифицированы
        preview_count = min(15, count)
        print(f"\n📋 Изображения для уникализации (показано {preview_count} из {count}):")
        
        for i, file_path in enumerate(image_files[:preview_count]):
            print(f"  {i+1}. {file_path.name}")
        
        if count > preview_count:
            print(f"  ... и еще {count - preview_count} файлов")
        
        print(f"\n⚠️  КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ:")
        print(f"   Эта операция НЕОБРАТИМО изменит ВСЕ {count} изображений!")
        print("   Каждый файл получит случайные модификации для уникальности:")
        print("   • Изменение яркости, контраста, насыщенности")
        print("   • Случайная обрезка краев (1-3 пикселя)")
        print("   • Добавление цифрового шума")
        print("   • Незначительные цветовые сдвиги")
        
        print(f"\n🛑 ОБЯЗАТЕЛЬНО создайте резервную копию директории!")
        print("   После выполнения операции восстановить оригиналы будет НЕВОЗМОЖНО!")
        
        # Двойное подтверждение для такой критической операции
        first_confirm = await questionary.confirm(
            f"Вы понимаете, что будет изменено {count} файлов НЕОБРАТИМО?",
            default=False
        ).ask_async()
        
        if not first_confirm:
            return False
        
        return await questionary.confirm(
            "ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ: Продолжить уникализацию всех изображений?",
            default=False
        ).ask_async()
    
    @staticmethod
    async def show_operation_preview(
        operation_name: str,
        files_affected: int,
        directory: Path,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Универсальный диалог предварительного просмотра операции.
        
        Args:
            operation_name: Название операции
            files_affected: Количество затрагиваемых файлов
            directory: Рабочая директория
            details: Дополнительные детали операции
            
        Returns:
            bool: True если пользователь подтверждает операцию
        """
        print(f"\n{'='*60}")
        print(f"🔍 ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР: {operation_name.upper()}")
        print(f"{'='*60}")
        print(f"📁 Директория: {directory}")
        print(f"📄 Затронутых файлов: {files_affected}")
        
        if details:
            for key, value in details.items():
                print(f"{key}: {value}")
        
        print(f"{'='*60}")
        
        return await questionary.confirm(
            f"Выполнить операцию '{operation_name}'?",
            default=True
        ).ask_async()


async def confirm_destructive_operation(
    operation_type: str,
    **kwargs
) -> bool:
    """
    Фабричная функция для создания диалогов подтверждения.
    
    Args:
        operation_type: Тип операции ('rename_duplicates', 'modify_duplicates', 'modify_all')
        **kwargs: Параметры для конкретного типа операции
        
    Returns:
        bool: True если операция подтверждена
    """
    try:
        if operation_type == "rename_duplicates":
            return await ConfirmationDialog.confirm_rename_duplicates(
                kwargs.get("duplicates_info", []),
                kwargs.get("directory", Path())
            )
        elif operation_type == "modify_duplicates":
            return await ConfirmationDialog.confirm_modify_duplicates(
                kwargs.get("duplicates_info", []),
                kwargs.get("directory", Path())
            )
        elif operation_type == "modify_all":
            return await ConfirmationDialog.confirm_modify_all_images(
                kwargs.get("image_files", []),
                kwargs.get("directory", Path())
            )
        else:
            logger.warning(f"Неизвестный тип операции: {operation_type}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка в диалоге подтверждения: {e}")
        return False