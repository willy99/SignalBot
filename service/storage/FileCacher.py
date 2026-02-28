import re
from service.storage.StorageFactory import StorageFactory
from dics.deserter_xls_dic import *
from service.processing.processors.DocProcessor import DocProcessor
from service.storage.LoggerManager import LoggerManager
import tempfile
import os

class MockWorkflow:
    """Заглушка для workflow, щоб збирати статистику без бота"""

    def __init__(self):
        self.log_manager = LoggerManager()
        self.stats = type('Stats', (), {
            'attachmentWordProcessed': 0,
            'attachmentPDFProcessed': 0,
            'doc_names': []
        })


class FileCacheManager:
    def __init__(self, cache_filepath: str, log_manager):
        self.cache_filepath = cache_filepath
        self.cache_data: List[Dict] = []
        # Спочатку створюємо клієнт
        self.client = StorageFactory.create_client(cache_filepath, log_manager)
        # Потім вантажимо кеш

    def get_file_separator(self):
        return self.client.get_separator()

    def build_cache(self, root_folder: str):
        print(f"📡 Починаю глибоке сканування папки: {root_folder}...")
        new_cache = []

        # Створюємо мок-воркфлоу один раз для всіх файлів, щоб не перевантажувати пам'ять
        workflow = MockWorkflow()
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

                if not display_path:
                    display_path = "(Коренева папка)"

                for filename in filenames:
                    print('>> processing ' + str(filename) + ' in ' + str(display_path))
                    full_path_win = f"{dirpath}\\{filename}"
                    extracted_names = []

                    # === СМАРТ-ПАРСИНГ: Обробляємо тільки Word-документи ===
                    if filename.lower().endswith(('.doc', '.docx')):
                        temp_local_path = None
                        try:
                            # 1. Читаємо файл з мережі через ваш SMBFileClient у пам'ять
                            file_buffer = self.client.get_file_buffer(full_path_win)

                            # 2. Створюємо тимчасовий локальний файл із правильним розширенням
                            ext = '.docx' if filename.lower().endswith('.docx') else '.doc'
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                                temp_file.write(file_buffer.read())
                                temp_local_path = temp_file.name  # Отримуємо локальний шлях (напр. /tmp/tmpxyz123.docx)

                            # 3. Годуємо парсеру ЛОКАЛЬНИЙ файл
                            processor = DocProcessor(workflow, temp_local_path, filename, use_ml=False)

                            # Витягуємо блок тексту з переліком осіб
                            raw_piece_3 = processor.engine.extract_text_between(
                                PATTERN_PIECE_3_START,
                                PATTERN_PIECE_3_END,
                                True
                            ) or ""

                            # Розбиваємо текст на окремі абзаци
                            persons_texts = processor.cut_into_person(raw_piece_3)

                            # Дістаємо імена
                            for person_text in persons_texts:
                                name = processor._extract_name(person_text)
                                if name:
                                    extracted_names.append(name.strip())

                        except Exception as e:
                            print(f"⚠️ Помилка парсингу імен у файлі {filename}: {e}")

                        finally:
                            # 4. ОБОВ'ЯЗКОВО прибираємо за собою: видаляємо тимчасовий файл
                            if temp_local_path and os.path.exists(temp_local_path):
                                os.remove(temp_local_path)

                    # === ФОРМУЄМО ЛЕГКИЙ КЕШ ===
                    new_cache.append({
                        'name': filename,
                        'path': display_path,
                        'names': extracted_names
                    })

            # === ОНОВЛЕНО: Делегуємо збереження клієнту ===
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
        # Розбиваємо запит по зірочках, екрануємо спецсимволи і зшиваємо назад через .*
        escaped_parts = [re.escape(part) for part in query.split('*')]
        regex_pattern = ".*".join(escaped_parts)

        try:
            compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
        except re.error:
            return []

        results = []
        for item in self.cache_data:
            # 1. Перевіряємо збіг у назві файлу
            if compiled_regex.search(item.get('name', '')):
                results.append(item)
                continue  # Якщо знайшли в назві, йдемо до наступного файлу (щоб не було дублікатів)

            # 2. Перевіряємо збіг у списку витягнутих імен
            # any() поверне True, якщо хоча б одне ім'я підходить під регулярку
            if any(compiled_regex.search(person) for person in item.get('names', [])):
                results.append(item)

        return results

    def copy_to_local(self, remote_source_path: str, local_dest_path: str):
        """Завантажує файл з мережі в локальну папку (через клієнт)"""
        with self.client:
            self.client.copy_file(remote_source_path, local_dest_path)