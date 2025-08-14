"""
GUI интерфейс для async_image_downloader
Использует tkinter для создания графического интерфейса
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import asyncio
import sys
from pathlib import Path

from utils.logger import logger
from utils.config import IMAGE_DIR
from core.downloader import download_images_for_folder, download_images_from_file
from core.duplicates import find_duplicates, rename_duplicates_from_list


class ImageDownloaderGUI:
    """Главный класс GUI приложения"""

    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        """Настройка основного окна"""
        self.root.title("Image Downloader & Processor")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        # Адаптивная цветовая схема
        try:
            # Попытка использовать системную тему
            self.root.tk.call("source", "azure.tcl")
            self.root.tk.call("set_theme", "auto")
        except:
            # Если не получилось, используем стандартную
            pass

    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        # Создаем главный контейнер
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем систему вкладок
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Создаем вкладки (пока пустые)
        self.create_download_tab()
        self.create_duplicates_tab()
        self.create_uniquify_tab()

        # Область для логов (пока скрыта)
        self.create_log_area(main_frame)

        # Статус-бар
        self.create_status_bar()

    def create_download_tab(self):
        """Создание вкладки скачивания"""
        download_frame = ttk.Frame(self.notebook)
        self.notebook.add(download_frame, text="Скачивание")

        # Основной контейнер с отступами
        main_container = ttk.Frame(download_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Секция ввода URL
        url_section = ttk.LabelFrame(
            main_container, text="Источник изображений")
        url_section.pack(fill=tk.X, pady=(0, 15))

        # Радиокнопки для выбора источника
        self.source_var = tk.StringVar(value="urls")

        ttk.Radiobutton(
            url_section,
            text="Ввести URL вручную",
            variable=self.source_var,
            value="urls",
            command=self.on_source_change
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Radiobutton(
            url_section,
            text="Загрузить из файла",
            variable=self.source_var,
            value="file",
            command=self.on_source_change
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        # Контейнер для URL ввода
        self.url_input_frame = ttk.Frame(url_section)
        self.url_input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.url_input_frame,
                  text="URL (по одному на строку):").pack(anchor=tk.W)
        self.url_text = scrolledtext.ScrolledText(
            self.url_input_frame,
            height=6,
            wrap=tk.WORD
        )
        self.url_text.pack(fill=tk.X, pady=(5, 0))

        # Добавляем поддержку Ctrl+C, Ctrl+V, Ctrl+A
        self.setup_text_bindings(self.url_text)

        # Контейнер для выбора файла (изначально скрыт)
        self.file_input_frame = ttk.Frame(url_section)

        file_row = ttk.Frame(self.file_input_frame)
        file_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(file_row, text="Файл с URL:").pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(
            file_row, textvariable=self.file_path_var, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X,
                             expand=True, padx=(10, 5))

        ttk.Button(
            file_row,
            text="Обзор...",
            command=self.browse_file
        ).pack(side=tk.RIGHT)

        # Секция назначения
        dest_section = ttk.LabelFrame(main_container, text="Папка назначения")
        dest_section.pack(fill=tk.X, pady=(0, 15))

        dest_row = ttk.Frame(dest_section)
        dest_row.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(dest_row, text="Папка:").pack(side=tk.LEFT)
        self.dest_var = tk.StringVar(value="manual_downloads")
        ttk.Entry(dest_row, textvariable=self.dest_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5)
        )

        ttk.Button(
            dest_row,
            text="Обзор...",
            command=self.browse_destination
        ).pack(side=tk.RIGHT)

        # Дополнительные настройки
        settings_section = ttk.LabelFrame(main_container, text="Настройки")
        settings_section.pack(fill=tk.X, pady=(0, 15))

        settings_row = ttk.Frame(settings_section)
        settings_row.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(settings_row, text="Начальный индекс:").pack(side=tk.LEFT)
        self.start_index_var = tk.StringVar(value="1000")
        start_index_entry = ttk.Entry(
            settings_row, textvariable=self.start_index_var, width=10)
        start_index_entry.pack(side=tk.LEFT, padx=(10, 0))

        # Кнопки управления
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.download_btn = ttk.Button(
            button_frame,
            text="Начать скачивание",
            command=self.start_download
        )
        self.download_btn.pack(side=tk.LEFT)

        ttk.Button(
            button_frame,
            text="Открыть папку",
            command=self.open_destination_folder
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Прогресс-бар
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_container,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))

        # Инициализация состояния
        self.on_source_change()

    def setup_text_bindings(self, text_widget):
        """Настройка горячих клавиш для текстовых полей"""
        # Ctrl+A - выделить все
        text_widget.bind('<Control-a>', lambda e: self.select_all(text_widget))
        text_widget.bind('<Control-A>', lambda e: self.select_all(text_widget))
        
        # Ctrl+C - копировать
        text_widget.bind('<Control-c>', lambda e: self.copy_text(text_widget))
        text_widget.bind('<Control-C>', lambda e: self.copy_text(text_widget))
        
        # Ctrl+V - вставить
        text_widget.bind('<Control-v>', lambda e: self.paste_text(text_widget))
        text_widget.bind('<Control-V>', lambda e: self.paste_text(text_widget))
        
        # Ctrl+X - вырезать
        text_widget.bind('<Control-x>', lambda e: self.cut_text(text_widget))
        text_widget.bind('<Control-X>', lambda e: self.cut_text(text_widget))
        
        # Правый клик - контекстное меню
        text_widget.bind('<Button-3>', lambda e: self.show_context_menu(e, text_widget))

    def select_all(self, text_widget):
        """Выделить весь текст"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        return 'break'

    def copy_text(self, text_widget):
        """Копировать выделенный текст"""
        try:
            text = text_widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            pass  # Нет выделенного текста
        return 'break'

    def paste_text(self, text_widget):
        """Вставить текст из буфера обмена"""
        try:
            text = self.root.clipboard_get()
            if text_widget.tag_ranges(tk.SEL):
                text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.insert(tk.INSERT, text)
        except tk.TclError:
            pass  # Буфер обмена пуст
        return 'break'

    def cut_text(self, text_widget):
        """Вырезать выделенный текст"""
        try:
            text = text_widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass  # Нет выделенного текста
        return 'break'

    def show_context_menu(self, event, text_widget):
        """Показать контекстное меню"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(
            label="Вырезать", command=lambda: self.cut_text(text_widget))
        context_menu.add_command(
            label="Копировать", command=lambda: self.copy_text(text_widget))
        context_menu.add_command(
            label="Вставить", command=lambda: self.paste_text(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Выделить все",
                                 command=lambda: self.select_all(text_widget))

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def create_duplicates_tab(self):
        """Создание вкладки поиска дубликатов"""
        duplicates_frame = ttk.Frame(self.notebook)
        self.notebook.add(duplicates_frame, text="Дубликаты")
        
        # Основной контейнер с отступами
        main_container = ttk.Frame(duplicates_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Секция выбора папки
        folder_section = ttk.LabelFrame(main_container, text="Папка для поиска дубликатов")
        folder_section.pack(fill=tk.X, pady=(0, 15))
        
        folder_row = ttk.Frame(folder_section)
        folder_row.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(folder_row, text="Папка:").pack(side=tk.LEFT)
        self.duplicates_folder_var = tk.StringVar()
        self.duplicates_folder_entry = ttk.Entry(
            folder_row, 
            textvariable=self.duplicates_folder_var,
            state="readonly"
        )
        self.duplicates_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        
        ttk.Button(
            folder_row, 
            text="Обзор...", 
            command=self.browse_duplicates_folder
        ).pack(side=tk.RIGHT)
        
        # Кнопки управления
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.find_duplicates_btn = ttk.Button(
            button_frame, 
            text="Найти дубликаты", 
            command=self.find_duplicates
        )
        self.find_duplicates_btn.pack(side=tk.LEFT)
        
        self.rename_duplicates_btn = ttk.Button(
            button_frame, 
            text="Переименовать дубликаты", 
            command=self.rename_duplicates,
            state="disabled"
        )
        self.rename_duplicates_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            button_frame, 
            text="Открыть папку", 
            command=self.open_duplicates_folder
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Секция результатов
        results_section = ttk.LabelFrame(main_container, text="Найденные дубликаты")
        results_section.pack(fill=tk.BOTH, expand=True)
        
        # Создаем Treeview для отображения дубликатов
        columns = ("original", "duplicate", "similarity")
        self.duplicates_tree = ttk.Treeview(results_section, columns=columns, show="headings", height=10)
        
        # Настраиваем заголовки
        self.duplicates_tree.heading("original", text="Оригинал")
        self.duplicates_tree.heading("duplicate", text="Дубликат")
        self.duplicates_tree.heading("similarity", text="Сходство")
        
        # Настраиваем ширину колонок
        self.duplicates_tree.column("original", width=200)
        self.duplicates_tree.column("duplicate", width=200)
        self.duplicates_tree.column("similarity", width=100)
        
        # Добавляем скроллбар
        duplicates_scrollbar = ttk.Scrollbar(results_section, orient=tk.VERTICAL, command=self.duplicates_tree.yview)
        self.duplicates_tree.configure(yscrollcommand=duplicates_scrollbar.set)
        
        # Размещаем элементы
        self.duplicates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        duplicates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Переменная для хранения найденных дубликатов
        self.found_duplicates = []

    def create_uniquify_tab(self):
        """Создание вкладки уникализации"""
        uniquify_frame = ttk.Frame(self.notebook)
        self.notebook.add(uniquify_frame, text="Уникализация")

        # Временная заглушка
        ttk.Label(uniquify_frame,
                  text="Вкладка уникализации - в разработке").pack(pady=20)

    def create_log_area(self, parent):
        """Создание области для логов"""
        # Контейнер для логов (изначально скрыт)
        self.log_frame = ttk.LabelFrame(parent, text="Логи операций")

        # Текстовое поле для логов
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            height=8,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопка показать/скрыть логи
        self.log_toggle_btn = ttk.Button(
            parent,
            text="Показать логи",
            command=self.toggle_logs
        )
        self.log_toggle_btn.pack(pady=(5, 0))

        self.logs_visible = False

    def create_status_bar(self):
        """Создание статус-бара"""
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_logs(self):
        """Показать/скрыть область логов"""
        if self.logs_visible:
            self.log_frame.pack_forget()
            self.log_toggle_btn.config(text="Показать логи")
            self.logs_visible = False
        else:
            self.log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            self.log_toggle_btn.config(text="Скрыть логи")
            self.logs_visible = True

    def add_log_message(self, message):
        """Добавить сообщение в лог"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, status):
        """Обновить статус-бар"""
        self.status_var.set(status)
        self.root.update_idletasks()

    def on_source_change(self):
        """Обработка изменения источника URL"""
        if self.source_var.get() == "urls":
            self.url_input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            self.file_input_frame.pack_forget()
        else:
            self.url_input_frame.pack_forget()
            self.file_input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    def browse_file(self):
        """Выбор файла с URL"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с URL",
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )
        if filename:
            self.file_path_var.set(filename)

    def browse_destination(self):
        """Выбор папки назначения"""
        folder = filedialog.askdirectory(
            title="Выберите папку для сохранения изображений"
        )
        if folder:
            # Получаем только имя папки, а не полный путь
            folder_name = Path(folder).name
            self.dest_var.set(folder_name)

    def open_destination_folder(self):
        """Открыть папку назначения в проводнике"""
        import subprocess
        import os

        dest_path = Path(IMAGE_DIR) / self.dest_var.get()

        if dest_path.exists():
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', str(dest_path)])
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open' if sys.platform ==
                               'darwin' else 'xdg-open', str(dest_path)])
        else:
            messagebox.showwarning(
                "Предупреждение", f"Папка {dest_path} не существует")

    def start_download(self):
        """Начать процесс скачивания"""
        # Валидация входных данных
        if self.source_var.get() == "urls":
            urls_text = self.url_text.get("1.0", tk.END).strip()
            if not urls_text:
                messagebox.showerror("Ошибка", "Введите хотя бы один URL")
                return
            urls = [url.strip()
                    for url in urls_text.split('\n') if url.strip()]
        else:
            file_path = self.file_path_var.get()
            if not file_path:
                messagebox.showerror("Ошибка", "Выберите файл с URL")
                return
            if not Path(file_path).exists():
                messagebox.showerror("Ошибка", "Выбранный файл не существует")
                return

        try:
            start_index = int(self.start_index_var.get())
        except ValueError:
            messagebox.showerror(
                "Ошибка", "Начальный индекс должен быть числом")
            return

        dest_folder = self.dest_var.get().strip()
        if not dest_folder:
            messagebox.showerror("Ошибка", "Укажите папку назначения")
            return

        # Запуск скачивания в отдельном потоке
        self.download_btn.config(state="disabled", text="Скачивание...")
        self.progress_var.set(0)
        
        self.add_log_message("Начало скачивания...")
        self.update_status("Скачивание изображений...")
        
        # Запуск асинхронного скачивания в отдельном потоке
        download_thread = threading.Thread(
            target=self.run_download_async,
            args=(self.source_var.get(), urls if self.source_var.get() == "urls" else file_path, dest_folder, start_index),
            daemon=True
        )
        download_thread.start()

    def run_download_async(self, source_type, data, dest_folder, start_index):
        """Запуск асинхронного скачивания в отдельном потоке"""
        try:
            # Создаем новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if source_type == "urls":
                # Скачивание из списка URL
                coro = download_images_for_folder(dest_folder, data, start_index)
            else:
                # Скачивание из файла
                coro = download_images_from_file(Path(data), start_index)
            
            # Запускаем корутину
            loop.run_until_complete(coro)
            
            # Уведомляем GUI о завершении
            self.root.after(0, lambda: self.download_complete(True, None))
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании: {e}")
            # Уведомляем GUI об ошибке
            self.root.after(0, lambda: self.download_complete(False, str(e)))
        finally:
            loop.close()

    def download_complete(self, success=True, error_message=None):
        """Завершение скачивания"""
        self.download_btn.config(state="normal", text="Начать скачивание")
        self.progress_var.set(100 if success else 0)
        
        if success:
            self.add_log_message("Скачивание завершено успешно!")
            self.update_status("Готов к работе")
            messagebox.showinfo("Успех", "Скачивание завершено!")
        else:
            self.add_log_message(f"Ошибка скачивания: {error_message}")
            self.update_status("Ошибка скачивания")
            messagebox.showerror("Ошибка", f"Ошибка при скачивании:\n{error_message}")

    def browse_duplicates_folder(self):
        """Выбор папки для поиска дубликатов"""
        folder = filedialog.askdirectory(
            title="Выберите папку для поиска дубликатов",
            initialdir=IMAGE_DIR
        )
        if folder:
            self.duplicates_folder_var.set(folder)
            
    def open_duplicates_folder(self):
        """Открыть папку с дубликатами в проводнике"""
        import subprocess
        import os
        
        folder_path = self.duplicates_folder_var.get()
        
        if folder_path and Path(folder_path).exists():
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', folder_path])
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder_path])
        else:
            messagebox.showwarning("Предупреждение", "Выберите существующую папку")
            
    def find_duplicates(self):
        """Найти дубликаты в выбранной папке"""
        folder_path = self.duplicates_folder_var.get()
        
        if not folder_path:
            messagebox.showerror("Ошибка", "Выберите папку для поиска")
            return
            
        if not Path(folder_path).exists():
            messagebox.showerror("Ошибка", "Выбранная папка не существует")
            return
            
        # Очищаем предыдущие результаты
        for item in self.duplicates_tree.get_children():
            self.duplicates_tree.delete(item)
        self.found_duplicates = []
        
        # Запуск поиска в отдельном потоке
        self.find_duplicates_btn.config(state="disabled", text="Поиск...")
        self.rename_duplicates_btn.config(state="disabled")
        
        self.add_log_message(f"Начало поиска дубликатов в папке: {folder_path}")
        self.update_status("Поиск дубликатов...")
        
        # Запуск поиска дубликатов в отдельном потоке
        search_thread = threading.Thread(
            target=self.run_find_duplicates_async,
            args=(Path(folder_path),),
            daemon=True
        )
        search_thread.start()
        
    def run_find_duplicates_async(self, folder_path):
        """Запуск асинхронного поиска дубликатов в отдельном потоке"""
        try:
            # Создаем новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем поиск дубликатов (только поиск, без переименования)
            duplicates_list = loop.run_until_complete(find_duplicates(folder_path))
            
            # Уведомляем GUI о завершении с результатами
            self.root.after(0, lambda: self.find_duplicates_complete(True, None, duplicates_list))
            
        except Exception as e:
            logger.error(f"Ошибка при поиске дубликатов: {e}")
            # Уведомляем GUI об ошибке
            self.root.after(0, lambda: self.find_duplicates_complete(False, str(e), []))
        finally:
            loop.close()

    def find_duplicates_complete(self, success=True, error_message=None, duplicates_list=None):
        """Завершение поиска дубликатов"""
        self.find_duplicates_btn.config(state="normal", text="Найти дубликаты")
        
        if success and duplicates_list is not None:
            self.found_duplicates = duplicates_list
            
            # Очищаем таблицу
            for item in self.duplicates_tree.get_children():
                self.duplicates_tree.delete(item)
            
            # Заполняем таблицу найденными дубликатами
            for duplicate_path, hash_tuple, original_path in duplicates_list:
                # Показываем только имена файлов для читаемости
                original_name = original_path.name
                duplicate_name = duplicate_path.name
                similarity = "Высокое"  # Можно добавить расчет процента сходства
                
                self.duplicates_tree.insert("", "end", values=(original_name, duplicate_name, similarity))
            
            # Обновляем статус и логи
            count = len(duplicates_list)
            self.add_log_message(f"Поиск завершен. Найдено {count} дубликатов")
            self.update_status(f"Найдено {count} дубликатов")
            
            # Активируем кнопку переименования если есть дубликаты
            if count > 0:
                self.rename_duplicates_btn.config(state="normal")
            else:
                self.rename_duplicates_btn.config(state="disabled")
                
        else:
            self.add_log_message(f"Ошибка поиска дубликатов: {error_message}")
            self.update_status("Ошибка поиска")
            messagebox.showerror("Ошибка", f"Ошибка при поиске дубликатов:\n{error_message}")
            
    def rename_duplicates(self):
        """Переименовать найденные дубликаты"""
        if not self.found_duplicates:
            messagebox.showwarning("Предупреждение", "Сначала найдите дубликаты")
            return
            
        result = messagebox.askyesno(
            "Подтверждение", 
            f"Переименовать {len(self.found_duplicates)} дубликатов?"
        )
        
        if result:
            self.rename_duplicates_btn.config(state="disabled", text="Переименование...")
            self.add_log_message("Начало переименования дубликатов...")
            self.update_status("Переименование дубликатов...")
            
            # Запуск переименования в отдельном потоке
            rename_thread = threading.Thread(
                target=self.run_rename_duplicates_async,
                args=(self.found_duplicates,),
                daemon=True
            )
            rename_thread.start()
    
    def run_rename_duplicates_async(self, duplicates_list):
        """Запуск асинхронного переименования дубликатов в отдельном потоке"""
        try:
            # Создаем новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем переименование дубликатов
            renamed_count = loop.run_until_complete(rename_duplicates_from_list(duplicates_list))
            
            # Уведомляем GUI о завершении
            self.root.after(0, lambda: self.rename_duplicates_complete(True, None, renamed_count))
            
        except Exception as e:
            logger.error(f"Ошибка при переименовании дубликатов: {e}")
            # Уведомляем GUI об ошибке
            self.root.after(0, lambda: self.rename_duplicates_complete(False, str(e), 0))
        finally:
            loop.close()
            
    def rename_duplicates_complete(self, success=True, error_message=None, renamed_count=0):
        """Завершение переименования дубликатов"""
        self.rename_duplicates_btn.config(state="disabled", text="Переименовать дубликаты")
        
        if success:
            self.add_log_message(f"Переименование завершено! Переименовано {renamed_count} файлов")
            self.update_status("Готов к работе")
            messagebox.showinfo("Успех", f"Переименовано {renamed_count} дубликатов!")
            
            # Очищаем список и таблицу, так как дубликаты уже переименованы
            self.found_duplicates = []
            for item in self.duplicates_tree.get_children():
                self.duplicates_tree.delete(item)
        else:
            self.add_log_message(f"Ошибка переименования: {error_message}")
            self.update_status("Ошибка переименования")
            messagebox.showerror("Ошибка", f"Ошибка при переименовании:\n{error_message}")
            self.rename_duplicates_btn.config(state="normal", text="Переименовать дубликаты")

    def run(self):
        """Запуск GUI приложения"""
        logger.info("Запуск GUI интерфейса")
        self.root.mainloop()


def run_gui():
    """Функция для запуска GUI из main.py"""
    app = ImageDownloaderGUI()
    app.run()


if __name__ == "__main__":
    run_gui()
