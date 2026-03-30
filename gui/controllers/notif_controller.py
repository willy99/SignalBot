from typing import Optional

from domain.document_filter import DocumentFilter
from service.docworkflow.NotifService import NotifService, NotifDoc
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from utils.utils import get_person_key_from_str
from domain.person import Person
from dics.deserter_xls_dic import *
import config


class NotifController:
    def __init__(self, doc_templator: DocTemplator, workflow: MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.excel_processor = workflow.excelProcessor
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()
        self.doc_templator = doc_templator

    def search_drafts(self, ctx: RequestContext, search_filter: DocumentFilter):
        dservice = NotifService(self.db, ctx)
        docs = dservice.search_docs(search_filter)
        return [doc.model_dump() for doc in docs]

    def count_search_docs(self, ctx: RequestContext, search_filter: DocumentFilter):
        dservice = NotifService(self.db, ctx)
        return dservice.count_search_docs(search_filter, None)

    def save_doc(self, ctx: RequestContext, region: str, out_number: str, out_date: str, payload: list,
                 doc_id: int = None) -> int:
        self.logger.debug('UI:' + ctx.user_name + ': Зберігаємо повідомлення: ' + str(region) + ', number:' + out_number)
        service = NotifService(self.db, ctx)

        doc_model = NotifDoc(
            id=doc_id,
            region=region,
            out_number=out_number,
            out_date=out_date,
            payload=payload
        )

        return service.save_doc(doc_model)

    def delete_doc(self, ctx: RequestContext, doc_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет повідомлень: ' + str(doc_id))
        dservice = NotifService(self.db, ctx)
        return dservice.delete_doc(doc_id)

    def get_doc_by_id(self, ctx: RequestContext, doc_id: int) -> dict:
        service = NotifService(self.db, ctx)
        doc_model = service.get_doc_by_id(doc_id)
        if doc_model:
            return doc_model.model_dump()
        return None

    def generate_document(self, ctx: RequestContext, region: str, out_number: str, out_date: str, buffer_data: list) -> tuple[bytes, str]:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо документ повідомлень: ' + str(region) + ', number:' + out_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not out_number:
            raise ValueError("Будь ласка, введіть загальний вихідний номер.")

        return self.doc_templator.generate_notif_batch(region, out_number, out_date, buffer_data)

    def generate_individual_documents(self, ctx: RequestContext, region: str, out_num: str, out_date: str, buffer: list) -> tuple[bytes, str]:
        self.logger.debug(f'UI:{ctx.user_name}: Формуємо ZIP-архів індивідуальних повідомлень для {len(buffer)} осіб.')

        if not buffer:
            raise ValueError("Буфер порожній. Немає даних для генерації.")
        if not out_num:
            raise ValueError("Введіть вихідний номер.")

        # Передаємо роботу в темплейтер
        return self.doc_templator.generate_notif_zip_archive(region, out_num, out_date, buffer)

    def mark_as_completed(self, ctx: RequestContext, doc_id: int, payload: list, out_number: str, out_date: str, person_controller=None) -> bool:

        self.logger.debug(f'UI:{ctx.user_name}: Помічаємо комплект повідомлень як COMPLETED: {doc_id}')

        draft = self.get_doc_by_id(ctx, doc_id)
        if not draft:
            raise ValueError(f"Чернетку №{doc_id} не знайдено!")

        payload_data = draft.get('payload', [])

        search_keys = []
        for doc in payload_data:
            id_str = doc.get('id_number')
            if id_str:
                search_keys.append(get_person_key_from_str(id_str))

        all_found_data = person_controller.find_persons(search_keys)

        persons_to_update = []
        for doc in payload_data:
            id_str = doc.get('id_number')
            current_key = get_person_key_from_str(id_str)
            found_person_data = all_found_data.get(current_key.uid)

            if not found_person_data:
                self.logger.warning(f"Пропущено: не знайдено людину за ключем {id_str}")
                continue

            person_dict = found_person_data.get('data', {})
            logical_id = person_dict.get(COLUMN_INCREMENTAL)

            row_seq_num = doc.get('seq_num')
            mil_unit = doc.get('mil_unit') or MIL_UNITS[0]

            if logical_id is not None:
                p = Person(
                    id=logical_id,
                    kpp_num=f"{doc.get('kpp_num')}/{row_seq_num}",
                    kpp_date=doc.get('kpp_date'),
                    mil_unit=mil_unit
                )
                persons_to_update.append(p)

        if persons_to_update:
            success = person_controller.save_persons(ctx, persons_to_update, paint_color=config.EXCEL_LIGHT_GRAY_COLOR, partial_update=True)
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        dservice = NotifService(self.db, ctx)
        return dservice.mark_as_completed(doc_id, out_number, out_date)

    def is_existing_num(self, ctx: RequestContext, out_number: str, exclude_id: Optional[int] = None) -> bool:
        dservice = NotifService(self.db, ctx)
        return dservice.is_existing_num(out_number, exclude_id)