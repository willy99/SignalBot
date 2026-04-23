import io
import os
import smbclient
import config
from gui.services.request_context import RequestContext
from service.storage.FileStorageClient import FileStorageClient
from service.storage.LoggerManager import LoggerManager
import json
import threading

class SMBFileClient(FileStorageClient):
    """
    Клас для управління підключенням до мережевого диска через протокол SMB.
    Забезпечує роботу з файлами та папками за допомогою UNC шляхів.
    """

    _shared_smb_semaphore = threading.BoundedSemaphore(5)

    def __init__(self, path, log_manager: LoggerManager):
        self.server_ip = config.NET_SERVER_IP
        self.username = config.NET_USERNAME
        self.password = config.NET_PASSWORD
        self.is_connected = False
        self.logger = log_manager.get_logger()
        self.separator = "\\" if path.startswith("\\\\") else os.sep
        self._smb_lock = SMBFileClient._shared_smb_semaphore

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
        """Встановлює SMB-сесію з сервером. Теж захищено семафором!"""
        with self._smb_lock:
            try:
                smbclient.register_session(self.server_ip, username=self.username, password=self.password)
                self.is_connected = True
            except Exception as e:
                error_msg = str(e).lower()
                # 💡 Захист від мертвих сесій та залишку кредитів
                if "credits" in error_msg or "connection" in error_msg:
                    self.logger.warning(f"🔄 Вичерпано кредити або зависла сесія. Робимо жорстке скидання SMB кешу...")
                    try:
                        smbclient.reset_connection_cache()
                        smbclient.register_session(self.server_ip, username=self.username, password=self.password)
                        self.is_connected = True
                        self.logger.info(f"✅ Сесію успішно відновлено після скидання.")
                        return
                    except Exception as retry_err:
                        self.logger.error(f"❌ Помилка ПОВТОРНОГО підключення до SMB: {retry_err}")

                self.logger.error(f"❌ Помилка підключення до SMB {self.server_ip}: {e}")
                raise

    def disconnect(self):
        self.is_connected = False

    def make_dirs(self, path: str):
        with self._smb_lock:
            try:
                smbclient.makedirs(path, exist_ok=True)
            except Exception as e:
                self.logger.error(f"❌ Не вдалося створити папки на SMB: {e}")
                raise

    def get_file_buffer(self, ctx: RequestContext, share_path: str) -> io.BytesIO:
        with self._smb_lock:
            try:
                with smbclient.open_file(share_path, mode="rb") as f:
                    return io.BytesIO(f.read())
            except Exception as e:
                raise Exception(f"️ ❌ Не вдалося прочитати файл: {e}")

    def save_file_from_buffer(self, share_path: str, buffer: io.BytesIO):
        with self._smb_lock:
            try:
                buffer.seek(0)  # Скидаємо покажчик на початок перед читанням
                with smbclient.open_file(share_path, mode="wb") as f:
                    f.write(buffer.read())
                self.logger.debug(f"💾 Файл збережено на сервері: {share_path}")
            except Exception as e:
                self.logger.error(f"❌ Помилка збереження файлу на SMB: {e}")
                raise

    def save_json(self, path: str, data: list):
        """Зберігає об'єкт Python у JSON файл на мережевому диску."""
        with self._smb_lock:
            try:
                # open_file беремо з smbclient
                with smbclient.open_file(path, mode='w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                self.logger.debug(f"💾 JSON успішно збережено: {path}")
            except Exception as e:
                self.logger.error(f"❌ Помилка збереження JSON у {path}: {e}")
                raise

    def load_json(self, path: str) -> list:
        """Читає JSON файл з мережевого диска."""
        with self._smb_lock:
            try:
                with smbclient.open_file(path, mode='r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"❌ Помилка читання JSON з {path}: {e}")
                raise

    def exists(self, path: str) -> bool:
        """Перевіряє, чи існує файл або папка на SMB-сервері."""
        with self._smb_lock:
            try:
                return smbclient.path.exists(path)
            except Exception as e:
                self.logger.error(f"❌ Помилка перевірки шляху SMB {path}: {e}")
                return False

    def copy_file(self, source_path: str, dest_path: str):
        """Універсальне копіювання файлів (SMB<->SMB, Local->SMB, SMB->Local, Local->Local)."""
        with self._smb_lock:
            try:
                is_source_smb = source_path.startswith("\\\\")
                is_dest_smb = dest_path.startswith("\\\\")

                if is_source_smb and is_dest_smb:
                    # 1. Мережа -> Мережа (працює швидко на боці сервера)
                    smbclient.copyfile(source_path, dest_path)
                    self.logger.debug(f"📁 Файл скопійовано (SMB -> SMB): {dest_path}")

                elif not is_source_smb and is_dest_smb:
                    # 2. Локальний комп'ютер -> Мережа
                    with open(source_path, 'rb') as local_f:
                        with smbclient.open_file(dest_path, mode='wb') as smb_f:
                            while True:
                                chunk = local_f.read(64 * 1024)
                                if not chunk:
                                    break
                                smb_f.write(chunk)
                    self.logger.debug(f"📡 Файл завантажено (Local -> SMB): {dest_path}")

                elif is_source_smb and not is_dest_smb:
                    # 3. Мережа -> Локальний комп'ютер (ОСЬ ЦЕ ВИРІШУЄ ВАШУ ПРОБЛЕМУ!)
                    with smbclient.open_file(source_path, mode='rb') as smb_f:
                        with open(dest_path, 'wb') as local_f:
                            while True:
                                chunk = smb_f.read(64 * 1024)
                                if not chunk:
                                    break
                                local_f.write(chunk)
                    self.logger.debug(f"⬇️ Файл завантажено (SMB -> Local): {dest_path}")

                else:
                    # 4. Локальний -> Локальний (про всяк випадок, щоб не впало)
                    import shutil
                    shutil.copyfile(source_path, dest_path)
                    self.logger.debug(f"📂 Файл скопійовано (Local -> Local): {dest_path}")

            except Exception as e:
                self.logger.error(f"❌ Помилка копіювання файлу на сервер ({source_path} -> {dest_path}): {e}")
                raise

    def move_file(self, source_path: str, dest_path: str):
        """Переміщує (або перейменовує) файл на SMB-сервері."""
        with self._smb_lock:
            try:
                smbclient.rename(source_path, dest_path)
                self.logger.debug(f"📁 Файл переміщено: {source_path} -> {dest_path}")
            except Exception as e:
                self.logger.error(f"❌ Помилка переміщення файлу ({source_path} -> {dest_path}): {e}")
                raise

    def list_files(self, path: str, silent: bool = False, exclude_dirs: bool = False) -> list:
        with self._smb_lock:
            try:
                files = []
                for entry in smbclient.scandir(path):
                    if entry.is_dir() and not exclude_dirs:
                        files.append(entry.name)
                    elif entry.is_file():
                        files.append(entry.name)
                return files
            except Exception as e:
                if not silent:
                    self.logger.error(f"❌ Помилка отримання списку файлів з SMB ({path}): {e}")
                return []

    def walk(self, path: str):
        """Реалізує обхід директорій через SMB (аналог os.walk)."""
        with self._smb_lock:
            try:
                return smbclient.walk(path)
            except Exception as e:
                self.logger.error(f"❌ Помилка сканування папки {path}: {e}")
                return []

    def remove_file(self, path: str):
        with self._smb_lock:
            smbclient.remove(path)

    def remove_dir(self, path: str, recursive: bool = True):
        # rmdir працює тільки для порожніх папок
        with self._smb_lock:
            smbclient.rmdir(path, recursive=recursive)

    def close(self):
        """Явне закриття сесії (якщо не використовується 'with')."""
        self.disconnect()

    def get_file_mtime(self, filepath: str) -> float:
        """Повертає час останньої модифікації файлу (UNIX timestamp)"""
        try:
            # Для smbclient використовуємо stat:
            stat_info = smbclient.stat(filepath)
            return stat_info.st_mtime
        except Exception as e:
            self.logger.warning(f"Не вдалося отримати mtime для {filepath}: {e}")
            return 0.0