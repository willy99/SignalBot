from typing import Optional

from domain.document_filter import DocumentFilter
from service.docworkflow.DbrService import DbrService, DbrDoc
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow
from utils.utils import get_person_key_from_str
from domain.person import Person
from dics.deserter_xls_dic import *
import config


class DbrController:
    def __init__(self, workflow: MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()

    def search_drafts(self, ctx: RequestContext, doc_filter: DocumentFilter):
        dservice = DbrService(self.db, ctx)
        docs = dservice.search_docs(doc_filter)
        return [doc.model_dump() for doc in docs]

    def count_search_docs(self, ctx: RequestContext, search_filter: DocumentFilter):
        dservice = DbrService(self.db, ctx)
        return dservice.count_search_docs(search_filter, None)

    def save_dbr_doc(self, ctx: RequestContext, out_number: str, out_date: str, payload: list,
                     dbr_doc_id: int = None) -> int:
        service = DbrService(self.db, ctx)

        doc_model = DbrDoc(
            id=dbr_doc_id,
            out_number=out_number,
            out_date=out_date,
            payload=payload
        )

        return service.save_doc(doc_model)

    def delete_dbr_doc(self, ctx: RequestContext, dbr_doc_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет супроводів: ' + str(dbr_doc_id))
        dservice = DbrService(self.db, ctx)
        return dservice.delete_doc(dbr_doc_id)

    def get_dbr_doc_by_id(self, ctx: RequestContext, dbr_doc_id: int) -> dict:
        service = DbrService(self.db, ctx)
        doc_model = service.get_doc_by_id(dbr_doc_id)
        if doc_model:
            return doc_model.model_dump()
        return None

    def mark_as_completed(self, ctx: RequestContext, dbr_doc_id: int, payload: list, out_number: str, out_date: str,
                          person_controller=None) -> bool:

        self.logger.debug(f'UI:{ctx.user_name}: Помічаємо комплект документів як COMPLETED: {dbr_doc_id}')

        draft = self.get_dbr_doc_by_id(ctx, dbr_doc_id)
        if not draft:
            raise ValueError(f"Чернетку №{dbr_doc_id} не знайдено!")

        payload_data = draft.get('payload', [])
        persons_to_update = []

        for doc in payload_data:
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
            mil_unit = doc.get('mil_unit') if doc.get('mil_unit') else MIL_UNITS[0]

            if not found_person_data:
                self.logger.warning(f"Пропущено: не знайдено людину за ключем {row_key}")
                continue

            person_dict = found_person_data.get('data', {})
            logical_id = person_dict.get(COLUMN_INCREMENTAL)

            print(f'Знайдено логічний ID: {logical_id}')

            if logical_id is not None:
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
                    review_status=REVIEW_STATUS_WAITING,
                    mil_unit=mil_unit
                )
                persons_to_update.append(p)

        if persons_to_update:
            success = person_controller.save_persons(ctx, persons_to_update, paint_color=config.EXCEL_BLUE_COLOR, partial_update=True)
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        dservice = DbrService(self.db, ctx)
        return dservice.mark_as_completed(dbr_doc_id, out_number, out_date)

    def is_existing_num(self, ctx: RequestContext, out_number: str, exclude_id: Optional[int] = None) -> bool:
        dservice = DbrService(self.db, ctx)
        return dservice.is_existing_num(out_number, exclude_id)