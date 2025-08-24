"""
Система пользовательских подсказок и справки.
"""

from typing import List


class UserGuidance:
    """Система подсказок и справочной информации для пользователей."""

    OPERATION_TIPS = {
        "download": [
            "💡 Совет: Используйте --enable-pause-resume для больших загрузок",
            "📋 Поддерживаемые форматы: JPEG, PNG, WebP, GIF",
            "⚡ Максимальная скорость: 50 одновременных загрузок",
            "💾 Файлы сохраняются в ./images/downloaded_images/",
            "🔄 При ошибках автоматически выполняются повторные попытки",
        ],
        "find_duplicates": [
            "🔍 Поиск основан на визуальном сходстве изображений",
            "📸 Используются алгоритмы phash, dhash и average_hash",
            "📂 Дубликаты переименовываются с суффиксом '_duplicate_N'",
            "⚠️ Оригинальные файлы остаются без изменений",
            "💡 Совет: Создайте резервную копию перед обработкой",
        ],
        "uniquify": [
            "🎨 Модифицирует только найденные дубликаты",
            "🔧 Применяются: яркость, контраст, обрезка, шум",
            "⚠️ ВНИМАНИЕ: Изменения необратимы!",
            "💾 Обязательно создайте резервную копию",
            "🚀 Используйте --yes для автоматического режима",
        ],
        "uniquify_all": [
            "🎨 Модифицирует ВСЕ изображения в директории",
            "⚠️ КРИТИЧНО: Операция полностью необратима!",
            "🛑 Создайте полную резервную копию директории",
            "🎯 Идеально для SEO оптимизации изображений",
            "⏱️ Время выполнения зависит от размера изображений",
        ],
    }

    FIRST_TIME_TIPS = [
        "🎉 Добро пожаловать в Async Image Downloader!",
        "💡 Начните с команды 'download' для скачивания изображений",
        "📚 Используйте 'python main.py --help' для полной справки",
        "🔧 Все операции с дубликатами требуют подтверждения",
        "📁 Результаты сохраняются в папке ./images/",
    ]

    COMMON_ISSUES = {
        "no_images_found": {
            "message": "В указанной директории не найдено изображений",
            "solutions": [
                "📁 Проверьте правильность пути к директории",
                "🖼️ Убедитесь, что файлы имеют расширения: .jpg, .jpeg, .png, .webp, .gif",
                "👁️ Проверьте, что файлы не являются скрытыми (не начинаются с точки)",
                "📂 Попробуйте указать другую директорию",
            ],
        },
        "no_duplicates": {
            "message": "Дубликаты не найдены",
            "solutions": [
                "✅ Отлично! Все изображения уникальны",
                "🔍 Попробуйте снизить порог сходства в настройках",
                "📸 Возможно, изображения действительно различаются",
                "🎯 Используйте 'uniquify-all' для обработки всех изображений",
            ],
        },
        "download_errors": {
            "message": "Ошибки при скачивании изображений",
            "solutions": [
                "🌐 Проверьте подключение к интернету",
                "🔗 Убедитесь, что URL-адреса правильные и доступные",
                "⏰ Попробуйте увеличить время ожидания",
                "🔄 Некоторые сайты ограничивают скорость запросов",
            ],
        },
        "permission_denied": {
            "message": "Нет прав доступа к файлу или директории",
            "solutions": [
                "🔐 Запустите программу с правами администратора",
                "📝 Проверьте права доступа к директории",
                "🔓 Убедитесь, что файлы не заблокированы другими программами",
                "📁 Попробуйте выбрать другую директорию",
            ],
        },
    }

    @classmethod
    def show_operation_tips(cls, operation: str) -> None:
        """Показывает советы для конкретной операции."""
        tips = cls.OPERATION_TIPS.get(operation, [])
        if tips:
            print(f"\n💡 ПОЛЕЗНЫЕ СОВЕТЫ - {operation.upper()}")
            print("=" * 50)
            for tip in tips:
                print(f"   {tip}")
            print()

    @classmethod
    def show_welcome_message(cls) -> None:
        """Показывает приветственное сообщение для новых пользователей."""
        print("\n" + "🌟" * 20)
        for tip in cls.FIRST_TIME_TIPS:
            print(f"   {tip}")
        print("🌟" * 20 + "\n")

    @classmethod
    def show_help_for_issue(cls, issue_key: str) -> None:
        """Показывает справку по конкретной проблеме."""
        issue_info = cls.COMMON_ISSUES.get(issue_key, {})
        if issue_info:
            print(f"\n❓ ПРОБЛЕМА: {issue_info['message']}")
            print("=" * 60)
            print("💡 Возможные решения:")
            for solution in issue_info["solutions"]:
                print(f"   {solution}")
            print()

    @classmethod
    def get_operation_summary(cls, operation: str, **kwargs) -> str:
        """Возвращает краткую сводку об операции."""
        summaries = {
            "download": f"📥 Скачивание {kwargs.get('count', 0)} изображений",
            "find_duplicates": f"🔍 Поиск дубликатов в {kwargs.get('directory', 'директории')}",
            "uniquify": f"🎨 Уникализация дубликатов в {kwargs.get('directory', 'директории')}",
            "uniquify_all": f"🎨 Уникализация всех изображений в {kwargs.get('directory', 'директории')}",
        }
        return summaries.get(operation, f"⚙️ Выполнение операции: {operation}")

    @classmethod
    def show_safety_warning(cls, operation: str) -> None:
        """Показывает предупреждения о безопасности для деструктивных операций."""
        if operation in ["uniquify", "uniquify_all"]:
            print("\n" + "⚠️" * 25)
            print("   🛑 ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ О БЕЗОПАСНОСТИ 🛑")
            print("⚠️" * 25)
            print("   📁 Создайте резервную копию перед началом операции!")
            print("   🔄 Изменения изображений будут НЕОБРАТИМЫ!")
            print("   💾 Рекомендуется работать с копией директории!")
            print("⚠️" * 25 + "\n")

    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """Форматирует размер файла для пользователя."""
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} ТБ"

    @classmethod
    def format_duration(cls, seconds: float) -> str:
        """Форматирует продолжительность для пользователя."""
        if seconds < 60:
            return f"{seconds:.1f} сек"
        elif seconds < 3600:
            return f"{seconds/60:.1f} мин"
        else:
            return f"{seconds/3600:.1f} ч"

    @classmethod
    def show_performance_tips(cls, operation_time: float, items_processed: int) -> None:
        """Показывает советы по производительности."""
        if items_processed == 0:
            return

        avg_time = operation_time / items_processed

        print(f"\n📊 СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ:")
        print(f"   ⏱️ Среднее время на элемент: {avg_time:.2f} сек")
        print(f"   🚀 Обработано элементов в секунду: {1/avg_time:.1f}")

        if avg_time > 2:
            print(f"\n💡 СОВЕТЫ ДЛЯ УСКОРЕНИЯ:")
            print(f"   🖼️ Используйте изображения меньшего размера")
            print(f"   💾 Убедитесь в наличии свободного места на диске")
            print(f"   🔄 Закройте другие ресурсоемкие программы")

    @classmethod
    def get_progress_emoji(cls, progress: float) -> str:
        """Возвращает эмодзи для отображения прогресса."""
        if progress < 0.1:
            return "🟦"
        elif progress < 0.3:
            return "🟨"
        elif progress < 0.7:
            return "🟧"
        elif progress < 0.9:
            return "🟩"
        else:
            return "✅"


class InteractiveHelper:
    """Интерактивный помощник для пользователей."""

    @staticmethod
    def ask_for_confirmation_with_info(message: str, info_lines: List[str]) -> bool:
        """Запрашивает подтверждение с дополнительной информацией."""
        print(f"\n❓ {message}")
        if info_lines:
            print("ℹ️ Дополнительная информация:")
            for line in info_lines:
                print(f"   {line}")

        while True:
            response = input("\n   Продолжить? (y/n): ").lower().strip()
            if response in ["y", "yes", "да"]:
                return True
            elif response in ["n", "no", "нет"]:
                return False
            else:
                print("   Пожалуйста, введите 'y' для продолжения или 'n' для отмены")

    @staticmethod
    def show_progress_with_eta(current: int, total: int, start_time: float) -> None:
        """Показывает прогресс с оценкой времени завершения."""
        import time

        if current == 0:
            return

        elapsed = time.time() - start_time
        rate = current / elapsed
        remaining = (total - current) / rate if rate > 0 else 0

        progress = current / total
        progress_emoji = UserGuidance.get_progress_emoji(progress)

        print(
            f"   {progress_emoji} {current}/{total} "
            f"({progress*100:.1f}%) - "
            f"Осталось: {UserGuidance.format_duration(remaining)}"
        )


def show_context_sensitive_help(operation: str, error_occurred: bool = False) -> None:
    """
    Показывает контекстную справку в зависимости от ситуации.

    Args:
        operation: Название операции
        error_occurred: Произошла ли ошибка
    """
    if error_occurred:
        UserGuidance.show_help_for_issue(
            "download_errors" if operation == "download" else "permission_denied"
        )
    else:
        UserGuidance.show_operation_tips(operation)
