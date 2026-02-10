import os
import shutil
import io
from storage.FileStorageClient import FileStorageClient

class LocalFileClient(FileStorageClient):

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def make_dirs(self, path: str):
        try:
            os.makedirs(path, exist_ok=True)
            # print(f"📁 Локальну директорію перевірено: {path}")
        except Exception as e:
            print(f"❌ Помилка створення локальної директорії: {e}")
            raise

    def get_file_buffer(self, path: str) -> io.BytesIO:
        try:
            with open(path, 'rb') as f:
                return io.BytesIO(f.read())
        except Exception as e:
            print(f"❌ Не вдалося прочитати локальний файл {path}: {e}")
            return None

    def save_file_from_buffer(self, path: str, buffer: io.BytesIO):
        try:
            buffer.seek(0)
            with open(path, 'wb') as f:
                f.write(buffer.read())
            print(f"💾 Файл збережено локально: {path}")
        except Exception as e:
            print(f"❌ Помилка збереження локального файлу: {e}")
            raise

    def copy_file(self, source_path: str, dest_path: str):
        try:
            shutil.copy2(source_path, dest_path)
            print(f"🚚 Файл скопійовано локально: {dest_path}")
        except Exception as e:
            print(f"❌ Помилка локального копіювання: {e}")
            raise

    def list_files(self, path: str) -> list:
        """
        Повертає список назв файлів та папок у вказаній локальній директорії.
        :param path: Шлях до локальної папки.
        """
        try:
            if os.path.exists(path) and os.path.isdir(path):
                return os.listdir(path)
            else:
                print(f"⚠️ Шлях {path} не існує або не є директорією.")
                return []
        except Exception as e:
            print(f"❌ Помилка отримання списку локальних файлів ({path}): {e}")
            return []

    def close(self):
        pass