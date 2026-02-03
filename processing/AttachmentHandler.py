import os
import config
from processing.DocProcessor import DocProcessor
from utils.utils import get_effective_date
import shutil
import json

class AttachmentHandler:
    def __init__(self, workflow):
        self.workflow = workflow

    def handle_attachment(self, attachment_id, original_filename):
        effective_date = get_effective_date()

        # 1. Формуємо назви для кожного рівня
        year_folder = effective_date.strftime(config.FOLDER_YEAR_FORMAT)
        month_folder = effective_date.strftime(config.FOLDER_MONTH_FORMAT)
        day_folder = effective_date.strftime(config.FOLDER_DAY_FORMAT)

        # 2. Будуємо повний шлях: .../signal-data/2026/01/2026.01.28/
        target_path = os.path.join(
            config.DATA_DIR,
            year_folder,
            month_folder,
            day_folder
        )

        os.makedirs(target_path, exist_ok=True)

        source_file = os.path.join(config.SIGNAL_ATTACHMENTS_DIR, attachment_id)

        # Додаємо таймстамп для унікальності
        # unique_name = f"{int(effective_date.timestamp())}_{original_filename}"
        destination_file = os.path.join(target_path, original_filename)

        if os.path.exists(source_file):
            shutil.copy2(source_file, destination_file)

            if config.PROCESS_DOC:
                doc_processor = DocProcessor(destination_file)
                doc_processor.process_doc()
            if config.PROCESS_XLS:
                word_data = {'піб': 'КОЗАЧУК Вячеслав Вікторович', 'статус': 'СЗЧ'}
                self.workflow.excelProcessor.insert_record(word_data)
                self.workflow.excelProcessor.save()
            print(f"📁 Файл впорядковано: {destination_file}")

            return True
        else:
            print(f"❌ Файл {attachment_id} не знайдено в системній папці.")
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

        # Тут складніше: треба дочекатися відповіді від сокета саме на цей ID
        # Демон поверне JSON з полем "base64": "..."


    def get_attachment_content(self, attachment_id):
        # Шлях за замовчуванням на Mac/Linux
        base_path = os.path.expanduser("~/.local/share/signal-cli/attachments/")
        full_path = os.path.join(base_path, attachment_id)

        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                return f.read()
        return None
