import config
from domain.document_filter import DocumentFilter
from gui.services.request_context import RequestContext
from domain.person import Person
from typing import List, Optional, Dict, Any

from service.constants import DOC_PACKAGE_STANDART
from service.docworkflow.DocSupportService import DocSupportService, SupportDoc
from gui.controllers.person_controller import PersonController
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from utils.utils import get_person_key_from_str
from dics.deserter_xls_dic import COLUMN_INCREMENTAL, MIL_UNITS, COLUMN_MIL_UNIT
from gui.services.auth_manager import AuthManager

class SupportController:
    def __init__(self, doc_templator: DocTemplator, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.doc_templator = doc_templator
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

        return self.doc_templator.generate_support_batch_detailed(city, supp_number, supp_date, buffer_data)

    def generate_standard_support_document(self, ctx, city: str, supp_number: str, supp_date: str, buffer_data: list):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not supp_number:
            raise ValueError("Будь ласка, введіть загальний номер супроводу.")

        return self.doc_templator.generate_support_batch_standart(city, supp_number, supp_date, buffer_data)

    def generate_logs(self, ctx: RequestContext, city: str, supp_number: str, supp_date: str, buffer_data: list) -> str:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))
        log_text = self.doc_templator.generate_support_logs(city, supp_number, supp_date, buffer_data)
        print(str(log_text))
        return log_text

    def save_support_doc(self, ctx: RequestContext, city: str, out_number: str, out_date: str, buffer_data: list,
                         draft_id: Optional[int] = None, package_type:str=DOC_PACKAGE_STANDART) -> int:
        self.logger.debug('UI:' + ctx.user_name + ': Запис змін для пакету супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)

        doc_model = SupportDoc(
            id=draft_id,
            created_by=ctx.user_id,
            city=city,
            out_number=out_number,
            out_date=out_date,
            payload=buffer_data,
            package_type=package_type
        )

        return dservice.save_doc(doc_model)

    def search_drafts(self, ctx: RequestContext, search_filter: DocumentFilter) -> List[Dict[str, Any]]:
        dservice = DocSupportService(self.db, ctx)
        docs = dservice.search_docs(search_filter)
        return [doc.model_dump() for doc in docs]

    def count_search_docs(self, ctx: RequestContext, search_filter: DocumentFilter):
        dservice = DocSupportService(self.db, ctx)
        return dservice.count_search_docs(search_filter, None)

    def delete_draft(self, ctx: RequestContext, draft_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо пакет супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)
        return dservice.delete_doc(draft_id)

    def get_support_doc_by_id(self, ctx: RequestContext, draft_id: int) -> Optional[Dict[str, Any]]:
        self.logger.debug('UI:' + ctx.user_name + ': Дістаємо пакет супроводів: ' + str(draft_id))
        dservice = DocSupportService(self.db, ctx)
        doc_model = dservice.get_doc_by_id(draft_id)
        if doc_model:
            return doc_model.model_dump()
        return None

    def mark_as_completed(self, ctx: RequestContext, person_ctrl: PersonController, draft_id: int) -> bool:
        self.logger.debug(f'UI:{ctx.user_name}: Помічаємо комплект супроводів як COMPLETED: {draft_id}')

        draft = self.get_support_doc_by_id(ctx, draft_id)
        if not draft:
            raise ValueError(f"Чернетку №{draft_id} не знайдено!")

        out_number = draft.get('out_number')
        out_date = draft.get('out_date')
        payload = draft.get('payload', [])
        package_type = draft.get('package_type')

        # 1. Збираємо всі ключі для масового пошуку
        search_keys = []
        for doc in payload:
            id_str = doc.get('id_number')
            if id_str:
                search_keys.append(get_person_key_from_str(id_str))

        # 2. Викликаємо масовий пошук (один прохід по Excel)
        all_found_data = person_ctrl.find_persons(search_keys)

        persons_to_update = []
        for doc in payload:
            id_str = doc.get('id_number')
            current_key = get_person_key_from_str(id_str)
            found_person_data = all_found_data.get(current_key.uid)
            row_seq_num = doc.get('seq_num')

            if not found_person_data:
                self.logger.warning(f"Пропущено: не знайдено людину за ключем {id_str}")
                continue

            person_dict = found_person_data.get('data', {})
            logical_id = person_dict.get(COLUMN_INCREMENTAL)

            if logical_id is not None:
                # Логіка формування номера (суфікс /1, /2 тощо)
                individual_suffix = (f'/{row_seq_num}' if row_seq_num else '') if package_type != DOC_PACKAGE_STANDART else ''

                mil_unit = doc.get('mil_unit') or MIL_UNITS[0]

                p = Person(
                    id=logical_id,
                    dbr_date=out_date,
                    dbr_num=f"{out_number}{individual_suffix}",
                    mil_unit=mil_unit
                )
                persons_to_update.append(p)

        # 3. Масове оновлення в Excel (теж одним блоком)
        if persons_to_update:
            success = person_ctrl.save_persons(
                ctx,
                persons_to_update,
                paint_color=config.EXCEL_SUPPORT_COLOR,
                partial_update=True
            )
            if not success:
                raise Exception("Не вдалося оновити дані в Excel. Статус чернетки НЕ змінено.")

        # 4. Зміна статусу в БД
        dservice = DocSupportService(self.db, ctx)
        return dservice.mark_as_completed(draft_id)

    def is_existing_num(self, ctx: RequestContext, out_number: str, exclude_id: Optional[int] = None) -> bool:
        dservice = DocSupportService(self.db, ctx)
        return dservice.is_existing_num(out_number, exclude_id)