from dics.deserter_xls_dic import *
from domain.person import Person
from domain.person_filter import PersonSearchFilter
from domain.person_key import PersonKey
from gui.services.request_context import RequestContext
from utils.utils import get_person_key_from_str

class PersonController:
    def __init__(self, worklow, auth_manager):
        self.processor = worklow.excelProcessor
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def save_person(self, ctx: RequestContext, person_model, paint_color=None):
        self.logger.debug('UI:' + ctx.user_name + ': Зберігаємо персону ' + str(person_model))
        try:
            id = person_model.id

            if id is None:
                print("Помилка: не знайдено ID рядка для оновлення")
                return False
            updated_data = person_model.to_excel_dict()
            success = self.processor.update_row_by_id(id, updated_data, paint_color)
            if success:
                self.processor.save()
                return True
            return False

        except Exception as e:
            print(f"Помилка при збереженні: {e}")
            return False

    def find_person(self, ctx: RequestContext, person_key: PersonKey):
        return self.processor.find_person(person_key)

    def save_persons(self, ctx: RequestContext, person_list: list, partial_update=False, paint_color=None):
        self.logger.debug(f'UI:{ctx.user_name}: Зберігаємо пакет персон ({len(person_list)} шт.)')
        try:
            success_count = 0

            for person_model in person_list:

                updated_data = person_model.to_excel_dict(partial_update)
                print('>>> updated_data ' + str(updated_data))
                idx = updated_data[COLUMN_INCREMEMTAL]
                # updated_data[COLUMN_INCREMEMTAL] = None
                if self.processor.update_row_by_id(idx, updated_data, paint_color):
                    success_count += 1

            # Якщо хоча б один рядок було успішно оновлено, зберігаємо файл ОДИН раз
            if success_count > 0:
                self.processor.save()
                self.logger.debug(f'Успішно оновлено та збережено {success_count} рядків в Excel.')
                return True

            return False

        except Exception as e:
            self.logger.error(f"Помилка при пакетному збереженні: {e}")
            return False

    def search(self, ctx: RequestContext, filter_obj: PersonSearchFilter) -> List[Person]:
        self.logger.debug('UI:' + ctx.user_name + ': Шукаємо: ' + str(filter_obj))
        results = self.processor.search_people(filter_obj)
        return [Person.from_excel_dict(item['data']) for item in results]

    def get_column_options(self) -> Dict[str, List[str]]:
        return self.processor.get_column_options()
