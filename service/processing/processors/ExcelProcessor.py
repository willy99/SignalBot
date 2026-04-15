import xlwings as xw
import os
import warnings
from domain.person_filter import YES
import config
from dics.deserter_xls_dic import *
from dics.deserter_xls_dic import NA
from typing import List, Dict, Any
from utils.utils import format_ukr_date, get_typed_value, format_to_excel_date, get_strint_fromfloat, pythoncom_initialize, is_win
import traceback
from service.storage.LoggerManager import LoggerManager
from datetime import date, datetime
import threading
from domain.person_filter import PersonSearchFilter
from domain.person_key import PersonKey
from functools import wraps

def ensure_com(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs): # Додаємо self, щоб мати доступ до об'єкта
        pythoncom_initialize()
        try:
            # Перед виконанням функції перевіряємо/відновлюємо зв'язок з Excel
            self._refresh_com_connection()
            return func(self, *args, **kwargs)
        finally:
            # Для Windows потоків з NiceGUI краще не робити Uninitialize занадто агресивно
            pass
    return wrapper


class ExcelProcessor:
    def __init__(self, file_path, log_manager: LoggerManager, batch_processing=False, is_test_mode=False):
        pythoncom_initialize()
        self.is_test_mode = is_test_mode
        self.file_path: str = file_path
        self.workbook = None
        self.sheet = None
        self.column_map: Dict[str, int] = {}  # {назва: номер_колонки}
        self.header: Dict[str, int] = {}
        self.batch_processing = batch_processing
        self.logger = log_manager.get_logger()

        warnings.filterwarnings("ignore", category=UserWarning)
        self.abs_path = os.path.abspath(file_path)
        # На Windows краще спочатку перевірити, чи файл взагалі існує
        if not os.path.exists(self.abs_path):
            self.logger.error(f"Файл не знайдено: {self.abs_path}")
            raise FileNotFoundError(f"Excel файл відсутній за шляхом {self.abs_path}")

        self.app = xw.App(visible=True, add_book=False)
        self._load_workbook(config.DESERTER_TAB_NAME) #default tab name
        self.lock = threading.RLock()

        self.column_values: Dict[str, List[str]] = {} # для комбіков
        self._build_global_column_values()

    def _refresh_com_connection(self):
        """Метод для 'оживлення' зв'язку з Excel у новому потоці"""
        try:
            _ = self.app.api
        except Exception:
            self.logger.debug("🔄 Оновлення COM-зв'язку для нового потоку (Daily/Yearly Report)...")
            pythoncom_initialize()
            if xw.apps.count > 0:
                self.app = xw.apps.active
            else:
                self.app = xw.App(visible=True, add_book=False)

            file_name = os.path.basename(self.abs_path)
            try:
                self.workbook = self.app.books[file_name]
            except Exception:
                self.workbook = self.app.books.open(self.abs_path)
            self.sheet = self.workbook.sheets.active

    @ensure_com
    def get_correct_sheet_name(self, mil_unit):
        sheet_name = config.DESERTER_TAB_NAME
        if mil_unit is None:
            return sheet_name
        if mil_unit.find("701") > -1:
            return config.DESERTER_RESERVE_TAB_NAME
        return sheet_name


    @ensure_com
    def upsert_record(self, records_list: List[Dict[str, Any]]) -> bool:
        if not records_list:
            False
        sheet_name = self.get_correct_sheet_name(records_list[0].get(COLUMN_MIL_UNIT, None))
        print('>>>> sheet name: ' + sheet_name + ' and mil unit ' + str(records_list[0].get(COLUMN_MIL_UNIT, None)))
        self._load_workbook(sheet_name)
        self.switch_to_sheet(sheet_name)
        try:
            next_empty_row = self._processRow(records_list)
            self.update_total_formula()

            if not self.batch_processing:
                self.save()
            return True
        except Exception as e:
            self.logger.error(f"❌ Помилка під час upsert_record: {e}. Перевірте, що можете встромити рядок у екселі. По-друге, позбавляйтесь його ;) ")
            traceback.print_exc()
            #if self.workbook:
            #    self.workbook.close()
            #    self.workbook = None
            return False

    def _can_update_cell(self, col_name, current_col_value):
        if col_name == COLUMN_REVIEW_STATUS:
            if current_col_value and str(current_col_value).strip() == REVIEW_STATUS_ERDR:
                return False
        return True

    def _processRow(self, records_list):
        id_col_idx = self.column_map.get(COLUMN_INCREMENTAL.lower())
        if not id_col_idx:
            self.logger.error("❌ Помилка: Не знайдено колонку №. Ексель був пʼян")
            return

        last_row_with_data = self.get_last_row()
        target_insert_row = last_row_with_data + 1
        last_val = self.sheet.range((last_row_with_data, id_col_idx)).value

        try:
            if last_val is not None:
                current_id = int(float(last_val))
            else:
                current_id = 0
        except (ValueError, TypeError):
            if self.is_test_mode:
                current_id = 0
            else:
                raise ValueError(f'--- ⚠️ Помилка отримання поточного ID. Останнє значення: {last_val}')

        self.logger.debug(f'--- Визначено останній ID: {current_id} (з рядка {last_row_with_data})')

        last_col_idx = self.get_last_col()

        # 3. Перебір кожного словника в масиві
        for data_dict in records_list:
            existing_row = self._find_existing_row(data_dict)

            if existing_row:
                for col_name, value in data_dict.items():
                    idx = self.column_map.get(col_name.lower())
                    if idx:
                        # Кортеж тут!
                        current_cell = self.sheet.range((existing_row, idx))
                        if (not current_cell.value or current_cell.value == NA or col_name in OVERRIDE_COLUMNS) and value and self._can_update_cell(col_name, current_cell.value):
                            current_cell.value = get_typed_value(value)
                            self.logger.debug(f'--- [Рядок {existing_row}] оновлюємо {col_name}: {value}')
            else:
                # --- СТВОРЕННЯ НОВОГО ---
                current_id += 1

                # 1. Вставляємо порожній рядок
                # Це гарантує, що ми не копіюємо старі дані
                row_to_fill = self.sheet.range(f'{target_insert_row}:{target_insert_row}')
                row_to_fill.insert(shift='down')

                # Перехоплюємо цей же рядок (бо старий сованувся вниз)
                new_row_ref = self.sheet.range(f'{target_insert_row}:{target_insert_row}')
                new_row_ref.clear_contents()  # Повна зачистка

                # 2. Готуємо "болванку" рядка (масив порожніх значень довжиною в к-ть колонок)
                row_data = [None] * last_col_idx

                # 3. Заповнюємо масив даними
                # (Excel використовує 1-індексацію, масив 0-індексацію, тому idx-1)
                row_data[id_col_idx - 1] = current_id

                for col_name, value in data_dict.items():
                    idx = self.column_map.get(col_name.lower())
                    if idx and idx != id_col_idx and idx < len(row_data):
                        row_data[idx - 1] = get_typed_value(value)

                # 4. ПИШЕМО ВЕСЬ РЯДОК ОДНИМ МАХОМ (це в 10 разів швидше і надійніше)
                self.sheet.range((target_insert_row, 1)).value = row_data

                # 5. Косметика (білий колір та висота)
                new_row_ref.color = (255, 255, 255)
                new_row_ref.row_height = 15

                try:
                    if is_win():
                        new_row_ref.api.VerticalAlignment = -4108  # Центрування
                        new_row_ref.api.WrapText = False
                except:
                    pass

                self.logger.debug(f'--- [+] Додано новий запис ID:{current_id} у рядок {target_insert_row}')
                target_insert_row += 1
        return target_insert_row

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
        id_col = idx_map.get(COLUMN_INCREMENTAL.lower())

        if not all([pib_col, dob_col, rnokpp_col, des_col]):
            self.logger.error(f"--- ❌ Помилка: Не всі обов'язкові колонки знайдені")
            return None

        self.logger.debug(f'--- 🔎: Пошук в базі: {pib} || {dob} || {rnokpp}')

        last_row = self.get_last_row()

        if last_row < 2:
            return None

        # 3. Отримання масиву через чанки (кине Exception при помилці)
        data_range = self._fetch_records_by_chunks(last_row, self.get_last_col())

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
        chunk_size = config.EXCEL_CHUNK_SIZE
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

    def _build_global_column_values(self):
        """Збирає унікальні значення з усіх робочих листів (основний + резерв)"""
        self.logger.debug(">> Збір глобальних значень для комбобоксів...")

        # Створюємо словник зі списками для об'єднання
        columns_to_gather = [
            COLUMN_INSERT_DATE, COLUMN_DESERTION_DATE,
            COLUMN_TZK_REGION, COLUMN_SUBUNIT, COLUMN_SUBUNIT2,
            COLUMN_SERVICE_TYPE, COLUMN_TITLE, COLUMN_TITLE_2,
            COLUMN_DESERTION_TYPE, COLUMN_REVIEW_STATUS,
            COLUMN_DESERTION_PLACE, COLUMN_DESERTION_REGION
        ]

        # Використовуємо set для автоматичної унікальності
        global_sets = {col: set() for col in columns_to_gather}

        # Список листів, з яких ми хочемо витягти довідники
        target_sheets = [MIL_UNITS[0], MIL_UNITS[1]]

        for s_name in target_sheets:
            try:
                self.sheet = self.workbook.sheets[s_name]
                # Отримуємо заголовки конкретного листа
                headers = self.sheet.range('A1').expand('right').value
                header_to_idx = {name: i for i, name in enumerate(headers)}

                # Визначаємо останній рядок на цьому листі
                last_row = self.get_last_row()
                if last_row < 2:
                    continue

                for col_name in columns_to_gather:
                    if col_name in header_to_idx:
                        col_idx = header_to_idx[col_name] + 1
                        # Зчитуємо стовпець
                        values = self.sheet.range((2, col_idx), (last_row, col_idx)).value

                        if not isinstance(values, list):
                            values = [values]

                        for i, v in enumerate(values):
                            if v is None or str(v).strip() == "":
                                continue
                            if isinstance(v, (datetime, date)):
                                global_sets[col_name].add(str(v.year))
                            elif v is not None and str(v).strip() != "":
                                global_sets[col_name].add(str(v).strip())
            except Exception as e:
                self.logger.warning(f"Не вдалося зчитати довідники з листа {s_name}: {e}")

        # Перетворюємо set у відсортовані списки для UI
        self.column_values = {}
        for col_name, val_set in global_sets.items():
            self.column_values[col_name] = sorted(list(val_set))

        self.logger.debug(f">> Глобальні довідники зібрані: {len(target_sheets)} листа опрацьовано")

    def _load_workbook(self, sheet_name) -> None:
        try:
            try:
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

    def _refresh_com_connection(self):
        """Агресивне оновлення зв'язку, яке не боїться чужих потоків"""
        pythoncom_initialize()

        # Замість перевірки self.workbook (яка може бути 'битою'),
        # ми просто намагаємося знайти або підключити книгу заново.
        try:
            # 1. Отримуємо доступ до Excel (чистий виклик)
            if xw.apps.count > 0:
                app = xw.apps.active
            else:
                app = xw.App(visible=True, add_book=False)

            # 2. Підключаємося до книги за назвою файлу
            file_name = os.path.basename(self.abs_path)

            # ВАЖЛИВО: Отримуємо свіжий проксі-об'єкт для поточного потоку
            self.app = app
            self.workbook = app.books[file_name]

            # Тестуємо зв'язок
            _ = self.workbook.name

        except Exception as e:
            self.logger.debug(f"🔄 [COM RECOVERY] Спроба через повне відкриття: {e}")
            try:
                # Якщо книга не знайдена в активних — відкриваємо її явно
                self.workbook = xw.Book(self.abs_path)
                self.app = self.workbook.app
            except Exception as final_e:
                self.logger.error(f"❌ Критична помилка COM: {final_e}")


    @ensure_com
    def switch_to_sheet(self, sheet_name, silent=False):
        if not sheet_name:
            raise ValueError(f"Військова частина не визначена!")

        try:
            # Спроба звернутися до поточного аркуша
            _ = self.sheet.name
            # Якщо потік той самий, ми просто перемикаємо на потрібний
            self.sheet = self.workbook.sheets[sheet_name]
        except Exception:
            # Якщо вилетіла помилка маршалінгу — перепідключаємо книгу
            self.logger.debug(f"🔄 Потік змінився. Перепідключаю книгу для аркуша {sheet_name}")

            # Підключаємося до активного додатка Excel
            if xw.apps.count > 0:
                self.app = xw.apps.active
            else:
                self.app = xw.App(visible=True, add_book=False)

            # Відкриваємо або підключаємося до книги
            self.workbook = self.app.books[os.path.basename(self.abs_path)]
            self.sheet = self.workbook.sheets[sheet_name]

        if not silent:
            self._build_column_map()

    @ensure_com
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

    @ensure_com
    def get_column_options(self) -> Dict[str, List[str]]:
        return self.column_values

    @ensure_com
    def search_people(self, filter_obj: PersonSearchFilter) -> list:
        with self.lock:
            self.switch_to_sheet(filter_obj.mil_unit if filter_obj.mil_unit else config.DESERTER_TAB_NAME , silent=True)

            results = []
            last_row = self.get_last_row()

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
            kpp_num_idx = self.header.get(COLUMN_KPP_NUMBER, 1) - 1
            review_status_idx = self.header.get(COLUMN_REVIEW_STATUS, 1) - 1
            des_region_idx = self.header.get(COLUMN_DESERTION_REGION, 1) - 1
            article_idx = self.header.get(COLUMN_CC_ARTICLE, 1) - 1


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

                match_kpp = True
                if filter_obj.empty_kpp == YES:
                    kpp_num = str(row[kpp_num_idx])
                    safe_val = str(kpp_num).strip().lower()
                    match_kpp = safe_val in ['none', 'nan', 'null', '', '0', '0.0']

                match_status = True
                if filter_obj.review_statuses:
                    review_status = str(row[review_status_idx]).strip()
                    match_status = review_status in filter_obj.review_statuses

                match_402_article = True
                if filter_obj.include_402 is not None and filter_obj.include_402 == False:
                    article = get_strint_fromfloat(row[article_idx])
                    match_402_article = article != '402'

                match_des_region = True
                if filter_obj.desertion_region:
                    desertion_region = str(row[des_region_idx]).strip().lower() if row[des_region_idx] else ''
                    match_des_region = desertion_region == filter_obj.desertion_region.lower()

                if (match_text and match_des_year and match_des_year_from and match_des_year_to and
                        match_order and match_title2 and match_service and match_kpp and match_status and match_des_region and match_402_article):
                    serialized_row = []
                    for cell in row:
                        self._transform_cell(cell, serialized_row)

                    results.append({
                        'row_idx': i + 2,
                        'data': dict(zip(self.header, serialized_row))
                    })

            return results

    @ensure_com
    def find_persons(self, keys: list[PersonKey]) -> dict[str, dict]:
        """
        Шукає групу людей за один прохід по Excel.
        Повертає словник {id_number: {'row_idx': int, 'data': dict}}
        """
        if not keys:
            return {}

        results = {}
        keys_by_unit = {}
        for k in keys:
            unit = k.mil_unit if k.mil_unit else config.DESERTER_TAB_NAME
            keys_by_unit.setdefault(unit, []).append(k)

        with self.lock:
            for unit, unit_keys in keys_by_unit.items():
                self.switch_to_sheet(unit, silent=True)

                last_row = self.get_last_row()
                if last_row < 2:
                    continue

                # Завантажуємо весь лист в пам'ять ОДИН раз для цього підрозділу
                data = self.sheet.range(f"A2:BB{last_row}").value
                if not data:
                    continue

                # Отримуємо індекси колонок
                pib_idx = self.header.get(COLUMN_NAME, 1) - 1
                rnokpp_idx = self.header.get(COLUMN_ID_NUMBER, 1) - 1
                des_date_idx = self.header.get(COLUMN_DESERTION_DATE, 1) - 1

                # Створюємо копію списку ключів, які ще треба знайти (для оптимізації)
                remaining_keys = unit_keys[:]

                for i, row in enumerate(data):
                    if not row[pib_idx] or not remaining_keys:
                        continue

                    pib_val = str(row[pib_idx]).lower().strip()
                    rnokpp_val = get_strint_fromfloat(row[rnokpp_idx], "").strip()
                    des_date_val = format_ukr_date(row[des_date_idx])

                    # Перетворюємо дату з Excel в рядок для порівняння один раз на рядок
                    des_date_str = ""
                    if isinstance(des_date_val, (datetime, date)):
                        des_date_str = des_date_val.strftime("%d.%m.%Y")
                    else:
                        des_date_str = str(des_date_val).strip()

                    # Перевіряємо кожен ключ, який ми шукаємо в цьому листі
                    found_indices = []
                    for idx, key in enumerate(remaining_keys):
                        target_name = (key.name or "").lower().strip()
                        target_rnokpp = (key.rnokpp or "").strip()
                        target_des_date = (key.des_date or "").strip()

                        match_name = (target_name == pib_val) if target_name else True
                        match_rnokpp = (target_rnokpp == rnokpp_val) if (target_rnokpp and target_rnokpp != 'None') else True

                        # Порівняння дати (враховуючи ISO та UKR формати)
                        match_date = True
                        if target_des_date:
                            match_date = (target_des_date == des_date_str or
                                          (isinstance(des_date_val, (datetime, date)) and target_des_date == str(des_date_val.date())))

                        if match_name and match_rnokpp and match_date:
                            # Трансформуємо рядок
                            serialized_row = []
                            for cell in row:
                                self._transform_cell(cell, serialized_row)

                            results[key.uid] = {
                                'row_idx': i + 2,
                                'data': dict(zip(self.header, serialized_row))
                            }
                            found_indices.append(idx)

                    # Видаляємо знайдені ключі, щоб не перевіряти їх на наступних рядках
                    for idx in reversed(found_indices):
                        remaining_keys.pop(idx)

        return results

    @ensure_com
    def find_persons_by_ids(
        self,
        ids: list[int],
        mil_units: list[str] | None = None,
    ) -> dict[int, dict]:
        """
        Шукає рядки в Excel за логічним № (значення колонки A, COLUMN_INCREMENTAL).

        Відрізняється від find_persons тим, що:
          - Не потрібно знати ПІБ або РНОКПП — тільки логічний №
          - Повертає словник {logical_id: {'row_idx': int, 'data': dict}}
            де row_idx = фактичний номер рядка Excel (2-based),
            а logical_id = значення з колонки A (те, що приймає update_row_by_id)

        Використовується у compare_report_view для побудови Person перед save_persons:
            person = Person.from_excel_dict({
                COLUMN_INCREMENTAL: logical_id,   # ← ось що треба update_row_by_id
                COLUMN_MIL_UNIT: mil_unit,
                'Дата СЗЧ': '01.03.2023',
            })

        Args:
            ids:       список логічних № для пошуку
            mil_units: аркуші для пошуку; якщо None — шукаємо по всіх MIL_UNITS

        Returns:
            {logical_id: {'row_idx': int, 'data': dict}} — знайдені записи
        """
        if not ids:
            return {}

        target_units = mil_units or MIL_UNITS
        # Множина для O(1) пошуку — ids можуть бути int або float (Excel повертає float)
        ids_set = {int(i) for i in ids if i is not None}
        results: dict[int, dict] = {}

        with self.lock:
            for unit in target_units:
                if not ids_set:
                    break  # всі знайдено — виходимо

                try:
                    self.switch_to_sheet(unit, silent=True)
                except Exception as e:
                    self.logger.warning(f"find_persons_by_ids: не вдалось переключити аркуш {unit}: {e}")
                    continue

                last_row = self.get_last_row()
                if last_row < 2:
                    continue

                data = self.sheet.range(f"A2:BB{last_row}").value
                if not data:
                    continue

                id_col_idx = self.header.get(COLUMN_INCREMENTAL, 1) - 1

                for i, row in enumerate(data):
                    if not row or not row[id_col_idx]:
                        continue

                    raw_id = row[id_col_idx]
                    try:
                        logical_id = int(float(raw_id))
                    except (ValueError, TypeError):
                        continue

                    if logical_id not in ids_set:
                        continue

                    serialized: list = []
                    for cell in row:
                        self._transform_cell(cell, serialized)

                    row_data = dict(zip(self.header, serialized))
                    row_data[COLUMN_MIL_UNIT] = unit  # гарантуємо наявність mil_unit

                    results[logical_id] = {
                        'row_idx':  i + 2,   # фактичний рядок Excel (для логів)
                        'data':     row_data,
                    }
                    ids_set.discard(logical_id)

        if ids_set:
            self.logger.debug(
                f"find_persons_by_ids: не знайдено {len(ids_set)} записів: {ids_set}"
            )

        return results

    @ensure_com
    def find_person(self, key: PersonKey) -> dict:
        with self.lock:
            if key.mil_unit:
                self.switch_to_sheet(key.mil_unit, silent=True)
            else:
                self.switch_to_sheet(config.DESERTER_TAB_NAME, silent=True)

            last_row = self.get_last_row()
            data = self.sheet.range(f"A2:BB{last_row}").value

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
                match_rnokpp = (target_rnokpp == rnokpp_val) if (target_rnokpp and target_rnokpp != 'None') else True

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

    @ensure_com
    def delete_record(self, row_id: int, mil_unit: str) -> bool:
        try:
            with self.lock:
                self.switch_to_sheet(mil_unit, silent=True)
                ids = self.sheet.range('A2').expand('down').value

                if not isinstance(ids, list):
                    ids = [ids]

                try:
                    target_row_idx = ids.index(row_id) + 2
                except ValueError:
                    self.logger.debug(f"❌ EXCEL, delete_record, ID {row_id} не знайдено в колонці А")
                    return False

                self.sheet.range(f"{target_row_idx}:{target_row_idx}").delete()

                self.logger.debug(f"✅ EXCEL: Рядок з ID {row_id} (рядок {target_row_idx}) успішно видалено.")
                return True

        except Exception as e:
            self.logger.debug(f"❌ EXCEL, Помилка видалення xlwings: {e}")
            return False

    @ensure_com
    def update_row_by_id(self, row_id: int, updated_data: dict, paint_with_color=None):
        try:
            with self.lock:
                mil_unit = updated_data[COLUMN_MIL_UNIT] if updated_data[COLUMN_MIL_UNIT] else MIL_UNITS[0]
                self.switch_to_sheet(mil_unit, silent=True)

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
                last_col_idx = self.get_last_col()
                row_range = self.sheet.range((target_row_idx, 1), (target_row_idx, last_col_idx))
                if paint_with_color:
                    self._color_row(row_range, paint_with_color)

                current_values = row_range.value
                new_values = list(current_values)

                for col_name, new_val in updated_data.items():
                    if col_name in header_map:
                        idx = header_map[col_name]
                        current_val_in_cell = current_values[idx]

                        # --- ЛОГІКА ЗАХИСТУ КОМІРКИ ---
                        if col_name == COLUMN_REVIEW_STATUS:
                            if str(current_val_in_cell).strip() == REVIEW_STATUS_ERDR:
                                self.logger.debug(f"--- [Skip Column] Статус ЄРДР вже встановлено для ID {row_id}, не затираємо.")
                                continue
                        new_values[idx] = get_typed_value(new_val)
                row_range.value = new_values

                return True
        except Exception as e:
            self.logger.debug(f"❌ EXCEL, Помилка xlwings: {e}")
            return False

    def _color_row(self, range, hex_color):
        if not hex_color: return
        """Зафарбовує весь рядок (від A до BB) вказаним кольором."""
        range.color = hex_color

    @ensure_com
    def batch_search_names(self, names_list: List[str]) -> List[Dict[str, Any]]:
        self.switch_to_sheet(config.DESERTER_TAB_NAME, silent=True)

        # 1. Отримуємо індекси колонок
        pib_idx = self.column_map.get(COLUMN_NAME.lower())
        rnokpp_idx = self.column_map.get(COLUMN_ID_NUMBER.lower())

        last_row = self.get_last_row()
        if last_row < 2:
            return [{'name': n, 'found': False, 'rnokpp': None} for n in names_list]

        # 2. Забираємо дані обох колонок одним запитом (діапазон від A до останньої потрібної)
        # Щоб не гадати з буквами, візьмемо весь рядок даних з 2 по last_row
        # Або точково, якщо колонки далеко:
        data_range = self.sheet.range((2, 1), (last_row, self.get_last_col())).value

        # 3. Формуємо словник для швидкого пошуку: { "прізвище": "код" }
        # Використовуємо словник, щоб дістати РНОКПП за ПІБ
        db_map = {}
        for row in data_range:
            name_val = row[pib_idx - 1]  # xlwings 1-based, list 0-based
            if name_val:
                name_key = str(name_val).strip().lower()
                code_val = row[rnokpp_idx - 1] if rnokpp_idx else None
                # Якщо знайдено, зберігаємо код (чистимо від .0 якщо це float з Excel)
                db_map[name_key] = get_strint_fromfloat(code_val) if code_val else "---"

        # 4. Перевіряємо список
        results = []
        for orig_name in names_list:
            search_name = str(orig_name).strip().lower()
            found = search_name in db_map

            results.append({
                'name': orig_name,
                'found': found,
                'rnokpp': db_map.get(search_name) if found else None
            })

        # Сортування: спочатку не знайдені
        results.sort(key=lambda x: x['found'])
        return results

    @ensure_com
    def update_total_formula(self):
        """
        Вставляє формулу =SUBTOTAL(...) у колонку 'I' під останнім записом.
        target_row - рядок, куди треба вставити формулу.
        """
        last_data_row = self.get_last_row() + 1
        formula_str = f"=SUBTOTAL(103, $I$2:$I${last_data_row-1})"

        try:
            cell = self.sheet.range(f'I{last_data_row}')
            cell.formula = formula_str
            try:
                if is_win():
                    cell.api.Font.Bold = True
                else:
                    cell.api.font_object.bold = True
            except:
                pass
        except Exception as e:
            self.logger.error(f"❌ Помилка при оновленні формули SUBTOTAL: {e}")

    @ensure_com
    def get_last_col(self):
        headers = self.sheet.range('A1').expand('right').value
        return len(headers)

    @ensure_com
    def get_last_row(self):
        # last_row = self.sheet.used_range.last_cell.row
        last_row = self.sheet.range('A1048576').end('up').row
        print('>>> last row :: ' + str(last_row))
        return last_row