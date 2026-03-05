import os
import io
import config
from service.storage.StorageFactory import StorageFactory
from datetime import datetime, timedelta
import zipfile
from service.storage.LoggerManager import LoggerManager

class BackupData:
    def __init__(self, log_manager: LoggerManager):
        # Шлях до робочого файлу Excel
        self.source_file = config.DESERTER_XLSX_FILE_PATH
        # Базовий шлях для бекапів (тепер беремо з config)
        self.base_backup_path = config.BACKUP_STORAGE_PATH
        self.log_manager = log_manager
        self.logger = self.log_manager.get_logger()

    def make_backup(self) -> str:
        effective_date = datetime.now().date()

        with StorageFactory.create_client(self.base_backup_path, self.log_manager) as client:
            target_path = client.get_target_folder_path(effective_date, self.base_backup_path)

            source_file_name = os.path.basename(self.source_file)
            backup_file_name = f"{effective_date.strftime('%Y-%m-%d')}_{source_file_name}"

            # Назва архіву тепер .zip
            backup_zip_name = f"{effective_date.strftime('%Y-%m-%d')}_{source_file_name}.zip"

            separator = client.separator
            destination_zip_path = f"{target_path.rstrip(separator)}{separator}{backup_zip_name}"

            # 1. ПЕРЕВИЗНАЧАЄМО ПЕРЕВІРКУ:
            # Якщо ми не можемо отримати список файлів, значить папки немає -> бекапу точно немає
            try:
                existing_files = client.list_files(target_path, silent=True)
                if backup_zip_name in existing_files:
                    self.logger.debug(f"--- ℹ️ Backup за сьогодні вже існує.")
                    return destination_zip_path
            except Exception:
                # Папки не існує (Error 2/0xc000003a) — це нормально для першого запуску
                self.logger.debug(f"--- 📂 Папка дня ще не створена, готуємо новий дамп...")

            # 2. СТВОРЮЄМО ПАПКУ ТА КОПІЮЄМО
            try:
                if not os.path.exists(self.source_file):
                    self.logger.error(f"--- ❌ Помилка: Файл {self.source_file} не знайдено.")
                    return ""

                # Створюємо ZIP у пам'яті
                zip_buffer = io.BytesIO()
                log_path = self.log_manager.get_log_path()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    # Додаємо файл в архів (arcname - це ім'я всередині архіву)
                    if os.path.exists(self.source_file):
                        zip_file.write(self.source_file, arcname=source_file_name)
                    # Додаємо Лог
                    if os.path.exists(log_path):
                        zip_file.write(log_path, arcname=os.path.basename(log_path))

                    # 3. ДОДАЄМО БАЗУ ДАНИХ ТА ЇЇ СУПУТНІ ФАЙЛИ
                    db_path = config.DB_NAME

                    # Формуємо список всіх необхідних файлів БД
                    db_files_to_backup = [
                        db_path,  # bot_data.db
                        f"{db_path}-wal",  # bot_data.db-wal
                        f"{db_path}-shm"  # bot_data.db-shm
                    ]

                    # Додаємо файл проекту DB Browser (.sqbpro), якщо розширення .db
                    if db_path.endswith('.db'):
                        db_files_to_backup.append(db_path.replace('.db', '.sqbpro'))

                    # Проходимо по списку і додаємо в архів ті, що існують
                    for db_file in db_files_to_backup:
                        if os.path.exists(db_file):
                            # arcname кладе файл в корінь архіву з його оригінальним ім'ям
                            zip_file.write(db_file, arcname=os.path.basename(db_file))

                # Тепер створюємо папки (smb_client.makedirs працює чисто)
                client.make_dirs(target_path)

                # Копіюємо
                # Зберігаємо буфер архіву в сховище
                client.save_file_from_buffer(destination_zip_path, zip_buffer)

                # 4. ОЧИЩЕННЯ ЛОГУ
                # Робимо це тільки після успішного збереження архіву
                self.log_manager.clear_log()

                self.logger.debug(f"--- ✅ Створено щоденний дамп")
                return destination_zip_path

            except Exception as e:
                self.logger.error(f"--- ❌ Критична помилка під час копіювання: {e}")
                return ""

    def _check_remote_dir_exists(self, client, path):
        """Допоміжна перевірка для SMB клієнта, якщо os.path.exists не працює з UNC."""
        try:
            client.list_files(path, silent=True)
            return True
        except:
            return False

    def cleanupOldBackups(self, n_days: int):
        """Видаляє папки бекапів, які старіші за n_days."""
        self.logger.debug(f"--- 🧹 Очищення бекапів старіше за {n_days} днів...")

        limit_date = datetime.now() - timedelta(days=n_days)

        with StorageFactory.create_client(self.base_backup_path, self.log_manager) as client:
            try:
                # 1. Отримуємо список років
                years = client.list_files(self.base_backup_path, silent=True)
                for year in years:
                    year_path = f"{self.base_backup_path.rstrip(client.separator)}{client.separator}{year}"

                    # 2. Отримуємо місяці
                    months = client.list_files(year_path, silent=True)
                    for month in months:
                        month_path = f"{year_path}{client.separator}{month}"

                        # 3. Отримуємо дні (папки типу 15.02.2026)
                        days = client.list_files(month_path, silent=True)
                        for day_folder in days:
                            day_path = f"{month_path}{client.separator}{day_folder}"

                            # Спробуємо розпарсити дату з назви папки (якщо формат 15.02.2026)
                            try:
                                # Формат має збігатися з вашим config.FOLDER_DAY_FORMAT
                                folder_date = datetime.strptime(day_folder, config.FOLDER_DAY_FORMAT)

                                if folder_date < limit_date:
                                    self._delete_dir_recursive(client, day_path)
                                    self.logger.debug(f"--- 🗑️ Видалено застарілий бекап: {day_path}")
                            except ValueError:
                                # Якщо папка має інший формат назви — ігноруємо
                                continue
            except Exception as e:
                self.logger.warning(f"⚠️ Помилка під час очищення старіх бекапів: {e}")

    def _delete_dir_recursive(self, client, path: str):
        """Рекурсивне видалення папки через клієнт."""
        # У SMBFileClient треба буде додати методи для видалення файлів та папок
        # Наразі, якщо це SMB, можна використати smbclient.rmdir / remove
        import smbclient
        try:
            # Для SMB:
            if path.startswith("\\\\"):
                # Спочатку видаляємо файли всередині
                files = client.list_files(path, silent=True)
                for f in files:
                    smbclient.remove(f"{path}{client.separator}{f}")
                # Потім саму папку
                smbclient.rmdir(path)
            else:
                # Для локального диска:
                import shutil
                shutil.rmtree(path)
        except Exception as e:
            self.logger.error(f"❌ Не вдалося видалити {path}: {e}")