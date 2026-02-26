from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from domain.person import Person
from typing import List, Optional

from service.docworkflow.DocSupportService import DocSupportService

class SupportController:
    def __init__(self, doc_processor, worklow, auth_manager):
        self.doc_processor = doc_processor
        self.workflow = worklow
        self.db = worklow.db
        self.excel_processor = worklow.excelProcessor
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def generate_support_document(self, ctx: RequestContext, city: str, supp_number: str, buffer_data: list) -> tuple[bytes, str]:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not supp_number:
            raise ValueError("Будь ласка, введіть загальний номер супроводу.")

        # Викликаємо процесор для генерації
        return self.doc_processor.generate_support_batch(city, supp_number, buffer_data)

    def search_persons(self, ctx: RequestContext, query: str) -> List[Person]:
        search_filter = PersonSearchFilter(
            query=query
        )
        results = self.excel_processor.search_people(search_filter)
        return [Person.from_excel_dict(item['data']) for item in results]

    def save_support_doc(self, ctx:RequestContext, city: str, support_number: str, buffer_data: list,
                   support_doc_id: Optional[int] = None):
        dservice = DocSupportService(self.db, ctx)
        return dservice.save_support_doc(city, support_number, buffer_data, support_doc_id)

    def get_all_drafts(self, ctx: RequestContext):
        # Викликаємо сервіс або прямо метод БД (залежно від вашої архітектури)
        dservice = DocSupportService(self.db, ctx)
        return dservice.get_all_support_docs()

    def delete_draft(self, ctx: RequestContext, draft_id: int):
        dservice = DocSupportService(self.db, ctx)
        return dservice.delete_support_doc(draft_id)
