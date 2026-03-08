from service.docworkflow.InboxService import InboxService
from gui.services.request_context import RequestContext
from typing import Dict, List
from gui.services.auth_manager import AuthManager
from service.processing.MyWorkFlow import MyWorkFlow
import io

class InboxController:
    def __init__(self, workflow: MyWorkFlow, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.workflow = workflow
        self.db = workflow.db
        self.log_manager = workflow.log_manager

    def get_user_inbox_messages(self, ctx: RequestContext) -> Dict[str, List[str]]:
        service = InboxService(self.log_manager, ctx)
        return service.get_user_inbox_messages()

    def download_personal_file(self, ctx: RequestContext, filename: str) -> io.BytesIO:
        """Отримує буфер файлу з персональної папки користувача."""
        service = InboxService(self.log_manager, ctx)
        return service.get_personal_file(ctx.user_login, filename)

    def assign_file(self, ctx: RequestContext, filename: str, is_personal: bool, target_username: str):
        """Викликається з UI для переміщення файлу."""
        service = InboxService(self.log_manager, ctx)
        source_user = ctx.user_login if is_personal else None
        service.assign_file(source_user, filename, target_username)

    def delete_file(self, ctx: RequestContext, filename: str):
        """Обробник для видалення файлу користувачем."""
        service = InboxService(self.log_manager, ctx)
        service.delete_file(ctx.user_login, filename)

    def upload_root_file(self, ctx: RequestContext, filename: str, file_data: bytes):
        """Обробник для завантаження нового файлу через UI."""
        service = InboxService(self.log_manager, ctx)
        service.upload_file_to_root(filename, file_data)