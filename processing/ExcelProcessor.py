import xlwings as xw
import os

import io
import warnings
from copy import copy
from config import DESERTER_TAB_NAME, EXCEL_CHUNK_SIZE
from dics.deserter_xls_dic import *
from dics.deserter_xls_dic import NA
from typing import List, Dict, Any
from utils.utils import format_ukr_date, get_typed_value
import traceback
from storage.LoggerManager import LoggerManager

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
            self.logger.warning(f'--- ⚠️ Помилка отримання поточного ID. Останнє значення: {last_val}')
            current_id = 0

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

    def switch_to_sheet(self, sheet_name):
        if not sheet_name:
            raise ValueError(f"Військова частина не визначена!")
        sheet_name = sheet_name
        self.sheet = self.workbook.sheets[sheet_name]
        self._build_column_map()

    def save(self) -> None:
        print('>>> in workbook sqave method')
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