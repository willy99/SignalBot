import os
import regex as re
import time
import logging
import tempfile
from typing import List, Dict
from datetime import datetime
from dics.deserter_xls_dic import PATTERN_PIECE_3_START, PATTERN_ERDR_CONDITIONS_START, PATTERN_ERDR_CONDITIONS_END, PATTERN_ERDR_CONDITIONS_NAME
from gui.services.request_context import RequestContext
from service.processing.processors.DocProcessor import DocProcessor
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory

class ErdrCacheManager:
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

    def build_cache(self, ctx: RequestContext, root_folder: str, progress_callback=None):
        print(f"📡 Починаю сканування папки ЄРДР: {root_folder}...")
        previous_level = self.log_manager.get_logger().getEffectiveLevel()
        self.log_manager.get_logger().setLevel(logging.ERROR)

        new_cache = []
        self.is_indexing = True
        self.start_time = time.time()
        self.current_stats = {}
        self.total_count = 0
        self.total_persons = 0

        normalized_root = root_folder.rstrip('\\/')

        try:
            with self.client:
                for dirpath, dirnames, filenames in self.client.walk(root_folder):

                    # На відміну від старого індексатора, ми НЕ обрізаємо dirnames.
                    # Дозволяємо йому заходити у всі вкладені папки (-02, ready, 2024 тощо)

                    display_path = re.sub(r'^\\\\[^\\]+\\[^\\]+', '', dirpath)
                    display_path = display_path.lstrip('\\')

                    # Спробуємо знайти рік у шляху для статистики (якщо є)
                    year_match = re.search(r'(202[0-9])', dirpath)
                    folder_group = year_match.group(1) if year_match else "Інше"

                    # Фільтруємо pdf та jpg
                    valid_files = [f for f in filenames if f.lower().endswith(('.doc','.docx','.pdf', '.jpg', '.jpeg', '.png')) and not f.startswith(('._', '~$'))]

                    if valid_files and progress_callback:
                        progress_callback(self.current_stats)

                    for filename in valid_files:
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

                        print(f'>> ERDR processing {filename} in {display_path}')
                        full_path_win = f"{dirpath}\\{filename}"
                        extracted_names = []
                        temp_local_path = None

                        try:
                            # 1. Завантажуємо файл у тимчасову пам'ять
                            file_buffer = self.client.get_file_buffer(None, full_path_win)

                            # Визначаємо розширення для темп-файлу
                            ext = os.path.splitext(filename)[1].lower()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                                temp_file.write(file_buffer.read())
                                temp_file.flush()
                                temp_local_path = temp_file.name

                            # 2. Викликаємо вашу кастомну функцію для ЄРДР
                            file_size = os.path.getsize(temp_local_path)
                            extracted_names = []
                            if file_size < 1048576:  # 1048576 байт = 1 МБ
                                extracted_names = self._extract_names_from_erdr(temp_local_path, filename, ext)

                        except Exception as e:
                            print(f"⚠️ Помилка парсингу ЄРДР у файлі {filename}: {e}")
                        finally:
                            if temp_local_path and os.path.exists(temp_local_path):
                                os.remove(temp_local_path)

                        # Зберігаємо результат
                        new_cache.append({
                            'name': filename,
                            'path': display_path,
                            'names': extracted_names
                        })

                        if extracted_names:
                            self.total_persons += len(extracted_names)

                        self.total_count += 1
                        self.current_stats[folder_group] = self.current_stats.get(folder_group, 0) + 1

                # Зберігаємо JSON
                self.client.save_json(self.cache_filepath, new_cache)
                self.cache_data = new_cache
                print(f"✅ Сканування ЄРДР завершено! Знайдено файлів: {len(self.cache_data)}")

        except Exception as e:
            print(f"❌ Критична помилка індексації ЄРДР: {e}")
            raise e
        finally:
            self.is_indexing = False
            self.log_manager.get_logger().setLevel(previous_level)
            self.load_cache(force=True)

    def _extract_names_from_erdr(self, local_filepath: str, filename: str, ext: str) -> List[str]:
        """
        ТУТ ВАША ЛОГІКА.
        ext буде '.pdf', '.jpg' або '.jpeg'
        Оскільки це можуть бути картинки, для .jpg вам скоріше за все знадобиться pytesseract (OCR).
        Для .pdf - PyPDF2 або pdfplumber.
        """
        extracted_names = []

        processor = DocProcessor(self.log_manager, local_filepath, filename, use_ml=False)

        raw_piece_3 = processor.engine.extract_text_between(
            PATTERN_ERDR_CONDITIONS_START,
            PATTERN_ERDR_CONDITIONS_END,
            True
        ) or ""

        if not raw_piece_3:
            print(processor.engine.get_full_text())
        matches = re.findall(PATTERN_ERDR_CONDITIONS_NAME, raw_piece_3)
        for name in matches:
            clean_name = " ".join(name.split())
            if clean_name not in extracted_names and "Збройних Сил України" not in clean_name:
                extracted_names.append(clean_name)
        print(str(extracted_names))


        return extracted_names

    def load_cache(self, force=False):

        try:
            if force or not self.cache_data:
                self.total_count = 0
                self.total_persons = 0
                self.last_indexed_date = "Ніколи"
                self.status_color = "text-gray-600"

                with self.client:
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

                print(f"📦 Кеш ЄРДР завантажено. Всього записів: {self.total_count}")
        except Exception as e:
            print(f"⚠️ Файл кешу ЄРДР не знайдено.")

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