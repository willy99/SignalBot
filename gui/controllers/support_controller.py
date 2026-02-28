from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from domain.person import Person
from typing import List, Optional, Dict, Any
from service.docworkflow.DocSupportService import DocSupportService
from gui.controllers.person_controller import PersonController
from utils.utils import get_person_key_from_str
from dics.deserter_xls_dic import COLUMN_INCREMEMTAL

class SupportController:
    def __init__(self, doc_processor, worklow, auth_manager):
        self.doc_processor = doc_processor
        self.workflow = worklow
        self.db = worklow.db
        self.excel_processor = worklow.excelProcessor
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def generate_support_document(self, ctx: RequestContext, city: str, supp_number: str, supp_date: str, buffer_data: list) -> tuple[bytes, str]:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not supp_number:
            raise ValueError("Будь ласка, введіть загальний номер супроводу.")

        # Викликаємо процесор для генерації
        return self.doc_processor.generate_support_batch(city, supp_number, supp_date, buffer_data)

    def generate_logs(self, ctx: RequestContext, city: str, supp_number: str, supp_date: str, buffer_data: list) -> str:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))
        log_text = self.doc_processor.generate_support_logs(city, supp_number, supp_date, buffer_data)
        print(str(log_text))
        return log_text

    def search_persons(self, ctx: RequestContext, query: str) -> List[Person]:
        search_filter = PersonSearchFilter(
            query=query
        )
        results = self.excel_processor.search_people(search_filter)
        return [Person.from_excel_dict(item['data']) for item in results]


    # методи для list view

    def save_support_doc(self, ctx:RequestContext, city: str, support_number: str, support_date, buffer_data: list,
                   draft_id: Optional[int] = None):
        self.logger.debug('UI:' + ctx.user_name + ': Запис змін для пакету супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)
        return dservice.save_support_doc(city, support_number, support_date, buffer_data, draft_id)

    def get_all_drafts(self, ctx: RequestContext):
        dservice = DocSupportService(self.db, ctx)
        return dservice.get_all_support_docs()

    def delete_draft(self, ctx: RequestContext, draft_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)
        return dservice.delete_support_doc(draft_id)

    def get_support_doc_by_id(self,ctx: RequestContext, draft_id: int) -> Optional[Dict[str, Any]]:
        self.logger.debug('UI:' + ctx.user_name + ': Дістаємо пакет супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)
        return dservice.get_support_doc_by_id(draft_id)

    def mark_as_completed(self, ctx: RequestContext, person_ctrl: PersonController, draft_id: int) -> bool:
        self.logger.debug(f'UI:{ctx.user_name}: Помічаємо комплект супроводів як COMPLETED: {draft_id}')

        draft = self.get_support_doc_by_id(ctx, draft_id)
        if not draft:
            raise ValueError(f"Чернетку №{draft_id} не знайдено!")

        support_number = draft.get('support_number')
        support_date = draft.get('support_date')
        payload = draft.get('payload', [])

        persons_to_update = []
        for doc in payload:

            row_key = get_person_key_from_str(doc.get('id_number'))
            found_person_data = person_ctrl.find_person(ctx, row_key)

            if not found_person_data:
                self.logger.warning(
                    f"Пропущено: не знайдено людину за ключем {row_key}")
                continue

            person_dict = found_person_data.get('data', {})
            logical_id = person_dict.get(COLUMN_INCREMEMTAL)

            print(f'Знайдено логічний ID: {logical_id}')

            if logical_id is not None:
                # Тепер ми передаємо правильний ID, за яким процесор зможе знайти рядок
                p = Person(
                    id=logical_id,
                    dbr_date=support_date,
                    dbr_num=support_number
                )
                persons_to_update.append(p)

        if persons_to_update:
            success = person_ctrl.save_persons(ctx, persons_to_update, paint_color="E2EFDA", partial_update=True)
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        dservice = DocSupportService(self.db, ctx)
        return dservice.mark_as_completed(draft_id)
