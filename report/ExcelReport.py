from datetime import datetime, date
from typing import Any, Optional
import traceback
import config
from dics.deserter_xls_dic import *
from collections import defaultdict
from storage.LoggerManager import LoggerManager
from config import DESERTER_TAB_NAME
from utils.utils import get_strint_fromfloat
from domain.person_filter import PersonSearchFilter

class ExcelReporter:
    def __init__(self, excelProcessor, log_manager: LoggerManager):
        # Завантажуємо файл у режимі read_only для швидкості
        self.excelProcessor = excelProcessor
        self.logger = log_manager.get_logger()


    def get_subunit_desertion_stats(self, search_filter: PersonSearchFilter):
        """Збирає повну статистику по підрозділах, званнях та термінах СЗЧ."""
        self.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME)
        try:
            # Ініціалізуємо вкладений словник (автоматично створює гілки)

            def get_stats_template():
                return {
                    'under_3': 0, 'over_3': 0,
                    'ret_mu': 0, 'ret_res': 0,
                    REVIEW_STATUS_NOT_ASSIGNED: 0,
                    REVIEW_STATUS_EXECUTING: 0,
                    REVIEW_STATUS_CLOSED: 0,
                    REVIEW_STATUS_NON_ERDR: 0,
                    REVIEW_STATUS_ERDR: 0,
                    REVIEW_STATUS_NON_EVIL: 0,
                    'dupl': 0,
                    'un_des': 0, 'un_ret': 0,
                    'st_term': 0, 'st_call': 0, 'st_contr': 0,
                    'pl_ppd': 0, 'pl_rvbz': 0, 'pl_other': 0,
                    'weapon': 0,
                    'rev_specified': 0,
                    'rev_dbr_notif': 0,
                    'rev_dbr_mater': 0,
                    'rev_dbr_nonerdr': 0,
                    'rev_dbr_erdr': 0,
                    'rev_suspend': 0,
                    'rev_courts': 0,
                    'rev_punish': 0,
                    'rev_nonevil': 0,
                }

            stats = defaultdict(lambda: defaultdict(lambda: {
                'рядовий_сержант': get_stats_template(),
                'офіцер': get_stats_template(),
                'сержант': get_stats_template(),
                'рядовий': get_stats_template(),
                'all': get_stats_template(),
            }))

            q_des_year = search_filter.des_year
            q_des_date_from = date.fromisoformat(search_filter.des_date_from) if search_filter.des_date_from else None
            q_des_date_to = date.fromisoformat(search_filter.des_date_to) if search_filter.des_date_to else None

            # Отримуємо індекси стовпців з вашого column_map
            name_idx: Final[int] = self.excelProcessor.header.get(COLUMN_NAME) - 1
            id_idx: Final[int] = self.excelProcessor.header.get(COLUMN_ID_NUMBER) - 1
            unit_idx: Final[int] = self.excelProcessor.header.get(COLUMN_SUBUNIT) - 1
            sub_unit_idx: Final[int] = self.excelProcessor.header.get(COLUMN_SUBUNIT2) - 1
            rank_idx: Final[int] = self.excelProcessor.header.get(COLUMN_TITLE_2) - 1
            des_date_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DESERTION_DATE) - 1
            ret_mu_idx: Final[int] = self.excelProcessor.header.get(COLUMN_RETURN_DATE) -1
            ret_res_idx: Final[int] = self.excelProcessor.header.get(COLUMN_RETURN_TO_RESERVE_DATE) - 1
            exp_review_idx: Final[int] = self.excelProcessor.header.get(COLUMN_REVIEW_STATUS) - 1
            where_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DESERTION_PLACE) - 1
            service_type_idx: Final[int] = self.excelProcessor.header.get(COLUMN_SERVICE_TYPE) - 1

            kpp_date_idx: Final[int] = self.excelProcessor.header.get(COLUMN_KPP_DATE) - 1
            kpp_num_idx: Final[int] = self.excelProcessor.header.get(COLUMN_KPP_NUMBER) - 1
            dbr_date_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DBR_DATE) - 1
            dbr_num_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DBR_NUMBER) - 1
            suspended_idx: Final[int] = self.excelProcessor.header.get(COLUMN_SUSPENDED) - 1
            des_type_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DESERTION_TYPE) - 1

            # Читаємо весь заповнений діапазон

            last_row = self.excelProcessor.sheet.range((65536, 1)).end('up').row
            data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value

            people_history = defaultdict(list)

            if data is None:
                return stats

            processed = 0
            for i, row in enumerate(data):
                # filter date
                des_date = row[des_date_idx] # mandatory field
                des_date_year = str(des_date.year) if des_date is not None else None

                ret_mu_date = row[ret_mu_idx]
                ret_mu_date_year = str(ret_mu_date.year) if ret_mu_date is not None else None
                ret_res_date = row[ret_res_idx]
                ret_res_date_year = str(ret_res_date.year) if ret_res_date is not None else None

                kpp_date = row[kpp_date_idx]
                kpp_date_year = str(kpp_date.year) if kpp_date is not None else None
                kpp_num = row[kpp_num_idx]
                dbr_date = row[dbr_date_idx]
                dbr_date_year = str(dbr_date.year) if dbr_date is not None else None
                dbr_num = row[dbr_num_idx]

                name = str(row[name_idx]).strip()
                id_number = get_strint_fromfloat(row[id_idx], "")
                unit = str(row[unit_idx] or "Не вказано").strip()
                where = str(row[where_idx] or "Не вказано").strip()
                service_type = str(row[service_type_idx] or "Не вказано").strip()
                des_type = str(row[des_type_idx] or "Не вказано").strip()
                sub_unit = str(row[sub_unit_idx] or "Не вказано").strip()
                rank = str(row[rank_idx] or "").lower().strip()
                officer_keywords = ['офіцер']
                sergeant_keywords = ['сержант']
                is_officer = any(word in rank for word in officer_keywords)
                is_sergeant = any(word in rank for word in sergeant_keywords)
                rank_key = 'офіцер' if is_officer else 'рядовий_сержант'

                suspended = str(row[suspended_idx]).strip()
                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ СЗЧ

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

                match_period = match_des_year and match_des_year_from and match_des_year_to

                # duplicates for subunits
                mil_unit_key = f"{unit}_{sub_unit}"
                name_key = f"{id_number}_{name}"

                # 1. Отримуємо список дублікатів (якщо немає - створюємо порожній)
                review_status = str(row[exp_review_idx]).strip().lower()

                rank_separated_key = 'офіцер' if is_officer else 'сержант' if is_sergeant else 'рядовий'  # для класифіц. звіту
                people_history[name_key].append({
                    'des_date': des_date,  # дата СЗЧ
                    'ret_mu_date': ret_mu_date,  # дата повернення
                    'ret_res_date': ret_res_date,  # дата повернення в брез
                    'unit': unit,
                    'sub_unit': sub_unit,
                    'rank': rank_separated_key,
                    'service_type': service_type
                })

                if match_period:

                    try:
                        if ret_mu_date:
                            days = (ret_mu_date -  des_date).days
                            if days < 0:
                                self.logger.error(f"❌ Як би альо, в чувака сзч пізніше дати повернення: {name_key} Тікав: {str(des_date)}, повернувся: {str(ret_mu_date)}")
                        else:
                            days = 4
                    except ValueError:
                        days = 0
                    period_key = 'under_3' if days <= 3 else 'over_3'
                    stats[unit][sub_unit][rank_key][period_key] += 1

                    # статус відпрацювання
                    for review_key, value in REVIEW_STATUS_MAP.items():
                        if review_status in value:
                            stats[unit][sub_unit]['all'][review_key] += 1

                    # унікальні сзч та повернення
                    if where in ['РВБЗ']:
                        stats[unit][sub_unit]['all']['pl_rvbz'] += 1
                    elif where in ['ППД']:
                        stats[unit][sub_unit]['all']['pl_ppd'] += 1
                    else: stats[unit][sub_unit]['all']['pl_other'] += 1

                    if des_type == DESERTION_TYPE_WEAPON_KEYWORD:
                        stats[unit][sub_unit]['all']['weapon'] += 1
                    stats[unit][sub_unit]['all']['rev_specified'] = 0 # const
                    stats[unit][sub_unit]['офіцер']['rev_specified'] = 0 # const

                    if (not q_des_year or kpp_date_year in q_des_year) and kpp_num is not None:
                        stats[unit][sub_unit]['all']['rev_dbr_notif'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_dbr_notif'] += 1

                    if (not q_des_year or dbr_date_year in q_des_year) and dbr_num is not None:
                        stats[unit][sub_unit]['all']['rev_dbr_mater'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_dbr_mater'] += 1

                    if review_status in REVIEW_STATUS_MAP[REVIEW_STATUS_NON_ERDR]:
                        stats[unit][sub_unit]['all']['rev_dbr_nonerdr'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_dbr_nonerdr'] += 1
                    if review_status in REVIEW_STATUS_MAP[REVIEW_STATUS_ERDR]:
                        stats[unit][sub_unit]['all']['rev_dbr_erdr'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_dbr_erdr'] += 1

                    if suspended == SUSPENDED_KEYWORD:
                        stats[unit][sub_unit]['all']['rev_suspend'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_suspend'] += 1

                    stats[unit][sub_unit]['all']['rev_courts'] = 0 # const
                    stats[unit][sub_unit]['офіцер']['rev_courts'] = 0 # const

                    stats[unit][sub_unit]['all']['rev_punish'] = 0 # const
                    stats[unit][sub_unit]['офіцер']['rev_punish'] = 0 # const

                    if review_status in REVIEW_STATUS_MAP[REVIEW_STATUS_NON_EVIL]:
                        stats[unit][sub_unit]['all']['rev_nonevil'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_nonevil'] += 1

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ ПОВЕРНЕННЯ В ВЧ
                row_ret_mu_date = None
                if ret_mu_date:
                    row_ret_mu_date = ret_mu_date.date() if isinstance(ret_mu_date, datetime) else ret_mu_date

                if row_ret_mu_date and match_period:
                    # Перевіряємо, чи вписується дата повернення у фільтри
                    match_ret_mu_year = (not q_des_year) or (ret_mu_date_year in q_des_year)
                    match_ret_mu_from = (not q_des_date_from) or (row_ret_mu_date >= q_des_date_from)
                    match_ret_mu_to = (not q_des_date_to) or (row_ret_mu_date <= q_des_date_to)

                    if match_ret_mu_year and match_ret_mu_from and match_ret_mu_to:
                        stats[unit][sub_unit][rank_key]['ret_mu'] += 1

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ ПОВЕРНЕННЯ В РЕЗЕРВ
                row_ret_res_date = None
                if ret_res_date:
                    row_ret_res_date = ret_res_date.date() if isinstance(ret_res_date, datetime) else ret_res_date

                if row_ret_res_date and match_period:
                    # Перевіряємо, чи вписується дата повернення в резерв у фільтри
                    match_ret_res_year = (not q_des_year) or (ret_res_date_year in q_des_year)
                    match_ret_res_from = (not q_des_date_from) or (row_ret_res_date >= q_des_date_from)
                    match_ret_res_to = (not q_des_date_to) or (row_ret_res_date <= q_des_date_to)

                    if match_ret_res_year and match_ret_res_from and match_ret_res_to:
                        stats[unit][sub_unit][rank_key]['ret_res'] += 1

                processed+=1

            # unique calculation for filtered year
            for name_key, cases in people_history.items():

                cases.sort(key=lambda x: x['des_date'])
                last_case = cases[-1]

                last_des_date = last_case['des_date']
                if isinstance(last_des_date, datetime):
                    last_des_date = last_des_date.date()

                match_year = (not q_des_year) or (str(last_des_date.year) in q_des_year)
                match_from = (not q_des_date_from) or (last_des_date >= q_des_date_from)
                match_to = (not q_des_date_to) or (last_des_date <= q_des_date_to)

                if match_year and match_from and match_to:

                    unit = last_case['unit']
                    sub_unit = last_case['sub_unit']
                    rank = last_case['rank']
                    service_type = last_case['service_type']

                    if last_case['ret_mu_date'] is None or last_case['ret_res_date'] == "":
                        stats[unit][sub_unit][rank]['un_des'] += 1
                    else:
                        stats[unit][sub_unit][rank]['un_ret'] += 1

                    if len(cases) > 1:
                        stats[unit][sub_unit][rank]['dupl'] += 1
                    else:
                        service_map = {
                            'призивом': 'st_call',
                            'контрактом': 'st_contr'
                        }
                        service_key = service_map.get(service_type, 'st_term')
                        stats[unit][sub_unit]['all'][service_key] += 1

            return stats
        except Exception as e:
            traceback.print_exc()
            return []






    def get_summary_report(self) -> str:
        """Генерує текстовий звіт по СЗЧ за допомогою xlwings."""
        total_count = 0
        today_count = 0
        today = datetime.now().date()

        # В xlwings індекси стовпців часто базуються на 1 (як в Excel),
        # тому для роботи зі списками Python нам знадобиться (index - 1)
        pib_idx = self.excelProcessor.column_map.get(COLUMN_NAME.lower())
        date_added_idx = self.excelProcessor.column_map.get(COLUMN_INSERT_DATE.lower())
        id_idx = self.excelProcessor.column_map.get(COLUMN_INCREMEMTAL.lower())

        if not all([id_idx, pib_idx, date_added_idx]):
            return "❌ Помилка: Не знайдено необхідні стовпці для звіту."

        # Отримуємо останній рядок
        last_row = self.excelProcessor.sheet.range('A' + str(self.excelProcessor.sheet.cells.last_cell.row)).end(
            'up').row

        if last_row < 2:
            return "📊 База порожня."

        # Зчитуємо всі дані одним махом (це значно швидше, ніж ітерація по клітинках)
        # Зверни увагу: ми беремо діапазон від 2-го рядка до останнього
        data = self.excelProcessor.sheet.range((2, 1),
                                               (last_row, self.excelProcessor.sheet.used_range.columns.count)).value

        # Якщо в таблиці лише один рядок даних, xlwings поверне список, а не список списків.
        # Робимо перевірку, щоб завжди працювати з матрицею.
        if last_row == 2:
            data = [data]

        for row in data:
            # В xlwings індекси у списку data відповідають (index - 1)
            pib_value = row[pib_idx - 1]
            date_val = row[date_added_idx - 1]

            # 1. Рахуємо загальну кількість (якщо є ПІБ)
            if pib_value and str(pib_value).strip():
                total_count += 1

                # 2. Рахуємо кількість за сьогодні
                # xlwings автоматично конвертує дати Excel в об'єкти datetime Python
                if date_val:
                    if self._is_today(date_val, today):
                        today_count += 1

        return (
            "📊 *ЩОДЕННИЙ ЗВІТ ПО БАЗІ СЗЧ*\n"
            "━━━━━━━━━━━━━━━\n"
            f"📈 Всього записів у базі: *{total_count}*\n"
            f"📅 Внесено за сьогодні: *{today_count}*\n"
            "━━━━━━━━━━━━━━━\n"
            f"🕒 Дата звіту: {today.strftime(config.EXCEL_DATE_FORMAT)}"
        )

    def get_montly_report(self) -> str:
        """Генерує текстовий звіт по СЗЧ із групуванням по місяцях."""
        total_count = 0
        today_count = 0
        # Словник для статистики: {"2026-02": 10, "2026-01": 25}
        monthly_stats = defaultdict(int)

        today = datetime.now().date()

        pib_idx = self.excelProcessor.column_map.get(COLUMN_NAME.lower())
        date_added_idx = self.excelProcessor.column_map.get(COLUMN_INSERT_DATE.lower())
        id_idx = self.excelProcessor.column_map.get(COLUMN_INCREMEMTAL.lower())

        if not id_idx or not pib_idx or not date_added_idx:
            return "❌ Помилка: Не знайдено необхідні стовпці для звіту."

        for row in self.excelProcessor.sheet.iter_rows(min_row=2, values_only=True):
            pib_value = row[pib_idx - 1]
            date_val = row[date_added_idx - 1]

            if pib_value and str(pib_value).strip():
                total_count += 1

                if date_val:
                    # Перетворюємо значення в об'єкт datetime
                    dt_obj = self._parse_date(date_val)
                    if dt_obj:
                        # 1. Перевірка на сьогодні
                        if dt_obj.date() == today:
                            today_count += 1

                        # 2. Групування YYYY-MM
                        month_key = dt_obj.strftime("%Y-%m")
                        monthly_stats[month_key] += 1

        # Формуємо блок статистики по місяцях
        monthly_report_lines = []
        # Сортуємо ключі, щоб найновіші місяці були зверху
        for m_key in sorted(monthly_stats.keys(), reverse=True):
            monthly_report_lines.append(f"🗓 {m_key}: *{monthly_stats[m_key]}*")

        monthly_block = "\n".join(monthly_report_lines)

        return (
            "📊 *ЗВІТ ПО БАЗІ СЗЧ*\n"
            "━━━━━━━━━━━━━━━\n"
            f"📈 Всього записів: *{total_count}*\n"
            f"📅 Внесено за сьогодні: *{today_count}*\n"
            "━━━━━━━━━━━━━━━\n"
            "*Статистика по місяцях:*\n"
            f"{monthly_block}\n"
            "━━━━━━━━━━━━━━━\n"
            f"🕒 Дата звіту: {today.strftime('%d.%m.%Y')}"
        )

    def get_dupp_names_report(self) -> Dict[str, List[Dict[str, Any]]]:
        # Отримуємо індекси колонок (переконайтеся, що константи імпортовані)
        name_idx = self.excelProcessor.header.get(COLUMN_NAME) - 1
        id_idx = self.excelProcessor.header.get(COLUMN_ID_NUMBER) - 1
        birth_idx = self.excelProcessor.header.get(COLUMN_BIRTHDAY) - 1
        des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE) - 1

        last_row = self.excelProcessor.sheet.range((65536, 1)).end('up').row
        data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value

        # 1. Словник для збору ВСІХ записів по кожному імені
        people_history = defaultdict(list)

        if not data:
            return {}

        # ЕТАП 1: Групуємо всі рядки за іменем
        for row in data:
            if not row:
                continue

            name = str(row[name_idx]).strip()
            # Пропускаємо порожні імена
            if not name or name == 'None':
                continue

            id_number = get_strint_fromfloat(row[id_idx], "").strip()

            # Додаємо запис в історію цієї людини
            people_history[name].append({
                'des_date': row[des_date_idx],
                'id_number': id_number,
                'birthday': row[birth_idx],
            })

        # 2. Словник ТІЛЬКИ для тих, у кого збігається ПІБ, але різні ІПН
        dupp_names = {}

        # ЕТАП 2: Фільтруємо зібрані дані
        for name, records in people_history.items():
            # Збираємо всі унікальні ІПН для цього імені
            # if r['id_number'] відкидає порожні значення (якщо в одній з карток ІПН просто не вказали)
            unique_ids = set(r['id_number'] for r in records if r['id_number'])

            if len(unique_ids) > 1:
                dupp_names[name] = records

        return dupp_names

    @staticmethod
    def _is_today(cell_value: Any, today_date: datetime.date) -> bool:
        """Перевіряє, чи збігається дата в клітинці з сьогоднішньою."""
        dt_obj = ExcelReporter._parse_date(cell_value)
        return dt_obj.date() == today_date if dt_obj else False

    @staticmethod
    def _parse_date(cell_value: Any) -> Optional[datetime]:
        """Універсальний парсер дати на основі форматів з конфігу."""
        if isinstance(cell_value, datetime):
            return cell_value

        if isinstance(cell_value, str):
            # Прибираємо зайві пробіли
            clean_val = cell_value.strip()
            for fmt in config.EXCEL_DATE_FORMATS_REPORT:
                try:
                    return datetime.strptime(clean_val, fmt)
                except ValueError:
                    continue
        return None
