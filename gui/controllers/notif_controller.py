from domain.person_filter import PersonSearchFilter
from service.docworkflow.NotifService import NotifService
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from utils.utils import get_person_key_from_str
from domain.person import Person
from dics.deserter_xls_dic import *
from config import EXCEL_LIGHT_GRAY_COLOR


class NotifController:
    def __init__(self, doc_templator: DocTemplator, workflow:MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.excel_processor = workflow.excelProcessor
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()
        self.doc_templator = doc_templator


    def get_all_drafts(self, ctx: RequestContext):
        dservice = NotifService(self.db, ctx)
        return dservice.get_all_docs()

    def save_doc(self, ctx: RequestContext, region, out_number: str, out_date: str, payload: list,
                   doc_id: int = None) -> int:
        service = NotifService(self.db, ctx)
        return service.save_doc(region, out_number, out_date, payload, doc_id)

    def delete_doc(self, ctx: RequestContext, doc_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет супроводів: ' + str(doc_id))
        dservice = NotifService(self.db, ctx)
        return dservice.delete_doc(doc_id)

    def get_doc_by_id(self, ctx: RequestContext, doc_id: int) -> dict:
        service = NotifService(self.db, ctx)
        return service.get_doc_by_id(doc_id)

    def generate_document(self, ctx: RequestContext, region: str, out_number: str, out_date: str, buffer_data: list) -> tuple[bytes, str]:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо доповідь: ' + str(region) + ', number:' + out_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not out_number:
            raise ValueError("Будь ласка, введіть загальний вихідний номер.")

        # Викликаємо процесор для генерації
        return self.doc_templator.generate_notif_batch(region, out_number, out_date, buffer_data)

    def mark_as_completed(self, ctx: RequestContext, doc_id: int, payload: list, out_number: str, out_date: str,
                          person_controller=None) -> bool:

        self.logger.debug(f'UI:{ctx.user_name}: Помічаємо комплект документів як COMPLETED: {doc_id}')

        draft = self.get_doc_by_id(ctx, doc_id)
        if not draft:
            raise ValueError(f"Чернетку №{doc_id} не знайдено!")

        payload = draft.get('payload', [])
        persons_to_update = []
        for doc in payload:

            row_key = get_person_key_from_str(doc.get('id_number'))
            found_person_data = person_controller.find_person(ctx, row_key)
            kpp_number = doc.get('kpp_num')
            kpp_date = doc.get('kpp_date')

            if not found_person_data:
                self.logger.warning(
                    f"Пропущено: не знайдено людину за ключем {row_key}")
                continue

            person_dict = found_person_data.get('data', {})
            logical_id = person_dict.get(COLUMN_INCREMEMTAL)

            print(f'Знайдено логічний ID: {logical_id}')

            if logical_id is not None:
                p = Person(
                    id=logical_id,
                    kpp_num=kpp_number,
                    kpp_date=kpp_date,
                    # review_status=REVIEW_STATUS_WAITING
                )
                persons_to_update.append(p)

        if persons_to_update:
            success = person_controller.save_persons(ctx, persons_to_update, paint_color=EXCEL_LIGHT_GRAY_COLOR, partial_update=True)
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        dservice = NotifService(self.db, ctx)
        return dservice.mark_as_completed(doc_id, out_number, out_date)