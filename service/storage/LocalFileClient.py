import os
import shutil
import io
from service.storage.FileStorageClient import FileStorageClient
from service.storage.LoggerManager import LoggerManager
import json

class LocalFileClient(FileStorageClient):

    def __init__(self, path, log_manager: LoggerManager):
        self.separator = os.sep
        self.logger = log_manager.get_logger()
        pass

    def get_separator(self):
        return self.separator

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def make_dirs(self, path: str):
        try:
            os.makedirs(path, exist_ok=True)
            # self.logger.debug(f"📁 Локальну директорію перевірено: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка створення локальної директорії: {e}")
            raise

    def get_file_buffer(self, path: str) -> io.BytesIO:
        try:
            with open(path, 'rb') as f:
                return io.BytesIO(f.read())
        except Exception as e:
            self.logger.error(f"❌ Не вдалося прочитати локальний файл {path}: {e}")
            return None

    def save_file_from_buffer(self, path: str, buffer: io.BytesIO):
        try:
            buffer.seek(0)
            with open(path, 'wb') as f:
                f.write(buffer.read())
            self.logger.debug(f"💾 Файл збережено локально: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка збереження локального файлу: {e}")
            raise

    def copy_file(self, source_path: str, dest_path: str):
        try:
            shutil.copy2(source_path, dest_path)
            self.logger.debug(f"🚚 Файл скопійовано локально: {dest_path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка локального копіювання: {e}")
            raise

    def move_file(self, source_path: str, dest_path: str):
        try:
            shutil.move(source_path, dest_path)
            self.logger.debug(f"🚚 Файл скопійовано локально: {dest_path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка локального копіювання: {e}")
            raise

    def list_files(self, path: str, silent: bool = False, exclude_dirs: bool = False) -> list:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                files = []
                for entry in os.scandir(path):
                    if entry.is_file():
                        files.append(entry.name)
                return files
            else:
                self.logger.warning(f"⚠️ Шлях {path} не існує або не є директорією.")
                return []
        except Exception as e:
            self.logger.error(f"❌ Помилка отримання списку локальних файлів ({path}): {e}")
            return []

    def remove_file(self, path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
                # self.logger.debug(f"🗑️ Файл видалено: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка видалення локального файлу: {e}")
            raise

    def remove_dir(self, path: str, recursive: bool = True):
        try:
            if os.path.exists(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
                # self.logger.debug(f"🗑️ Папку видалено: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка видалення локальної папки: {e}")
            raise

    def walk(self, path: str):
        try:
            return os.walk(path)
        except Exception as e:
            self.logger.error(f"❌ Помилка сканування локальної папки {path}: {e}")
            return []

    def save_json(self, path: str, data: list):
        try:
            with open(path, mode='w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            self.logger.debug(f"💾 JSON успішно збережено локально: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка збереження JSON локально у {path}: {e}")
            raise

    def load_json(self, path: str) -> list:
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"❌ Помилка читання JSON локально з {path}: {e}")
            raise

    def exists(self, path: str) -> bool:
        """Перевіряє, чи існує файл або папка локально."""
        try:
            return os.path.exists(path)
        except Exception as e:
            self.logger.error(f"❌ Помилка перевірки шляху {path}: {e}")
            return False

    def close(self):
        pass