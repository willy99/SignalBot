import os
import config
from processing.DocProcessor import DocProcessor
from utils.utils import get_effective_date
import json
from storage.StorageFactory import StorageFactory
import unicodedata

class AttachmentHandler:
    def __init__(self, workflow):
        self.workflow = workflow
        self.fileProxy = StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH)

    def handle_attachment(self, attachment_id, original_filename):
        effective_date = get_effective_date()

        original_filename = unicodedata.normalize('NFC', original_filename)

        target_path = self.fileProxy.get_target_document_folder_path(effective_date)
        separator = "\\" if config.DOCUMENT_STORAGE_PATH.startswith("\\\\") else os.sep

        destination_file = f"{target_path}{separator}{original_filename}"

        source_file = os.path.join(config.SIGNAL_ATTACHMENTS_DIR, attachment_id)
        if not os.path.exists(source_file):
            print(f"❌ Файл {attachment_id} не знайдено в системній папці.")
            return False

        try:
            with StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH) as client:
                # Створюємо папки (локально або на SMB)
                client.make_dirs(target_path)

                client.copy_file(source_file, destination_file)

                data_for_excel = None
                file_parsed = True

                # 4. Обробка документа
                if config.PROCESS_DOC:
                    # Обробляємо ЛОКАЛЬНИЙ файл (source_file), це швидше і надійніше,
                    # ніж читати назад із мережі для парсингу.
                    doc_processor = DocProcessor(self.workflow, source_file, original_filename)
                    data_for_excel = doc_processor.process()
                    file_parsed = doc_processor.check_for_errors(data_for_excel)

                # 5. Оновлення Excel (ExcelProcessor всередині теж має використовувати фабрику)
                if config.PROCESS_XLS and data_for_excel is not None:
                    self.workflow.excelProcessor.upsert_record(data_for_excel)
                print(f"📁 Файл впорядковано: {destination_file}")

                # 6. Очищення локального вкладення Signal (опціонально)
                # self._cleanup_local_source(source_file)
                return file_parsed

        except Exception as e:
            print(f"❌ Помилка під час обробки вкладення: {e}")
        return False

    def download_attachment(self, client, attachment_id):
        payload = {
            "jsonrpc": "2.0",
            "method": "getAttachment",
            "params": {
                "id": attachment_id
            },
            "id": 2
        }
        client.sendall((json.dumps(payload) + "\n").encode())


    def get_attachment_content(self, attachment_id):
        # Шлях за замовчуванням на Mac/Linux
        base_path = os.path.expanduser(config.SIGNAL_ATTACHMENTS_DIR)
        full_path = os.path.join(base_path, attachment_id)

        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                return f.read()
        return None

    def _cleanup_local_source(self, path):
        """Видаляє тимчасовий файл вкладення Signal після обробки"""
        try:
            if os.path.exists(path):
                os.remove(path)
                # print(f"🧹 Локальний файл видалено: {path}")
        except Exception as e:
            print(f"⚠️ Не вдалося видалити локальний файл: {e}")