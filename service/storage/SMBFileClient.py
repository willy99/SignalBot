import io
import os
import smbclient
from smbclient import register_session, delete_session, open_file, makedirs
from config import NET_SERVER_IP, NET_USERNAME, NET_PASSWORD
from service.storage.FileStorageClient import FileStorageClient
from service.storage.LoggerManager import LoggerManager
import json

class SMBFileClient(FileStorageClient):
    """
    Клас для управління підключенням до мережевого диска через протокол SMB.
    Забезпечує роботу з файлами та папками за допомогою UNC шляхів.
    """

    def __init__(self, path, log_manager: LoggerManager):
        self.server_ip = NET_SERVER_IP
        self.username = NET_USERNAME
        self.password = NET_PASSWORD
        self.is_connected = False
        self.logger = log_manager.get_logger()
        self.separator = "\\" if path.startswith("\\\\") else os.sep

    def get_separator(self):
        return self.separator

    def __enter__(self):
        """Реалізація контекстного менеджера для автоматичного підключення."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Реалізація контекстного менеджера для автоматичного розриву з'єднання."""
        self.disconnect()

    def connect(self):
        """Встановлює SMB-сесію з сервером."""
        try:
            register_session(self.server_ip, username=self.username, password=self.password)
            self.is_connected = True
            # self.logger.debug(f"✅ Сесію з {self.server_ip} встановлено.")
        except Exception as e:
            self.logger.error(f"❌ Помилка підключення до SMB {self.server_ip}: {e}")
            raise

    def disconnect(self):
        """Закриває активну сесію."""
        if self.is_connected:
            try:
                delete_session(self.server_ip)
                self.is_connected = False
                # self.logger.debug(f"🔌 Сесію з {self.server_ip} закрито.")
            except Exception as e:
                self.logger.error(f"⚠️ Помилка при закритті сесії: {e}")

    def make_dirs(self, path: str):
        try:
            makedirs(path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"❌ Не вдалося створити папки на SMB: {e}")
            raise

    def get_file_buffer(self, share_path: str) -> io.BytesIO:
        try:
            with open_file(share_path, mode="rb") as f:
                return io.BytesIO(f.read())
        except Exception as e:
            raise Exception(f"️ ❌ Не вдалося прочитати файл: {e}")

    def save_file_from_buffer(self, share_path: str, buffer: io.BytesIO):
        try:
            buffer.seek(0)  # Скидаємо покажчик на початок перед читанням
            with open_file(share_path, mode="wb") as f:
                f.write(buffer.read())
            self.logger.debug(f"💾 Файл збережено на сервері: {share_path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка збереження файлу на SMB: {e}")
            raise

    def save_json(self, path: str, data: list):
        """Зберігає об'єкт Python у JSON файл на мережевому диску."""
        try:
            # open_file беремо з smbclient
            with open_file(path, mode='w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            self.logger.debug(f"💾 JSON успішно збережено: {path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка збереження JSON у {path}: {e}")
            raise

    def load_json(self, path: str) -> list:
        """Читає JSON файл з мережевого диска."""
        try:
            with open_file(path, mode='r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"❌ Помилка читання JSON з {path}: {e}")
            raise

    def copy_file(self, source_path: str, dest_path: str):
        """Копіює файл з однієї SMB-папки в іншу SMB-папку."""
        try:
            smbclient.copyfile(source_path, dest_path)
            self.logger.debug(f"📁 Файл успішно скопійовано на сервері в Outbox: {dest_path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка копіювання на сервері ({source_path} -> {dest_path}): {e}")
            raise

    def copy_file(self, source_path: str, dest_path: str):
        """Копіює (завантажує) файл з локального диска на SMB-сервер."""
        try:
            if source_path.startswith("\\\\"):
                smbclient.copyfile(source_path, dest_path)
                self.logger.debug(f"📁 Файл успішно скопійовано на сервері в: {dest_path}")
            else:
                with open(source_path, 'rb') as local_f:
                    with open_file(dest_path, mode='wb') as smb_f:
                        while True:
                            chunk = local_f.read(64 * 1024)
                            if not chunk:
                                break
                            smb_f.write(chunk)
                self.logger.debug(f"📡 Вкладення успішно скопійовано на сервер: {dest_path}")
        except Exception as e:
            self.logger.error(f"❌ Помилка копіювання файлу на сервер ({source_path} -> {dest_path}): {e}")
            raise


    def list_files(self, path: str, silent: bool = False) -> list:
        try:
            return smbclient.listdir(path)
        except Exception as e:
            if not silent:
                self.logger.error(f"❌ Помилка отримання списку файлів з SMB ({path}): {e}")
            return []

    def walk(self, path: str):
        """Реалізує обхід директорій через SMB (аналог os.walk)."""
        try:
            return smbclient.walk(path)
        except Exception as e:
            self.logger.error(f"❌ Помилка сканування папки {path}: {e}")
            return []

    def remove_file(self, path: str):
        smbclient.remove(path)

    def remove_dir(self, path: str, recursive: bool = True):
        # rmdir працює тільки для порожніх папок
        smbclient.rmdir(path, recursive=recursive)

    def close(self):
        """Явне закриття сесії (якщо не використовується 'with')."""
        self.disconnect()