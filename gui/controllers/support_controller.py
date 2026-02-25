from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from domain.person import Person
from typing import List

class SupportController:
    def __init__(self, doc_processor, worklow, auth_manager):
        self.doc_processor = doc_processor
        self.workflow = worklow
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

    def search_persons(self, ctx, query: str) -> List[Person]:
        search_filter = PersonSearchFilter(
            query=query
        )
        results = self.excel_processor.search_people(search_filter)
        return [Person.from_excel_dict(item['data']) for item in results]