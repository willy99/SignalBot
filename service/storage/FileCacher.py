import re
from service.storage.StorageFactory import StorageFactory
from dics.deserter_xls_dic import *
from service.processing.processors.DocProcessor import DocProcessor
from service.storage.LoggerManager import LoggerManager
import tempfile
import os
from utils.regular_expressions import extract_name

class FileCacheManager:
    def __init__(self, cache_filepath: str, log_manager):
        self.cache_filepath = cache_filepath
        self.cache_data: List[Dict] = []
        self.client = StorageFactory.create_client(cache_filepath, log_manager)

    def get_file_separator(self):
        return self.client.get_separator()

    def build_cache(self, root_folder: str, progress_callback=None):
        print(f"📡 Починаю глибоке сканування папки: {root_folder}...")
        new_cache = []
        yearly_stats = {}

        # Створюємо мок-воркфлоу один раз для всіх файлів, щоб не перевантажувати пам'ять
        # workflow = MockWorkflow()
        normalized_root = root_folder.rstrip('\\/')
        current_year = None
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


                if len(path_parts) > 3:
                    current_year = path_parts[3] if path_parts[3] and re.match(r'^\d{4}', path_parts[3]) else None
                # 3. Якщо ми знайшли файли в будь-якій підпапці цього року

                if current_year and filenames:
                    # Рахуємо тільки валідні документи
                    valid_files_count = sum(1 for f in filenames if f.lower().endswith(('.doc', '.docx', '.pdf')) and not f.startswith(('._', '~$')))

                    if valid_files_count > 0:
                        yearly_stats[current_year] = yearly_stats.get(current_year, 0) + valid_files_count
                        if progress_callback:
                            progress_callback(yearly_stats)

                if not display_path:
                    display_path = "(Коренева папка)"

                for filename in filenames:
                    print('>> processing ' + str(filename) + ' in ' + str(display_path))
                    full_path_win = f"{dirpath}\\{filename}"
                    extracted_names = []

                    # === СМАРТ-ПАРСИНГ: Обробляємо тільки Word-документи ===
                    # Ігноруємо системні файли macOS (._) та відкриті тимчасові файли Word (~$)
                    if filename.lower().endswith(('.doc', '.docx', '.pdf')) and not filename.startswith(('._', '~$')):
                        temp_local_path = None
                        try:
                            file_buffer = self.client.get_file_buffer(full_path_win)

                            ext = '.docx' if filename.lower().endswith('.docx') else '.pdf' if filename.lower().endswith('.pdf') else '.doc'
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                                temp_file.write(file_buffer.read())
                                temp_file.flush()  # ВАЖЛИВО! Примусово скидаємо дані на диск
                                temp_local_path = temp_file.name  # Отримуємо локальний шлях

                            processor = DocProcessor(LoggerManager(), temp_local_path, filename, use_ml=False)

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

            self.client.save_json(self.cache_filepath, new_cache)

        self.cache_data = new_cache
        print(f"✅ Сканування завершено! Знайдено файлів: {len(self.cache_data)}")

    def load_cache(self):
        """Завантажує індекс з файлу через абстрактний клієнт"""
        try:
            if not self.cache_data:
                with self.client:
                    # === ОНОВЛЕНО: Делегуємо читання клієнту ===
                    self.cache_data = self.client.load_json(self.cache_filepath)
                print(f"📦 Кеш файлів завантажено. Всього записів: {len(self.cache_data)}")
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

    def copy_to_local(self, remote_source_path: str, local_dest_path: str):
        """Завантажує файл з мережі в локальну папку (через клієнт)"""
        with self.client:
            self.client.copy_file(remote_source_path, local_dest_path)