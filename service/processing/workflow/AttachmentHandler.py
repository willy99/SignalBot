import os
import config
from service.processing.DocumentProcessingService import DocumentProcessingService
from utils.utils import sanitize_filename


class AttachmentHandler:
    def __init__(self, workflow):
        # Залишаємо workflow, бо його передає MyWorkFlow (Signal-бот)
        self.workflow = workflow
        self.logger = self.workflow.log_manager.get_logger()

    def handle_attachment(self, attachment_id, original_filename) -> list[str]:
        # --- БЕЗПЕКА: Санітизація імені файлу ---
        safe_original_filename = sanitize_filename(original_filename)

        if safe_original_filename != original_filename:
            self.logger.warning(f"⚠️ Підозріле ім'я файлу змінено: {original_filename} -> {safe_original_filename}")

        # 1. Знаходимо локальний файл, який завантажив Signal
        source_file = os.path.join(config.SIGNAL_ATTACHMENTS_DIR, attachment_id)
        if not os.path.exists(source_file):
            self.logger.error(f"❌ Файл {attachment_id} не знайдено в системній папці Signal.")
            return []

        # 2. Ініціалізуємо сервіс обробки
        processor_service = DocumentProcessingService(
            log_manager=self.workflow.log_manager,
            backuper=self.workflow.backuper,
            excel_processor=self.workflow.excelProcessor
        )

        # 3. Передаємо ОЧИЩЕНЕ ім'я файлу в сервіс
        # Тепер DocumentProcessingService працюватиме тільки в межах дозволених папок
        result = processor_service.process_full_workflow(source_file, safe_original_filename)

        return result