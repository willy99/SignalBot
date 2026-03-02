import xlwings as xw
import os
import sys

import warnings

from config import DESERTER_TAB_NAME, EXCEL_CHUNK_SIZE
from dics.deserter_xls_dic import *
from dics.deserter_xls_dic import NA
from typing import List, Dict, Any
from utils.utils import format_ukr_date, get_typed_value, format_to_excel_date, get_strint_fromfloat
import traceback
from service.storage.LoggerManager import LoggerManager
from datetime import date, datetime
import threading
from domain.person_filter import PersonSearchFilter
from domain.person_key import PersonKey

class ExcelProcessor:
    def __init__(self, file_path, log_manager: LoggerManager, batch_processing=False):
        self.file_path: str = file_path
        self.workbook = None
        self.sheet = None
        self.column_map: Dict[str, int] = {}  # {назва: номер_колонки}
        self.header: Dict[str, int] = {}
        self.batch_processing = batch_processing
        self.logger = log_manager.get_logger()

        warnings.filterwarnings("ignore", category=UserWarning)
        self.abs_path = os.path.abspath(file_path)
        self.app = xw.App(visible=False, add_book=False)
        self._load_workbook(DESERTER_TAB_NAME) #default tab name
        self.lock = threading.Lock()

        self.column_values: Dict[str, List[str]] = {} # для комбіков

    def upsert_record(self, records_list: List[Dict[str, Any]]) -> None:
        if not records_list:
            return
        sheet_name = records_list[0].get(COLUMN_MIL_UNIT, None)
        self._load_workbook(sheet_name)
        try:
            self._processRow(records_list)
            if not self.batch_processing:
                self.save()
        except Exception as e:
            self.logger.error(f"❌ Помилка під час upsert_record: {e}")
            traceback.print_exc()
            if self.workbook:
                self.workbook.close()
                self.workbook = None

    def _processRow(self, records_list):
        id_col_idx = self.column_map.get(COLUMN_INCREMEMTAL.lower())
        if not id_col_idx:
            self.logger.error("❌ Помилка: Не знайдено колонку №")
            return

        last_used_row = self.sheet.used_range.last_cell.row
        last_row_with_data = self.sheet.range((last_used_row, id_col_idx)).end('up').row
        target_insert_row = last_row_with_data + 1

        last_val = self.sheet.range((last_row_with_data, id_col_idx)).value

        try:
            if last_val is not None:
                # Спершу перетворюємо на float (на випадок 11164.0), а потім на int
                current_id = int(float(last_val))
            else:
                current_id = 0
        except (ValueError, TypeError):
            # self.logger.warning(f'--- ⚠️ Помилка отримання поточного ID. Останнє значення: {last_val}')
            print('>>>> target row: ' + str(target_insert_row))
            print('>>>> last_val: ' + str(last_val))
            print('>>>> last_used_row: ' + str(last_used_row))
            print('>>>> last_row_with_data: ' + str(last_row_with_data))
            raise ValueError(f'--- ⚠️ Помилка отримання поточного ID. Останнє значення: {last_val}')

        self.logger.debug(f'--- Визначено останній ID: {current_id} (з рядка {last_row_with_data})')

        # 3. Перебір кожного словника в масиві
        for data_dict in records_list:
            existing_row = self._find_existing_row(data_dict)

            if existing_row:
                for col_name, value in data_dict.items():
                    idx = self.column_map.get(col_name.lower())
                    if idx:
                        # Кортеж тут!
                        current_cell = self.sheet.range((existing_row, idx))
                        if (not current_cell.value or current_cell.value == NA) and value:
                            current_cell.value = get_typed_value(value)
                            self.logger.debug(f'--- [Рядок {existing_row}] оновлюємо {col_name}: {value}')
            else:
                # --- СТВОРЕННЯ НОВОГО ---
                current_id += 1

                # Вставляємо новий рядок через native Excel API
                # Це автоматично копіює стилі та формули з рядка вище
                try:
                    self.sheet.range((target_insert_row, 1)).api.entire_row.insert()
                except Exception as e:
                    self.sheet.range(f'{target_insert_row - 1}:{target_insert_row - 1}').copy()
                    # 2. Вставляємо скопійоване зі зсувом вниз (це створить новий рядок з форматом)
                    self.sheet.range(f'{target_insert_row}:{target_insert_row}').insert(shift='down')

                # 1. Записуємо ID в першу колонку
                self.sheet.range((target_insert_row, id_col_idx)).value = current_id

                # 2. Записуємо всі інші дані
                for col_name, value in data_dict.items():
                    idx = self.column_map.get(col_name.lower())
                    if idx:
                        self.sheet.range((target_insert_row, idx)).value = get_typed_value(value)

                # 3. Додаткове налаштування (висота та вирівнювання, якщо Excel не підхопив сам)
                new_row_range = self.sheet.range(f'{target_insert_row}:{target_insert_row}')
                new_row_range.row_height = 15
                # На Маці api.VerticalAlignment для центру (Excel constant: -4108)
                try:
                    if sys.platform == "win32":
                        # Код для Windows (pywin32)
                        new_row_range.api.VerticalAlignment = -4108
                        new_row_range.api.WrapText = False
                    else:
                        # Код для Mac (appscript)
                        new_row_range.api.vertical_alignment = -4108
                        new_row_range.api.wrap_text = False
                except:
                    pass

                self.logger.debug(f'--- [+] Додано новий запис ID:{current_id} у рядок {target_insert_row}')

                # Переходимо до наступного рядка
                target_insert_row += 1

    def _find_existing_row(self, data_dict: Dict[str, Any]):
        """Шукає номер рядка за ПІБ, Датою народження та РНОКПП через xlwings (Mac-версія)."""

        # 1. Готуємо вхідні дані
        pib = str(data_dict.get(COLUMN_NAME, '')).strip().lower()
        dob = str(data_dict.get(COLUMN_BIRTHDAY, '')).strip()
        rnokpp = str(data_dict.get(COLUMN_ID_NUMBER, '')).strip()
        des_date = str(data_dict.get(COLUMN_DESERTION_DATE, '')).strip()

        # Отримуємо індекси (xlwings 1-indexed)
        idx_map = self.column_map
        pib_col = idx_map.get(COLUMN_NAME.lower())
        dob_col = idx_map.get(COLUMN_BIRTHDAY.lower())
        rnokpp_col = idx_map.get(COLUMN_ID_NUMBER.lower())
        des_col = idx_map.get(COLUMN_DESERTION_DATE.lower())
        ret_col = idx_map.get(COLUMN_RETURN_DATE.lower())
        res_col = idx_map.get(COLUMN_RETURN_TO_RESERVE_DATE.lower())
        id_col = idx_map.get(COLUMN_INCREMEMTAL.lower())

        if not all([pib_col, dob_col, rnokpp_col, des_col]):
            self.logger.error(f"--- ❌ Помилка: Не всі обов'язкові колонки знайдені")
            return None

        self.logger.debug(f'--- 🔎: Пошук в базі: {pib} || {dob} || {rnokpp}')

        try:
            last_row = self.sheet.range((1048576, id_col)).end('up').row
        except Exception:
            last_row = self.sheet.used_range.last_cell.row

        if last_row < 2:
            return None

        # 3. Отримання масиву через чанки (кине Exception при помилці)
        data_range = self._fetch_records_by_chunks(last_row, len(self.column_map))

        # self.logger.debug('--- data length ' + str(len(data_range)))
        # --- ЗАХИСТ ВІД 'NoneType' ---
        if not data_range or not isinstance(data_range, list) or last_row == 1 or not isinstance(data_range, list):
            self.logger.error("⚠️ Критична помилка: Не вдалося зчитати дані з листа")
            return None

        for i, row_data in enumerate(data_range):
            # Додамо ще одну перевірку всередині циклу
            if not row_data or not isinstance(row_data, list):
                continue

            # Індексація в row_data 0-базова, тому всюди -1
            s_pib = row_data[pib_col - 1].lower()
            s_dob = format_ukr_date(row_data[dob_col - 1])
            s_rnokpp = str(row_data[rnokpp_col - 1])
            if s_rnokpp.endswith('.0'): s_rnokpp = s_rnokpp[:-2]
            s_des_date = format_ukr_date(row_data[des_col - 1])

            # Якщо треба змінити значення, використовуємо кортеж для range
            s_ret_date = format_ukr_date(row_data[ret_col - 1])
            s_res_date = format_ukr_date(row_data[res_col - 1])
            # Костиль 31.12.2020
            if s_ret_date == '31.12.2020' or s_res_date == '31.12.2020':
                if s_ret_date == '31.12.2020':
                    s_ret_date = ""
                if s_res_date == '31.12.2020':
                    s_res_date = ""

            # Перевірка збігу
            if s_pib == pib and s_dob == dob and s_rnokpp == rnokpp:
                actual_excel_row = i + 1

                if des_date == s_des_date or (not s_ret_date and not s_res_date):
                    s_id = row_data[id_col - 1]
                    self.logger.debug(f'--- 🔎🤘 Чувака знайдено (ID:{s_id}), рядок {actual_excel_row}' + str(' Попередня Дата повернення:' + str(s_ret_date)))
                    if '31.12.2020' in s_ret_date:
                        self.sheet.range((actual_excel_row, ret_col)).value = None
                    if '31.12.2020' in s_res_date:
                        self.sheet.range((actual_excel_row, res_col)).value = None
                    return actual_excel_row

        self.logger.debug('--- 🔎➕: Чувака немає, додаємо новий рядок')
        return None

    def _fetch_records_by_chunks(self, last_row: int, num_cols: int) -> List[List[Any]]:
        """Зчитує дані з Excel частинами. Кидає помилку, якщо дані не зачитані."""
        chunk_size = EXCEL_CHUNK_SIZE
        all_data = []

        for start_row in range(1, last_row + 1, chunk_size):
            end_row = min(start_row + chunk_size - 1, last_row)
            try:
                # ndim=2 гарантує, що ми завжди отримаємо список списків
                chunk = self.sheet.range((start_row, 1), (end_row, num_cols)).options(ndim=2).value

                if chunk is None:
                    raise ValueError(f"Excel повернув порожній чанк (None) на рядках {start_row}-{end_row}")

                all_data.extend(chunk)

            except Exception as e:
                self.logger.error(f"❌ Критична помилка зчитування чанка {start_row}-{end_row}")
                raise Exception(f"Неможливо прочитати дані Excel: {e}")

        return all_data

    def _build_column_map(self):
        """Створює словник імен колонок для швидкого доступу"""
        if self.sheet:
            header_values = self.sheet.range('1:1').value
            for idx, val in enumerate(header_values):
                if val:
                    clean_name = str(val).strip()
                    clean_name_lower = clean_name.lower()
                    self.column_map[clean_name_lower] = idx + 1
                    self.header[clean_name] = idx + 1

    def _build_column_values(self):
        columns_to_gather = [
            COLUMN_TZK_REGION,
            COLUMN_SUBUNIT,
            COLUMN_SUBUNIT2,
            COLUMN_SERVICE_TYPE,
            COLUMN_TITLE,
            COLUMN_TITLE_2,
            COLUMN_DESERTION_TYPE,
            COLUMN_REVIEW_STATUS,
            COLUMN_DESERTION_PLACE,
            COLUMN_DESERTION_REGION,

            COLUMN_INSERT_DATE,
            COLUMN_DESERTION_DATE,
        ]

        self.column_values = {}

        # 1. Отримуємо заголовки для пошуку індексів
        headers = self.sheet.range('A1').expand('right').value
        header_to_idx = {name: i for i, name in enumerate(headers)}

        # 2. Визначаємо межі даних (остання заповнена строка)
        last_row = self.sheet.range('A' + str(self.sheet.cells.last_cell.row)).end('up').row

        if last_row < 2:
            return {col: [] for col in columns_to_gather}

        for col_name in columns_to_gather:
            if col_name in header_to_idx:
                col_idx = header_to_idx[col_name] + 1  # xlwings індекси з 1

                # Зчитуємо весь стовпець одним махом (від рядка 2 до останнього)
                column_values = self.sheet.range((2, col_idx), (last_row, col_idx)).value
                if not isinstance(column_values, list):
                    column_values = [column_values]

                processed_values = set()
                for v in column_values:
                    if v is None or str(v).strip() == "":
                        continue

                    if isinstance(v, (datetime, date)):
                        processed_values.add(str(v.year))
                    else:
                        processed_values.add(str(v).strip())

                unique = sorted(list(processed_values), key=lambda x: int(x) if x.isdigit() else x)
                self.column_values[col_name] = unique
            else:
                self.column_values[col_name] = []

        return self.column_values

    def _load_workbook(self, sheet_name) -> None:
        try:
            try:
                # Проста перевірка на "вошивість" зв'язку з Excel
                _ = self.app.api
            except:
                self.logger.debug(">> Excel process was dead, restarting...")
                self.app = xw.App(visible=False, add_book=False)

            if self.workbook is None:
                self.logger.debug(f'>> OPENING WORKBOOK: {self.abs_path}')
                self.workbook = self.app.books.open(self.abs_path)
                self.switch_to_sheet(sheet_name)
                self.logger.debug(f'>> EXCEL TOUCHED SUCCESSFULLY, sheet ' + sheet_name)

        except Exception as e:
            # self.logger.debug(f"Помилка ініціалізації Excel: {e}")
            traceback.print_exc()
            raise BaseException(f"⚠️ Помилка ініціалізації Excel: {e}")

    def switch_to_sheet(self, sheet_name, silent=False):
        if not sheet_name:
            raise ValueError(f"Військова частина не визначена!")
        self.sheet = self.workbook.sheets[sheet_name]
        if not silent:
            self._build_column_map()
            self._build_column_values()

    def save(self) -> None:
        if self.workbook is None:
            self.logger.error("⚠️ Спроба зберегти порожній воркбук. Скасовано.")
            return
        try:
            self.workbook.save()
            self.logger.debug(f"--- ✔️ EXCEL УСПІШНО ОНОВЛЕНО")
        except Exception as e:
            self.logger.error(f"❌ Критична помилка при збереженні: {e}")

    def close(self):
        try:
            if self.workbook:
                self.workbook.close()
            # Перевіряємо, чи app ще живий перед тим як вийти
            if self.app and self.app.api:
                self.app.quit()
        except:
            pass
        finally:
            self.workbook = None
            self.app = None

    def __del__(self):
        """Автоматичне закриття при видаленні об'єкта"""
        try:
            self.close()
        except:
            pass


    def get_column_options(self) -> Dict[str, List[str]]:
        return self.column_values

    def search_people(self, filter_obj: PersonSearchFilter) -> list:
        self.switch_to_sheet(DESERTER_TAB_NAME, silent=True)

        results = []
        last_row = self.sheet.range((1048576, 1)).end('up').row

        data = self.sheet.range(f"A2:BB{last_row}").value
        if data is None:
            return results

        q_text = (filter_obj.query or "").lower().strip()
        q_des_year = filter_obj.des_year
        q_des_date_from = date.fromisoformat(filter_obj.des_date_from) if filter_obj.des_date_from else None
        q_des_date_to = date.fromisoformat(filter_obj.des_date_to) if filter_obj.des_date_to else None

        q_order = filter_obj.o_ass_num
        q_title2 = filter_obj.title2
        q_service = filter_obj.service_type
        pib_idx = self.header.get(COLUMN_NAME, 1) - 1
        rnokpp_idx = self.header.get(COLUMN_ID_NUMBER, 1) - 1
        des_date_idx = self.header.get(COLUMN_DESERTION_DATE, 1) - 1
        o_ass_num_idx = self.header.get(COLUMN_ORDER_ASSIGNMENT_NUMBER, 1) - 1
        title2_idx = self.header.get(COLUMN_TITLE_2, 1) - 1
        service_idx = self.header.get(COLUMN_SERVICE_TYPE, 1) - 1

        for i, row in enumerate(data):
            if not row[pib_idx]: continue

            pib_val = str(row[pib_idx]).lower()
            rnokpp_val = get_strint_fromfloat(row[rnokpp_idx])
            o_ass_num_val = get_strint_fromfloat(row[o_ass_num_idx], "")

            des_date = row[des_date_idx]  # mandatory field

            des_date_year = None
            if isinstance(des_date, (datetime, date)):
                des_date_year = str(des_date.year)

            # === ЛОГІКА ФІЛЬТРАЦІЇ ===

            match_text = True
            if q_text:
                match_text = (q_text in pib_val or q_text in rnokpp_val)

            match_des_year = True
            if q_des_year:
                if isinstance(q_des_year, list):
                    match_des_year = (des_date_year in q_des_year)
                else:
                    match_des_year = (des_date_year == str(q_des_year))

            match_des_year_from = True
            match_des_year_to = True

            if q_des_date_from or q_des_date_to:
                if des_date:
                    if isinstance(des_date, datetime):
                        row_des_date = des_date.date()
                    elif isinstance(des_date, date):
                        row_des_date = des_date
                    else:
                        row_des_date = None

                    if row_des_date:
                        if q_des_date_from:
                            match_des_year_from = (row_des_date >= q_des_date_from)
                        if q_des_date_to:
                            match_des_year_to = (row_des_date <= q_des_date_to)
                    else:
                        match_des_year_from = False
                        match_des_year_to = False  # Додано скидання для дати "До"
                else:
                    match_des_year_from = False
                    match_des_year_to = False

            match_order = True
            if q_order:
                match_order = (o_ass_num_val == str(q_order))

            match_title2 = True
            if q_title2:
                row_title = str(row[title2_idx]) if row[title2_idx] else ""
                match_title2 = (row_title == q_title2)

            match_service = True
            if q_service:
                row_service = str(row[service_idx]) if row[service_idx] else ""
                match_service = (row_service == q_service)

            if match_text and match_des_year and match_des_year_from and match_des_year_to and match_order and match_title2 and match_service:
                serialized_row = []
                for cell in row:
                    self._transform_cell(cell, serialized_row)

                results.append({
                    'row_idx': i + 2,
                    'data': dict(zip(self.header, serialized_row))
                })

        return results

    def find_person(self, key: PersonKey) -> dict:
        # self.switch_to_sheet(DESERTER_TAB_NAME, silent=True)

        last_row = self.sheet.range((1048576, 1)).end('up').row
        data = self.sheet.range(f"A2:BB{last_row}").value

        print('find, last row = ' + str(last_row))

        if data is None:
            return None

        pib_idx = self.header.get(COLUMN_NAME, 1) - 1
        rnokpp_idx = self.header.get(COLUMN_ID_NUMBER, 1) - 1
        des_date_idx = self.header.get(COLUMN_DESERTION_DATE, 1) - 1

        target_name = (key.name or "").lower().strip()
        target_rnokpp = (key.rnokpp or "").strip()
        target_des_date = (key.des_date or "").strip()

        for i, row in enumerate(data):
            if not row[pib_idx]:
                continue

            pib_val = str(row[pib_idx]).lower().strip()
            rnokpp_val = get_strint_fromfloat(row[rnokpp_idx], "").strip()

            match_name = (target_name == pib_val) if target_name else True
            match_rnokpp = (target_rnokpp == rnokpp_val) if target_rnokpp else True

            match_bday = True
            if target_des_date:
                des_date_val = format_ukr_date(row[des_date_idx])

                if isinstance(des_date_val, (datetime, date)):
                    match_bday = (target_des_date == str(des_date_val.date()) or target_des_date == des_date_val.strftime("%d.%m.%Y"))
                else:
                    match_bday = (target_des_date == str(des_date_val).strip())

            if match_name and match_rnokpp and match_bday:
                serialized_row = []
                for cell in row:
                    self._transform_cell(cell, serialized_row)

                return {
                    'row_idx': i + 2,
                    'data': dict(zip(self.header, serialized_row))
                }

        return None

    def _transform_cell(self, cell, serialized_row):
        if isinstance(cell, (datetime, date)):
            serialized_row.append(format_to_excel_date(cell))
        elif isinstance(cell, float):
            if cell.is_integer():
                serialized_row.append(int(cell))
            else:
                serialized_row.append(cell)
        else:
            if cell is not None:
                cell = str(cell).strip()
            serialized_row.append(cell)

    def update_row_by_id(self, row_id: int, updated_data: dict, paint_with_color=None):
        try:
            with self.lock:
                headers = self.sheet.range('A1').expand('right').value
                header_map = {name: idx for idx, name in enumerate(headers)}

                ids = self.sheet.range('A2').expand('down').value
                if not isinstance(ids, list):
                    ids = [ids]
                try:
                    target_row_idx = ids.index(row_id) + 2
                except ValueError:
                    self.logger.debug(f"❌ EXCEL, update_row_by_index, ID {row_id} не знайдено в колонці А")
                    return False
                last_col_idx = len(headers)
                row_range = self.sheet.range((target_row_idx, 1), (target_row_idx, last_col_idx))
                if paint_with_color:
                    self._color_row(row_range, paint_with_color)
                row_values = row_range.value
                for col_name, new_value in updated_data.items():
                    if col_name in header_map:
                        idx = header_map[col_name]
                        row_values[idx] = new_value
                row_range.value = row_values

                return True
        except Exception as e:
            self.logger.debug(f"❌ EXCEL, Помилка xlwings: {e}")
            return False

    def _color_row(self, range, hex_color):
        if not hex_color: return
        """Зафарбовує весь рядок (від A до BB) вказаним кольором."""
        range.color = hex_color

    def batch_search_names(self, names_list: List[str]) -> List[Dict[str, Any]]:
        """
        Масовий пошук ПІБ в базі Excel.
        Повертає відсортований список словників: спочатку ті, кого НЕ знайдено (False), потім ті, хто Є (True).
        """
        # Переконуємось, що ми на правильному листі
        self.switch_to_sheet(DESERTER_TAB_NAME, silent=True)

        # 1. Знаходимо колонку з ПІБ
        pib_col_idx = self.column_map.get(COLUMN_NAME.lower()) or self.header.get(COLUMN_NAME)
        if not pib_col_idx:
            self.logger.error(f"❌ Не знайдено колонку {COLUMN_NAME} для масового пошуку")
            return []

        # 2. Визначаємо останній рядок
        try:
            last_row = self.sheet.range((1048576, pib_col_idx)).end('up').row
        except Exception:
            last_row = self.sheet.used_range.last_cell.row

        # 3. Забираємо всю колонку з бази ОДНИМ запитом
        if last_row < 2:
            excel_names_raw = []
        else:
            excel_names_raw = self.sheet.range((2, pib_col_idx), (last_row, pib_col_idx)).value

        if not isinstance(excel_names_raw, list):
            excel_names_raw = [excel_names_raw]

        # 4. Формуємо Set (множину) у нижньому регістрі для миттєвого пошуку
        excel_db_set = set()
        for val in excel_names_raw:
            if val:
                excel_db_set.add(str(val).strip().lower())

        # 5. Перевіряємо кожне ім'я з нашого списку (textarea)
        results = []
        for orig_name in names_list:
            if not orig_name:
                continue

            search_name = str(orig_name).strip().lower()
            is_found = search_name in excel_db_set

            results.append({
                'name': orig_name,  # Зберігаємо оригінальний регістр для красивого виводу
                'found': is_found
            })

        # 6. Сортуємо: спочатку False (хрестики, бо False = 0), потім True (галочки, бо True = 1)
        results.sort(key=lambda x: x['found'])

        return results