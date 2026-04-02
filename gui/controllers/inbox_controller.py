from service.docworkflow.InboxService import InboxService
from gui.services.request_context import RequestContext
from typing import Dict, List
from gui.services.auth_manager import AuthManager
from service.processing.DocumentProcessingService import DocumentProcessingService
from service.processing.MyWorkFlow import MyWorkFlow
import io
import config
from service.storage.StorageFactory import StorageFactory


class InboxController:
    def __init__(self, workflow: MyWorkFlow, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.workflow = workflow
        self.db = workflow.db
        self.log_manager = workflow.log_manager

    def get_user_inbox_messages(self, ctx: RequestContext) -> Dict[str, List[str]]:
        service = InboxService(self.log_manager, ctx)
        return service.get_user_inbox_messages()

    def download_file(self, ctx: RequestContext, filename: str, root_dir: str, is_personal: bool) -> io.BytesIO:
        """Отримує буфер файлу з персональної папки користувача."""
        service = InboxService(self.log_manager, ctx)
        return service.download_file(ctx.user_login if is_personal else None, filename, root_dir)

    def assign_file(self, ctx: RequestContext, filename: str, is_personal: bool, target_username: str, source_folder=None):
        """Викликається з UI для переміщення файлу."""
        service = InboxService(self.log_manager, ctx)
        source_user = ctx.user_login if is_personal else None
        service.assign_file(source_user, filename, target_username, source_folder)

    def delete_file(self, ctx:RequestContext, user_login:str, folder:str, filename: str):
        """Обробник для видалення файлу користувачем."""
        service = InboxService(self.log_manager, ctx)
        service.delete_file(user_login, folder, filename)

    def upload_root_file(self, ctx: RequestContext, filename: str, file_data: bytes):
        """Обробник для завантаження нового файлу через UI."""
        service = InboxService(self.log_manager, ctx)
        service.upload_file_to_root(filename, file_data)

    def archive_file(self, ctx, filename: str) -> bool:
        """Тільки копіює файл у щоденну папку."""
        client = StorageFactory.create_client(config.INBOX_DIR_PATH, self.log_manager)
        source_file = f"{config.INBOX_DIR_PATH}{client.get_separator()}{filename}"  # Або шлях до персональної папки

        dservice = DocumentProcessingService(self.log_manager)
        return dservice.archive_document(source_file, filename) is not None


    def process_file_to_excel(self, ctx, filename: str) -> list[str]:
        """Повна обробка: архівація + парсинг + Excel."""
        client = StorageFactory.create_client(config.INBOX_DIR_PATH, self.log_manager)
        source_file = f"{config.INBOX_DIR_PATH}{client.get_separator()}{filename}"  # Або шлях до персональної папки

        # Нам потрібен доступ до ExcelProcessor у Web-шарі
        excel_processor = self.workflow.excelProcessor
        backuper = self.workflow.backuper
        processor = DocumentProcessingService(self.log_manager, backuper, excel_processor)

        return processor.process_full_workflow(source_file, filename)

    def parse_file_for_review(self, ctx, filename: str) -> tuple[list[dict], list[str]]:
        """Бекап, архівація та повернення розпарсених даних для рев'ю в UI."""
        client = StorageFactory.create_client(config.INBOX_DIR_PATH, self.log_manager)
        source_file = f"{config.INBOX_DIR_PATH}{client.get_separator()}{filename}"

        excel_processor = self.workflow.excelProcessor
        backuper = self.workflow.backuper
        processor = DocumentProcessingService(self.log_manager, backuper, excel_processor)

        # Робимо бекап і переносимо файл в архів (як і раніше)
        processor.make_backup()
        processor.archive_document(source_file, filename)

        # Але замість process_to_excel викликаємо наш новий метод
        return processor.parse_document_only(source_file, filename)