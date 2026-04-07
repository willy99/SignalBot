# service/processing/DocumentProcessingService.py
import logging
import os
import config
from dics.deserter_xls_dic import COLUMN_NAME
from service.processing.processors.DocProcessor import DocProcessor
from service.storage.LoggerManager import LoggerManager
from utils.utils import get_effective_date
import unicodedata
import traceback
from service.storage.StorageFactory import StorageFactory
from datetime import datetime
import tempfile

class DocumentProcessingService:
    def __init__(self, log_manager, backuper=None, excel_processor=None):
        self.logger = log_manager.get_logger()
        self.log_manager = log_manager
        self.backuper = backuper
        self.excel_processor = excel_processor
        self.fileProxy = StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, self.log_manager)

    def make_backup(self) -> bool:
        """1. Створення резервної копії бази/Excel."""
        if self.backuper:
            try:
                self.backuper.make_backup()
                return True
            except Exception as e:
                self.logger.error(f"❌ Помилка під час бекапу: {e}")
                return False
        return True  # Якщо бекапер не переданий, вважаємо, що все ОК

    def archive_document(self, source_file_path: str, original_filename: str) -> str:
        """2. Копіювання файлу у цільову (впорядковану) папку."""
        effective_date = get_effective_date()
        original_filename = unicodedata.normalize('NFC', original_filename)
        target_path = self.fileProxy.get_target_folder_path(effective_date, config.DOCUMENT_STORAGE_PATH)

        try:
            with StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, self.log_manager) as client:
                destination_file = f"{target_path}{client.separator}{original_filename}"

                if config.PROCESS_DOC:
                    client.make_dirs(target_path)
                    client.copy_file(source_file_path, destination_file)
                    self.logger.debug(f"📁 Файл впорядковано: {destination_file}")

                return destination_file
        except Exception as e:
            self.logger.error(f"❌ Помилка архівації документа: {e}")
            self.logger.debug(traceback.format_exc())
            return None

    def process_to_excel(self, source_file_path: str, original_filename: str) -> list[str]:
        """3. Розпізнавання документа та запис результатів у Excel/БД."""
        if not os.path.exists(
                source_file_path):  # Якщо це мережевий шлях, os.path.exists може брехати, але залишимо для сумісності
            self.logger.warning(f"⚠️ Шлях {source_file_path} недоступний локально. Спробуємо завантажити через клієнт.")

        local_temp_path = None
        try:
            # 1. Створюємо безпечний тимчасовий файл із правильним розширенням
            _, ext = os.path.splitext(original_filename)
            fd, local_temp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)  # Закриваємо дескриптор, нам потрібен лише шлях

            # 2. Копіюємо файл з мережі локально
            with StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, self.log_manager) as client:
                client.copy_file(source_file_path, local_temp_path)

            # 3. Передаємо ЛОКАЛЬНИЙ файл у ваш парсер!
            doc_processor = DocProcessor(self.log_manager, local_temp_path, original_filename)
            data_for_excel = doc_processor.process()
            file_parse_messages = doc_processor.check_for_errors(data_for_excel)

            if config.PROCESS_XLS and data_for_excel is not None and self.excel_processor:
                self.excel_processor.upsert_record(data_for_excel)
                self.logger.debug(f"📊 Дані з {original_filename} записано в таблицю.")

            return file_parse_messages

        except Exception as e:
            self.logger.error(f"❌ Помилка під час обробки та запису в Excel: {e}")
            self.logger.debug(traceback.format_exc())
            return False
        finally:
            # 4. Гарантоване прибирання
            if local_temp_path and os.path.exists(local_temp_path):
                try:
                    os.remove(local_temp_path)
                except Exception as cleanup_err:
                    self.logger.warning(f"🧹 Не вдалося видалити тимчасовий файл {local_temp_path}: {cleanup_err}")

    def process_full_workflow(self, source_file_path: str, original_filename: str) -> list[str]:
        """
        Метод-фасад для повного циклу: Бекап -> Архів -> Ексель.
        (Ідеально підходить для використання у Signal AttachmentHandler).
        """
        self.make_backup()
        self.archive_document(source_file_path, original_filename)
        return self.process_to_excel(source_file_path, original_filename)

    def get_daily_archive_files(self, target_date, known_names: list) -> list[dict]:
        dt = datetime.combine(target_date, datetime.min.time()).replace(hour=12)
        target_path = self.fileProxy.get_target_folder_path(dt, config.DOCUMENT_STORAGE_PATH)

        archive_list = []
        known_surnames = [name.split()[0].lower() for name in known_names if name]

        try:
            with StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, self.log_manager) as client:
                if not client.exists(target_path):
                    return []

                files = client.list_files(target_path)
                for filename in files:
                    file_path = f"{target_path}{client.separator}{filename}"
                    found_names = []

                    _, ext = os.path.splitext(filename)
                    # 💡 ОПТИМІЗАЦІЯ ШВИДКОСТІ: Ігноруємо не-документи
                    if ext.lower() not in ['.doc', '.docx', '.rtf']:
                        archive_list.append({'name': 'Не текстовий документ', 'filename': filename})
                        continue

                    fd, local_temp_path = tempfile.mkstemp(suffix=ext)
                    os.close(fd)

                    try:
                        client.copy_file(file_path, local_temp_path)
                        # log_manager = Logger Manager(logging_level=logging.ERROR)
                        doc_processor = DocProcessor(self.log_manager, local_temp_path, filename)
                        parsed_data_list = doc_processor.process()

                        if parsed_data_list:
                            found_names = [item.get(COLUMN_NAME) for item in parsed_data_list if item.get(COLUMN_NAME)]

                    except Exception as parse_err:
                        # 💡 ВИПРАВЛЕННЯ: Відловлюємо помилку конкретного файлу, щоб цикл не впав!
                        self.logger.warning(f"Не вдалося розпарсити {filename}: {parse_err}")
                    finally:
                        if os.path.exists(local_temp_path):
                            os.remove(local_temp_path)

                    # Перевіряємо на відомі імена
                    is_known = False
                    if found_names:
                        for name in found_names:
                            if name:
                                found_surname = name.split()[0].lower()
                                if any(found_surname in k_surname for k_surname in known_surnames):
                                    is_known = True
                                    break

                    if not is_known:
                        archive_list.append({
                            'name': ", ".join([n for n in found_names if n]) if found_names else 'Не вдалося розпізнати',
                            'filename': filename
                        })

        except Exception as e:
            self.logger.error(f"❌ Помилка отримання архівних файлів: {e}")
            self.logger.debug(traceback.format_exc())

        return archive_list

    def parse_document_only(self, source_file_path: str, original_filename: str) -> tuple[list[dict], list[str]]:
        """
        Тільки розпізнає документ і повертає сирі словники.
        БЕЗ запису в Excel!
        """
        if not os.path.exists(source_file_path):
            self.logger.warning(f"⚠️ Шлях {source_file_path} недоступний локально.")

        local_temp_path = None
        try:
            _, ext = os.path.splitext(original_filename)
            fd, local_temp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)

            with StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, self.log_manager) as client:
                client.copy_file(source_file_path, local_temp_path)

            doc_processor = DocProcessor(self.log_manager, local_temp_path, original_filename)
            data_for_excel = doc_processor.process()  # Це список словників
            file_parse_messages = doc_processor.check_for_errors(data_for_excel)

            return data_for_excel, file_parse_messages

        finally:
            if local_temp_path and os.path.exists(local_temp_path):
                os.remove(local_temp_path)