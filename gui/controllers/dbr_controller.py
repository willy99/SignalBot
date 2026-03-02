from service.docworkflow.DbrService import DbrService
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow

class DbrController:
    def __init__(self, workflow:MyWorkFlow, auth_manager: AuthManager):
        self.db = workflow.db
        self.log_manager = workflow.log_manager

    def get_all_drafts(self, ctx: RequestContext):
        dservice = DbrService(self.db, ctx)
        return dservice.get_all_dbr_docs()

    def save_dbr_doc(self, ctx: RequestContext, out_number: str, out_date: str, payload: list,
                   dbr_doc_id: int = None) -> int:
        service = DbrService(self.db, ctx)
        return service.save_dbr_doc(out_number, out_date, payload, dbr_doc_id)

    def get_dbr_doc_by_id(self, ctx: RequestContext, dbr_doc_id: int) -> dict:
        service = DbrService(self.db, ctx)
        return service.get_dbr_doc_by_id(dbr_doc_id)

    def mark_as_completed(self, ctx: RequestContext, dbr_doc_id: int, payload: list, out_number: str, out_date: str,
                          person_controller=None) -> bool:
        """
        Відзначає чернетку як виконану.
        Окрім зміни статусу чернетки, має оновити відповідні поля у таблиці військовослужбовців.
        """
        service = DbrService(self.db, ctx)

        # 1. Змінюємо статус самої чернетки в базі
        success = service.mark_as_completed(dbr_doc_id, out_number, out_date)

        if not success:
            return False

        # 2. Якщо передано person_controller, оновлюємо дані по кожному військовослужбовцю в Excel/БД
        if person_controller and payload:
            for person_data in payload:
                rnokpp = person_data.get('rnokpp')
                name = person_data.get('name')

                if rnokpp or name:
                    # Формуємо словник з полями, які треба оновити (наприклад, номер та дата повідомлення)
                    # Назви колонок залежать від вашого Excel (напр. COLUMN_NOTIFICATION_NUMBER)
                    update_dict = {
                        'Повідомлення ДБР (номер)': out_number,
                        'Повідомлення ДБР (дата)': out_date,
                        'Статус розгляду': 'Відправлено на ДБР'
                    }

                    try:
                        # Тут виклик методу оновлення з вашого PersonController / ExcelProcessor
                        # person_controller.update_person_by_rnokpp_or_name(ctx, name, rnokpp, update_dict)
                        pass  # Розкоментуйте і адаптуйте під ваші реальні методи
                    except Exception as e:
                        print(f"Помилка оновлення особи {name} в Excel: {e}")

        return True