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
        return
        # self._convert_region()

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
            last_row = self.get_last_row(sheet)
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
                #if region_my == NA:
                #    print('EMPTY FOR  ' + str(condition))

                results.append([region_my])

            # Записуємо всі результати в колонку одним зверненням (це набагато швидше)
            print('processed: ' + str(len(results)) + " vs values " + str(len(condition_values)))
            sheet.range((2, des_region_col)).value = results

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



    def _convert_A7018(self):
        print("--- Початок конвертації ---")

        try:
            # Підключаємось до Excel (видимим чи невидимим)
            self.app = xw.App(visible=False)
            self.wb = self.app.books.open(self.file_path)
            sheet = self.wb.sheets['А7018']

            # Отримуємо індекси колонок
            bio_col = self._get_column_index(sheet, COLUMN_BIO)
            birth_col = self._get_column_index(sheet, COLUMN_BIRTHDAY)
            rno_col = self._get_column_index(sheet, COLUMN_ID_NUMBER)
            enlist_date_col = self._get_column_index(sheet, COLUMN_ENLISTMENT_DATE)
            rtzk_col = self._get_column_index(sheet, COLUMN_TZK)
            rtzk_region_col = self._get_column_index(sheet, COLUMN_TZK_REGION)
            address_col = self._get_column_index(sheet, COLUMN_ADDRESS)
            phone_col = self._get_column_index(sheet, COLUMN_PHONE)

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
            bio_values = sheet.range((2, bio_col), (last_row, bio_col)).value
            birth_values = sheet.range((2, birth_col), (last_row, birth_col)).value
            rno_values = sheet.range((2, rno_col), (last_row, rno_col)).value
            enlist_values = sheet.range((2, enlist_date_col), (last_row, enlist_date_col)).value
            rtzk_values = sheet.range((2, rtzk_col), (last_row, rtzk_col)).value
            rtzk_region_values = sheet.range((2, rtzk_region_col), (last_row, rtzk_region_col)).value
            address_values = sheet.range((2, address_col), (last_row, address_col)).value
            phone_values = sheet.range((2, phone_col), (last_row, phone_col)).value

            print('>>> condition_values ' + str(len(condition_values)))
            print('>>> des_region_values ' + str(len(des_region_values)))
            print('>>> bio_values ' + str(len(bio_values)))
            print('>>> birth_values ' + str(len(birth_values)))
            print('>>> rno_values ' + str(len(rno_values)))
            print('>>> enlist_values ' + str(len(enlist_values)))
            print('>>> rtzk_values ' + str(len(rtzk_values)))
            print('>>> rtzk_region_values ' + str(len(rtzk_region_values)))
            print('>>> address_values ' + str(len(address_values)))
            print('>>> phone_values ' + str(len(phone_values)))

            # Список для результатів, які ми запишемо одним махом
            des_region_results = []
            birth_results = []
            rno_results = []
            enlist_date_results = []
            rtzk_results = []
            rtzk_regions_results = []
            address_results = []
            phone_results = []

            for i in range(len(condition_values)):
                row_idx = i + 2  # для логування або стилізації
                condition = str(condition_values[i] or "").strip()
                bio = str(bio_values[i] or "").strip()
                des_region = str(des_region_values[i] or "").strip()

                # Логіка підсвічування порожніх даних
                if not condition:
                    des_region_results.append([''])
                    birth_results.append([''])
                    rno_results.append([''])
                    enlist_date_results.append([''])
                    rtzk_results.append([''])
                    rtzk_regions_results.append([''])
                    address_results.append([''])
                    phone_results.append([''])
                    continue
                    # У xlwings колір задається через RGB кортеж
                    # sheet.range((row_idx, subunit_col)).color = (255, 199, 206)  # Pale Red

                # Екстракція підрозділу
                des_region = self.docProcessor._extract_desertion_region(condition)
                birth = self.docProcessor._extract_birthday(bio)
                rno = self.docProcessor._extract_id_number(bio)
                enlist_date = self.docProcessor._extract_conscription_date(bio)
                rtzk = self.docProcessor._extract_rtzk(bio)
                rtzk_region = self.docProcessor._extract_region(bio)
                address = self.docProcessor._extract_address(bio)
                phone = self.docProcessor._extract_phone(bio)

                des_region_results.append([des_region])
                birth_results.append([birth])
                rno_results.append([rno])
                enlist_date_results.append([enlist_date])
                rtzk_results.append([rtzk])
                rtzk_regions_results.append([rtzk_region])
                address_results.append([address])
                phone_results.append([phone])

            # Записуємо всі результати в колонку одним зверненням (це набагато швидше)
            # print('processed: ' + str(len(phone_results)) + " vs values " + str(len(condition_values)))
            sheet.range((2, des_region_col)).value = des_region_results
            sheet.range((2, birth_col)).value = birth_results
            sheet.range((2, rno_col)).value = rno_results
            sheet.range((2, enlist_date_col)).value = enlist_date_results
            sheet.range((2, rtzk_col)).value = rtzk_results
            sheet.range((2, rtzk_region_col)).value = rtzk_regions_results
            sheet.range((2, address_col)).value = address_results
            sheet.range((2, phone_col)).value = phone_results

            # self.wb.save()
            print("✅ Конвертацію A7018 завершено успішно.")

        except Exception as e:
            print(f"🔴 КРИТИЧНА ПОМИЛКА: {e}")
            print(traceback.format_exc())
        finally:
            if self.wb:
                self.wb.close()
            if self.app:
                self.app.quit()
            print("🏁 Excel сесію закрито.")



    def get_last_row(self, sheet):
        last_row = sheet.used_range.last_cell.row

        # Читаємо ВЕСЬ стовпець 'A' в пам'ять (це миттєво)
        col_a_values = sheet.range(f"A1:A{last_row}").value

        # Захист: якщо таблиця складається лише з 1 рядка, xlwings може повернути просто значення, а не список
        if not isinstance(col_a_values, list):
            col_a_values = [col_a_values]

        # Йдемо циклом ЗНИЗУ ВГОРУ по отриманих значеннях
        # len(col_a_values) - 1 — це останній індекс списку
        for i in range(len(col_a_values) - 1, -1, -1):
            val = col_a_values[i]

            # Якщо знайшли клітинку, яка не None і не порожній рядок
            if val is not None and str(val).strip() != '':
                last_row = i + 1  # +1, бо індекси масивів починаються з 0, а рядки в Excel з 1
                break

        print('>>> last row :: ' + str(last_row))
        return last_row