import re
from datetime import datetime
from gui.services.request_context import RequestContext
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
from dics.deserter_xls_dic import *
from service.processing.processors.DocProcessor import DocProcessor
import tempfile
import os
from utils.regular_expressions import extract_name
import time
import logging

class FileCacheManager:
    def __init__(self, cache_filepath: str, log_manager: LoggerManager):
        self.cache_filepath = cache_filepath
        self.cache_data: List[Dict] = []
        self.client = StorageFactory.create_client(cache_filepath, log_manager)

        self.is_indexing = False
        self.current_stats = {}
        self.start_time = None
        self.total_count = 0
        self.total_persons = 0
        self.status_color = "text-gray-600"
        self.log_manager = log_manager

    def get_file_separator(self):
        return self.client.get_separator()

    def build_cache(self, ctx: RequestContext, root_folder: str, progress_callback=None):
        print(f"📡 Починаю глибоке сканування папки: {root_folder}...")
        previous_level = self.log_manager.get_logger().getEffectiveLevel()
        self.log_manager.get_logger().setLevel(logging.ERROR)
        new_cache = []
        yearly_stats = {}
        self.is_indexing = True  # Встановлюємо статус відразу
        self.start_time = time.time()
        self.current_stats = {}  # Очищуємо стару статситику
        self.total_count = 0
        self.total_persons = 0

        try:
            # Створюємо мок-воркфлоу один раз для всіх файлів, щоб не перевантажувати пам'ять
            # workflow = MockWorkflow()
            normalized_root = root_folder.rstrip('\\/')

            with self.client:
                for dirpath, dirnames, filenames in self.client.walk(root_folder):

                    # =========================================================
                    # 1. ФІЛЬТРАЦІЯ КОРЕНЕВИХ ПАПОК (Магія in-place модифікації)
                    # =========================================================
                    # Перевіряємо, чи ми зараз знаходимося в самій кореневій папці
                    if dirpath.rstrip('\\/') == normalized_root:
                        # Залишаємо в dirnames ТІЛЬКИ папки, що починаються з 4 цифр
                        # Це накаже walk() ВЗАГАЛІ НЕ ЗАХОДИТИ в інші "сміттєві" директорії!
                        dirnames[:] = [d for d in dirnames if re.match(r'^\d{4}', d)]

                    display_path = re.sub(r'^\\\\[^\\]+\\[^\\]+', '', dirpath)
                    display_path = display_path.lstrip('\\')

                    relative_path = dirpath.lower().replace(normalized_root, "").lstrip('\\/')
                    path_parts = relative_path.split('\\') if '\\' in relative_path else relative_path.split('/')
                    path_parts = [p for p in path_parts if p]
                    # print(f"DEBUG: path_parts = {path_parts}")
                    current_year = next((p for p in path_parts if re.match(r'^\d{4}', p)), None)

                    # 3. Якщо ми знайшли файли в будь-якій підпапці цього року

                    if current_year and filenames:
                        # Рахуємо тільки валідні документи
                        valid_files_count = sum(1 for f in filenames if f.lower().endswith(('.doc', '.docx', '.pdf')) and not f.startswith(('._', '~$')))
                        if valid_files_count > 0:
                            # self.current_stats[current_year] = self.current_stats.get(current_year, 0) + valid_files_count
                            # self.total_count += valid_files_count

                            if progress_callback:
                                progress_callback(self.current_stats)

                    if not display_path:
                        display_path = "(Коренева папка)"

                    for filename in filenames:
                        full_path_win = f"{dirpath}\\{filename}"

                        # =========================================================
                        # ЗАХИСТ ВІД ЗАБЛОКОВАНИХ ФАЙЛІВ ТА ВАЖКИХ ДОКУМЕНТІВ
                        # =========================================================
                        try:
                            # Перевіряємо, чи файл доступний і чи не занадто великий (> 50 МБ)
                            if self.client.get_file_size(full_path_win) > 50 * 1024 * 1024:
                                continue
                        except (OSError, PermissionError) as e:
                            # Якщо файл відкритий у Word, Windows кине PermissionError
                            print(f"⚠️ Файл {filename} зайнятий іншим процесом або недоступний. Пропускаємо.")
                            continue
                        extracted_names = []
                        print('>> processing ' + str(filename) + ' in ' + str(display_path))

                        # === СМАРТ-ПАРСИНГ: Обробляємо тільки Word-документи ===
                        # Ігноруємо системні файли macOS (._) та відкриті тимчасові файли Word (~$)
                        if filename.lower().endswith(('.doc', '.docx', '.pdf')) and not filename.startswith(('._', '~$')):
                            temp_local_path = None
                            try:
                                file_buffer = self.client.get_file_buffer(None, full_path_win)

                                ext = '.docx' if filename.lower().endswith('.docx') else '.pdf' if filename.lower().endswith('.pdf') else '.doc'
                                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                                    temp_file.write(file_buffer.read())
                                    temp_file.flush()
                                    temp_local_path = temp_file.name  # Отримуємо локальний шлях

                                processor = DocProcessor(self.log_manager, temp_local_path, filename, use_ml=False)

                                raw_piece_3 = processor.engine.extract_text_between(
                                    PATTERN_PIECE_3_START,
                                    PATTERN_PIECE_3_END,
                                    True
                                ) or ""

                                persons_texts = processor.cut_into_person(raw_piece_3)

                                for person_text in persons_texts:
                                    name = extract_name(person_text)
                                    if name:
                                        extracted_names.append(name.strip())

                            except Exception as e:
                                print(f"⚠️ Помилка парсингу імен у файлі {filename}: {e}")

                            finally:
                                if temp_local_path and os.path.exists(temp_local_path):
                                    os.remove(temp_local_path)

                        new_cache.append({
                            'name': filename,
                            'path': display_path,
                            'names': extracted_names
                        })
                        if extracted_names:
                            self.total_persons += len(extracted_names)  # Додаємо кількість знайдених прізвищ
                        self.total_count += 1
                        self.current_stats[current_year] = self.current_stats.get(current_year, 0) + 1

                self.client.save_json(self.cache_filepath, new_cache)

                self.cache_data = new_cache
                print(f"✅ Сканування завершено! Знайдено файлів: {len(self.cache_data)}")
        except Exception as e:
            print(f"❌ Критична помилка індексації: {e}")
            raise e  # Прокидаємо далі, щоб UI показав notify
        finally:
            self.is_indexing = False
            self.log_manager.get_logger().setLevel(previous_level)
            self.load_cache(force=True)

    def load_cache(self, force=False):
        """Завантажує індекс з файлу через абстрактний клієнт"""
        try:
            if force or not self.cache_data:
                self.total_count = 0
                self.total_persons = 0
                self.last_indexed_date = "Ніколи"
                self.status_color = "text-gray-600"  # дефолтний колір

                with self.client:
                    # === ОНОВЛЕНО: Делегуємо читання клієнту ===
                    self.cache_data = self.client.load_json(self.cache_filepath)
                    self.total_count = len(self.cache_data)
                    self.total_persons = sum(len(item.get('names', [])) for item in self.cache_data)
                    try:
                        if self.client.exists(self.cache_filepath):
                            mtime = self.client.get_file_mtime(self.cache_filepath)
                            diff_seconds = time.time() - mtime
                            diff_days = diff_seconds / (24 * 3600)

                            # Визначаємо колір за вашою умовою
                            if diff_days > 7:
                                self.status_color = "text-red-600 font-bold"
                            elif diff_days > 3:
                                self.status_color = "text-orange-500 font-bold"
                            else:
                                self.status_color = "text-green-600"

                            self.last_indexed_date = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
                    except Exception as e:
                        print(f"Не вдалося отримати дату файлу: {e}")
                print(f"📦 Кеш файлів завантажено. Всього записів: {self.total_count}")
        except Exception as e:
            print(f"⚠️ Файл кешу не знайдено або сталася помилка. Потрібно запустити build_cache(). Деталі: {e}")

    def search(self, query: str) -> List[Dict]:
        if not query or not self.cache_data:
            return []

        query = query.strip()
        escaped_parts = [re.escape(part) for part in query.split('*')]
        regex_pattern = ".*".join(escaped_parts)

        try:
            compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
        except re.error:
            return []

        results = []
        for item in self.cache_data:
            if compiled_regex.search(item.get('name', '')):
                results.append(item)
                continue

            if any(compiled_regex.search(person) for person in item.get('names', [])):
                results.append(item)

        return results

    def copy_to_local(self, ctx: RequestContext, remote_source_path: str, local_dest_path: str):

        """Завантажує файл з мережі в локальну папку (через клієнт)"""
        with self.client:
            self.client.copy_file(remote_source_path, local_dest_path)