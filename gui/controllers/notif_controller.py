from service.docworkflow.NotifService import NotifService
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow
from utils.utils import get_person_key_from_str
from domain.person import Person
from dics.deserter_xls_dic import *
from config import EXCEL_BLUE_COLOR

class NotifController:
    def __init__(self, workflow:MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()

    def get_all_drafts(self, ctx: RequestContext):
        dservice = NotifService(self.db, ctx)
        return dservice.get_all_docs()

    def save_doc(self, ctx: RequestContext, out_number: str, out_date: str, payload: list,
                   doc_id: int = None) -> int:
        service = NotifService(self.db, ctx)
        return service.save_doc(out_number, out_date, payload, doc_id)

    def delete_doc(self, ctx: RequestContext, doc_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет супроводів: ' + str(doc_id))
        dservice = NotifService(self.db, ctx)
        return dservice.delete_doc(doc_id)

    def get_doc_by_id(self, ctx: RequestContext, doc_id: int) -> dict:
        service = NotifService(self.db, ctx)
        return service.get_doc_by_id(doc_id)

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
            dbr_out_number = doc.get('dbr_num')
            dbr_out_date = doc.get('dbr_date')
            kpp_number = doc.get('kpp_num')
            kpp_date = doc.get('kpp_date')
            o_ass_num = doc.get('o_ass_num')
            o_ass_date = doc.get('o_ass_date')
            o_res_num = doc.get('o_res_num')
            o_res_date = doc.get('o_res_date')

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
                    kpp_num=kpp_number,
                    kpp_date=kpp_date,
                    dbr_date=dbr_out_date,
                    dbr_num=dbr_out_number,
                    o_ass_num=o_ass_num,
                    o_ass_date=o_ass_date,
                    o_res_num=o_res_num,
                    o_res_date=o_res_date,
                    review_status=REVIEW_STATUS_WAITING
                )
                persons_to_update.append(p)

        if persons_to_update:
            success = person_controller.save_persons(ctx, persons_to_update, paint_color=EXCEL_BLUE_COLOR, partial_update=True)
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        dservice = NotifService(self.db, ctx)
        return dservice.mark_as_completed(doc_id, out_number, out_date)