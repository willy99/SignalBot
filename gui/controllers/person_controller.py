from dics.deserter_xls_dic import *
from domain.person import Person
from domain.person_filter import PersonSearchFilter
from gui.services.request_context import RequestContext

class PersonController:
    def __init__(self, worklow, auth_manager):
        self.processor = worklow.excelProcessor
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def save_person(self, ctx: RequestContext, person_model, paint_color=None):
        self.logger.debug('UI:' + ctx.user_name + ': Зберігаємо персону ' + str(person_model))
        try:
            row_idx = person_model.id

            if row_idx is None:
                print("Помилка: не знайдено індекс рядка для оновлення")
                return False
            updated_data = person_model.to_excel_dict()
            success = self.processor.update_row_by_index(row_idx, updated_data, paint_color)
            if success:
                self.processor.save()
                return True
            return False

        except Exception as e:
            print(f"Помилка при збереженні: {e}")
            return False

    def search(self, ctx: RequestContext, filter_obj: PersonSearchFilter) -> List[Person]:
        self.logger.debug('UI:' + ctx.user_name + ': Шукаємо: ' + str(filter_obj))
        results = self.processor.search_people(filter_obj)
        return [Person.from_excel_dict(item['data']) for item in results]

    def get_column_options(self) -> Dict[str, List[str]]:
        return self.processor.get_column_options()
