import xlwings as xw
import traceback
from dics.deserter_xls_dic import *
from service.processing.processors.DocProcessor import DocProcessor
from utils.utils import format_ukr_date
from datetime import datetime, timedelta

class ColumnConverter:
    def __init__(self, excel_file_path, workflow):
        self.file_path = excel_file_path
        self.workflow = workflow
        # Ініціалізуємо DocProcessor (без прив'язки до файлу, просто як двигун)
        self.docProcessor = DocProcessor(workflow, None, None)
        self.app = None
        self.wb = None

    def _get_column_index(self, sheet, col_name):
        """Допоміжний метод для пошуку індексу колонки за назвою (1-based)"""
        header_row = sheet.range('1:1').value
        try:
            # Знаходимо індекс (xlwings повертає 0-based список, додаємо 1)
            return header_row.index(col_name) + 1
        except (ValueError, TypeError):
            print(f"Колонку '{col_name}' не знайдено в хедері.")
            return None

    def convert(self):
        # Тут можна викликати всі методи конвертації
        self._convert_region()

    def _convert_region(self):
        print("--- Початок конвертації ---")

        try:
            # Підключаємось до Excel (видимим чи невидимим)
            self.app = xw.App(visible=False)
            self.wb = self.app.books.open(self.file_path)
            sheet = self.wb.sheets[0]  # Беремо перший лист

            # Отримуємо індекси колонок
            condition_col = self._get_column_index(sheet, COLUMN_DESERT_CONDITIONS)
            des_region_col = self._get_column_index(sheet, COLUMN_DESERTION_REGION)


            if not all([condition_col, des_region_col]):
                print("!!! Необхідні колонки для мапінгу відсутні!")
                return

            # Визначаємо останній рядок
            last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
            print(f"Обробка {last_row - 1} рядків...")

            # Для швидкості зчитуємо цілі діапазони в пам'ять (list of lists)

            condition_values = sheet.range((2, condition_col), (last_row, condition_col)).value
            des_region_values = sheet.range((2, des_region_col), (last_row, des_region_col)).value

            print('>>> condition_values ' + str(len(condition_values)))
            print('>>> des_region_values ' + str(len(des_region_values)))

            # Список для результатів, які ми запишемо одним махом
            results = []

            for i in range(len(condition_values)):
                row_idx = i + 2  # для логування або стилізації
                condition = str(condition_values[i] or "").strip()
                des_region = str(des_region_values[i] or "").strip()

                # Логіка підсвічування порожніх даних
                if not condition:
                    results.append([''])
                    continue
                    # У xlwings колір задається через RGB кортеж
                    # sheet.range((row_idx, subunit_col)).color = (255, 199, 206)  # Pale Red

                # Екстракція підрозділу
                region_my = self.docProcessor._extract_desertion_region(condition)
                # print(str(i) + ': ' + region_my + ' vs ' + rtzk_region + " ( " + rtzk + ' || ' + address + ')')
                #if des_region and region_my != des_region:
                #    print('>>> Incorrect: ' + region_my + ' vs ' + des_region + " (" + condition + ')')
                #if region_my == NA and des_region:
                #    region_my = des_region
                #    # print('>>> MISSING: ' + region_my + ' vs ' + rtzk_region + " (" + rtzk + '||' + address + ')')
                if region_my == NA:
                    print('EMPTY FOR  ' + str(condition))

                results.append([region_my])

            # Записуємо всі результати в колонку одним зверненням (це набагато швидше)
            print('processed: ' + str(len(results)) + " vs values " + str(len(condition_values)))
            # sheet.range((2, rtzk_region_col)).value = results

            self.wb.save()
            print("✅ Конвертацію Subunit2 завершено успішно.")

        except Exception as e:
            print(f"🔴 КРИТИЧНА ПОМИЛКА: {e}")
            print(traceback.format_exc())
        finally:
            if self.wb:
                self.wb.close()
            if self.app:
                self.app.quit()
            print("🏁 Excel сесію закрито.")


    def _check_birthday_by_id(self):
        print("--- Початок перевірки ДН по РНОКПП ---")

        try:
            # Ініціалізація Excel
            self.app = xw.App(visible=False)
            self.wb = self.app.books.open(self.file_path)
            sheet = self.wb.sheets[0]

            # Отримуємо індекси колонок
            id_col = self._get_column_index(sheet, COLUMN_ID_NUMBER)
            birth_col = self._get_column_index(sheet, COLUMN_BIRTHDAY)
            name_col = self._get_column_index(sheet, COLUMN_NAME)

            if not all([id_col, birth_col, name_col]):
                print("!!! Необхідні колонки відсутні в Excel!")
                return

            # Визначаємо останній рядок по колонці Прізвища (зазвичай вона найбільш заповнена)
            # 1. Визначаємо номер останнього можливого рядка в Excel (напр. 1048576)
            max_excel_row = sheet.cells.last_cell.row

            # 2. Знаходимо останній заповнений рядок у конкретній колонці (name_col)
            # Це аналог натискання Cmd+Up у самому низу Excel
            last_row = sheet.cells(max_excel_row, name_col).end('up').row

            print(f"Загальна кількість рядків для аналізу: {last_row}")

            base_date = datetime(1899, 12, 31)

            for row in range(7000, last_row + 1):
                try:
                    # Читаємо значення построчно
                    id_val = sheet.cells(row, id_col).value
                    bth_val = sheet.cells(row, birth_col).value
                    name_val = sheet.cells(row, name_col).value

                    # Якщо ПІБ порожнє - ймовірно, це кінець даних або сміття
                    if not name_val:
                        continue

                    # Валідація та очищення ID
                    if id_val is None:
                        continue

                    # Обробка float (Excel часто віддає числа як 123.0)
                    id_str = str(int(float(id_val))) if isinstance(id_val, (float, int)) else str(id_val).strip()

                    if len(id_str) != 10 or not id_str.isdigit():
                        print(f"Рядок {row}: Некоректний формат РНОКПП '{id_str}'")
                        continue

                    # Обчислюємо дату з РНОКПП
                    days_count = int(id_str[:5])
                    birthday_calculated_dt = base_date + timedelta(days=days_count)
                    birthday_calculated = format_ukr_date(birthday_calculated_dt).strip()

                    # Отримуємо дату з таблиці
                    birthday_table = format_ukr_date(bth_val).strip() if bth_val else "відсутня"

                    # Порівняння
                    if birthday_table != birthday_calculated:
                        print(f"❌ Невідповідність [Рядок {row}]: {name_val}")
                        print(f"   РНОКПП: {id_str} -> {birthday_calculated}")
                        print(f"   В таблиці: {birthday_table}")

                        # Опціонально: підсвічуємо помилку в Excel
                        # sheet.cells(row, id_col).color = (255, 100, 100)

                except Exception as row_error:
                    # Якщо помилка в одному рядку - пропускаємо і йдемо далі
                    print(f"⚠️ Помилка обробки рядка {row}: {row_error}")
                    continue

            print("✅ Перевірку завершено.")

        except Exception as e:
            print(f"🔴 КРИТИЧНА ПОМИЛКА: {e}")
            traceback.print_exc()
        finally:
            if self.wb:
                self.wb.close()
            if self.app:
                self.app.quit()
            print("🏁 Excel сесію закрито.")