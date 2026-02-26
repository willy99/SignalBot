import re
from typing import List, Dict
from service.storage.StorageFactory import StorageFactory


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
        print(f"📡 Починаю сканування папки: {root_folder}...")
        new_cache = []

        with self.client:
            for dirpath, _, filenames in self.client.walk(root_folder):

                display_path = re.sub(r'^\\\\[^\\]+\\[^\\]+', '', dirpath)
                display_path = display_path.lstrip('\\')

                if not display_path:
                    display_path = "(Коренева папка)"

                for filename in filenames:
                    path_win = f"{dirpath}\\{filename}"
                    path_mac = path_win.replace('\\', '/')
                    if path_mac.startswith('//'):
                        path_mac = 'smb:' + path_mac
                    elif not path_mac.startswith('smb://'):
                        path_mac = 'smb://' + path_mac.lstrip('/')

                    new_cache.append({
                        'name': filename,
                        'path': display_path,
                        'path_win': path_win,
                        'path_mac': path_mac
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
        escaped_parts = [re.escape(part) for part in query.split('*')]
        regex_pattern = ".*".join(escaped_parts)

        try:
            compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
        except re.error:
            return []

        return [item for item in self.cache_data if compiled_regex.search(item['name'])]

    def copy_to_local(self, remote_source_path: str, local_dest_path: str):
        """Завантажує файл з мережі в локальну папку (через клієнт)"""
        with self.client:
            self.client.copy_file(remote_source_path, local_dest_path)