from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
import config
from typing import Dict, List, Any
from gui.services.request_context import RequestContext
import io

class InboxService:
    def __init__(self, log_manager: LoggerManager, ctx: RequestContext):
        self.log_manager = log_manager
        self.logger = log_manager.get_logger()
        self.ctx = ctx

    def get_user_inbox_messages(self) -> Dict[str, List[str]]:
        """Отримує файли з кореня інбоксу та з персональної папки користувача."""
        client = StorageFactory.create_client(config.INBOX_DIR_PATH, self.log_manager)
        result = {
            'root_files': [],
            'personal_files': [],
            'outbox_files': []
        }
        try:
            with (client):
                try:
                    root_items = client.list_files(config.INBOX_DIR_PATH, silent=True, exclude_dirs=True)
                    result['root_files'] = [f for f in root_items if not f.startswith('.')]
                except Exception as e:
                    self.logger.error(f"Помилка читання кореня Inbox: {e}")

                if self.ctx.user_login:
                    user_path = f"{config.INBOX_DIR_PATH}{client.get_separator()}{self.ctx.user_login}"
                    outbox_path = f"{config.OUTBOX_DIR_PATH}{client.get_separator()}{self.ctx.user_login}"

                    try:
                        u_items = client.list_files(user_path, silent=True, exclude_dirs=False)
                        if u_items:
                            result['personal_files'] = [f for f in u_items if not f.startswith('.')]
                        u_items = client.list_files(outbox_path, silent=True, exclude_dirs=False)
                        if u_items:
                            result['outbox_files'] = [f for f in u_items if not f.startswith('.')]

                    except Exception:
                        pass

        except Exception as e:
            self.logger.error(f"Критична помилка доступу до Inbox Service: {e}")

        return result

    def download_file(self, user_login: str, filename: str, root_dir: str) -> io.BytesIO:
        """Завантажує файл з SMB та повертає його як BytesIO буфер."""
        client = StorageFactory.create_client(root_dir, self.log_manager)
        if user_login:
            target_path = f"{root_dir}{client.get_separator()}{user_login}{client.get_separator()}{filename}"
        else:
            target_path = f"{root_dir}{client.get_separator()}{filename}"

        with client:
            try:
                # get_file_buffer вже реалізований у вас в SMBFileClient
                buffer = client.get_file_buffer(target_path)
                return buffer
            except Exception as e:
                self.logger.error(f"Помилка завантаження файлу {target_path}: {e}")
                raise

    def assign_file(self, source_user: str, filename: str, target_user: str):
        """Переміщує файл до папки target_user."""
        root_dir = config.INBOX_DIR_PATH

        client = StorageFactory.create_client(root_dir, self.log_manager)
        if source_user:
            src_path = f"{root_dir}{client.get_separator()}{source_user}{client.get_separator()}{filename}"
        else:
            src_path = f"{root_dir}{client.get_separator()}{filename}"

        dest_dir = f"{root_dir}{client.get_separator()}{target_user}"
        dest_path = f"{dest_dir}{client.get_separator()}{filename}"

        with client:
            try:
                client.make_dirs(dest_dir)
                client.move_file(src_path, dest_path)
            except Exception as e:
                self.logger.error(f"Помилка призначення файлу {filename} для {target_user}: {e}")
                raise

    def delete_file(self, user_login: str, folder:str, filename: str):
        """Видаляє файл з персональної папки користувача на SMB сервері."""
        client = StorageFactory.create_client(config.INBOX_DIR_PATH, self.log_manager)
        if user_login:
            target_path = f"{folder}{client.get_separator()}{user_login}{client.get_separator()}{filename}"
        else:
            target_path = f"{folder}{client.get_separator()}{filename}"
        with client:
            try:
                # Метод remove_file вже був у вашому SMBFileClient
                client.remove_file(target_path)
                self.logger.debug(f"🗑️ Файл видалено: {target_path}")
            except Exception as e:
                self.logger.error(f"❌ Помилка видалення файлу {target_path}: {e}")
                raise

    def upload_file_to_root(self, filename: str, file_data: bytes):
        """Зберігає завантажений файл у спільну (рутову) папку Inbox."""
        buffer = io.BytesIO(file_data)
        root_dir = config.INBOX_DIR_PATH

        client = StorageFactory.create_client(root_dir, self.log_manager)
        target_path = f"{root_dir}{client.get_separator()}{filename}"

        with client:
            try:
                client.save_file_from_buffer(target_path, buffer)
                self.logger.debug(f"⬆️ Файл успішно завантажено в корінь: {target_path}")
            except Exception as e:
                self.logger.error(f"❌ Помилка завантаження файлу {target_path}: {e}")
                raise