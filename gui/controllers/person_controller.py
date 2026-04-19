from typing import Any

from dics.deserter_xls_dic import *
from domain.person import Person
from domain.person_filter import PersonSearchFilter
from domain.person_key import PersonKey
from gui.services.request_context import RequestContext
from gui.services.auth_manager import AuthManager
from service.docworkflow.DbrService import DbrService
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.converter.ColumnConverter import ColumnConverter
from service.storage import FileCacher


class PersonController:
    def __init__(self, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.processor = worklow.excelProcessor
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()
        self.log_manager = worklow.log_manager
        self.excelFilePath = worklow.excelFilePath
        self.excelProcessor = worklow.excelProcessor

    def save_person(self, ctx: RequestContext, person_model, paint_color=None):
        self.logger.debug(f'UI:{ctx.user_name}: Зберігаємо персону {person_model.name}')
        try:
            person_id = person_model.id

            # Перетворюємо модель на словник для запису
            updated_data = person_model.to_excel_dict()

            if person_id is None:
                self.logger.debug("ID відсутній: створюємо новий запис в Excel.")

                success = self.processor.upsert_record([updated_data])

            else:
                self.logger.debug(f"Оновлюємо існуючий запис (ID: {person_id})")
                success = self.processor.update_row_by_id(person_id, updated_data, paint_color)

            if success:
                self.processor.save()
                self.logger.debug('✅ Дані успішно збережено в Excel.')
                return True

            self.logger.error('❌ Процесор повернув False при збереженні.')
            return False

        except Exception as e:
            self.logger.error(f"Помилка при збереженні персони: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    def delete_record(self, ctx: RequestContext, person_model):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо персону ' + str(person_model))
        try:
            id = person_model.id
            mil_unit = person_model.mil_unit if person_model.mil_unit else MIL_UNITS[0]

            if id is None:
                print("Помилка: не знайдено ID рядка для оновлення")
                return False
            success = self.processor.delete_record(id, mil_unit)
            if success:
                self.processor.save()
                return True
            return False

        except Exception as e:
            print(f"Помилка при видаленні: {e}")
            return False


    def find_person(self, person_key: PersonKey):
        return self.processor.find_person(person_key)

    def find_persons(self, person_keys: list[PersonKey])-> dict[str, dict]:
        return self.processor.find_persons(person_keys)

    def batch_search_names(self, ctx: RequestContext, names_list: List[str]) -> List[Dict[str, Any]] :
        self.logger.debug('UI:' + ctx.user_name + ': Шукаємо список з ' + str(len(names_list)) + ' людей')
        return self.processor.batch_search_names(names_list)

    def sync(self, ctx: RequestContext):
        self.logger.debug(f'UI:{ctx.user_name}: Сінхронізуємо базу')
        self.processor.save()
        return True

    def convert_columns(self, ctx:RequestContext):
        converter = ColumnConverter(self.excelFilePath, self.log_manager, self.excelProcessor)
        converter.convert()

    def save_persons(self, ctx: RequestContext, person_list: list, partial_update=False, paint_color=None):
        self.logger.debug(f'UI:{ctx.user_name}: Зберігаємо пакет персон ({len(person_list)} шт.)')
        try:
            with self.processor.lock:
                success_count = 0

                # 1. Групуємо людей за військовою частиною (щоб не стрибати між табами)
                grouped_persons = {}
                for person_model in person_list:
                    # Якщо з якихось причин mil_unit немає, ставимо дефолтний
                    m_unit = getattr(person_model, 'mil_unit', None) or MIL_UNITS[0]

                    if m_unit not in grouped_persons:
                        grouped_persons[m_unit] = []
                    grouped_persons[m_unit].append(person_model)

                # 2. Обробляємо кожну групу на своєму аркуші
                for mil_unit, persons in grouped_persons.items():

                    # Перемикаємо аркуш ОДИН РАЗ для всієї групи!
                    self.processor.switch_to_sheet(mil_unit, silent=True)

                    for person_model in persons:
                        updated_data = person_model.to_excel_dict(partial_update)
                        print(f'>>> updated_data [{mil_unit}]: {updated_data}')
                        idx = updated_data[COLUMN_INCREMENTAL]

                        # Відправляємо на збереження у процесор (він вже стоїть на правильному аркуші)
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

    '''
    def search(self, ctx: RequestContext, filter_obj: PersonSearchFilter) -> List[Person]:
        self.logger.debug('UI:' + ctx.user_name + ': Шукаємо: ' + str(filter_obj))
        mil_unit = MIL_UNITS[0]
        filter_obj.mil_unit = mil_unit
        results_a0224 = self.processor.search_people(filter_obj)
        for item in results_a0224:
            item['data'][COLUMN_MIL_UNIT] = mil_unit
        mil_unit = MIL_UNITS[1]
        filter_obj.mil_unit = mil_unit # спроба знайти на другому табі
        results_a7018 = self.processor.search_people(filter_obj)
        for item in results_a7018:
            item['data'][COLUMN_MIL_UNIT] = mil_unit
        results = results_a0224 + results_a7018
        return [Person.from_excel_dict(item['data']) for item in results]
    '''


    def search(self, ctx: RequestContext, filter_obj: PersonSearchFilter) -> List[Person]:
        self.logger.debug(f'UI:{ctx.user_name}: Шукаємо: {filter_obj}')

        # Визначаємо список частин для пошуку
        if filter_obj.mil_unit:
            # Якщо в фільтрі є конкретна частина, шукаємо тільки в ній
            units_to_search = [filter_obj.mil_unit]
        else:
            # Якщо ні — шукаємо по всьому списку (за замовчуванням MIL_UNITS)
            units_to_search = MIL_UNITS

        all_results = []

        for unit in units_to_search:
            # Створюємо копію фільтра або просто підміняємо unit для поточного проходу
            filter_obj.mil_unit = unit
            raw_data = self.processor.search_people(filter_obj)

            for item in raw_data:
                # Додаємо мітку частини в дані, щоб у таблиці було видно, звідки запис
                item['data'][COLUMN_MIL_UNIT] = unit
                person_obj = Person.from_excel_dict(item['data'])
                # Передаємо інформацію про збіг з тимчасового поля в об'єкт
                person_obj.matched_voc_info = item['data'].get('matched_voc_info', '')

                all_results.append(person_obj)

        return all_results

    def get_column_options(self) -> Dict[str, List[str]]:
        return self.processor.get_column_options()
