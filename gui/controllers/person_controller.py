from dics.deserter_xls_dic import *
from gui.model.person import Person

class PersonController:
    def __init__(self, worklow):
        self.processor = worklow.excelProcessor

    def search_people(self, year, name):
        return self.search(year, name, None)

    def search_by_erdr(self, o_ass_num, name):
        return self.search(None, name, o_ass_num)

    def save_person(self, person_model, paint_color=None):
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

    def search(self, year, query:str, o_ass_num:str) -> List[Person]:
        results = self.processor.search_by_name_rnkopp(query, year, o_ass_num)
        return [Person.from_excel_dict(item['data']) for item in results]

    def get_column_options(self) -> Dict[str, List[str]]:
        return self.processor.get_column_options()
