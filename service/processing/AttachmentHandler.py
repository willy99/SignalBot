import os
import config
import json
from service.processing.DocumentProcessingService import DocumentProcessingService

class AttachmentHandler:
    def __init__(self, workflow):
        # Залишаємо workflow, бо його передає MyWorkFlow (Signal-бот)
        self.workflow = workflow
        self.logger = self.workflow.log_manager.get_logger()

    def handle_attachment(self, attachment_id, original_filename) -> list[str]:
        # 1. Знаходимо локальний файл, який завантажив Signal
        source_file = os.path.join(config.SIGNAL_ATTACHMENTS_DIR, attachment_id)
        if not os.path.exists(source_file):
            self.logger.error(f"❌ Файл {attachment_id} не знайдено в системній папці Signal.")
            return []

        # 2. Ініціалізуємо наш новий незалежний сервіс обробки
        processor_service = DocumentProcessingService(
            log_manager=self.workflow.log_manager,
            backuper=self.workflow.backuper,
            excel_processor=self.workflow.excelProcessor
        )

        # 3. Передаємо всю магію (бекапи, копіювання, парсинг, Excel) сервісу
        result = processor_service.process_full_workflow(source_file, original_filename)

        # 4. Очищення локального вкладення Signal (опціонально)
        # if result:
        #     self._cleanup_local_source(source_file)

        return result

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
        try:
            if os.path.exists(path):
                os.remove(path)
                # self.logger.debug(f"🧹 Локальний файл видалено: {path}")
        except Exception as e:
            self.logger.error(f"⚠️ Не вдалося видалити локальний файл: {e}")