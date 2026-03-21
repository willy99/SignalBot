from datetime import datetime, date
from typing import Any, Optional
import traceback
import config
from dics.deserter_xls_dic import *
from collections import defaultdict

from service.constants import DB_DATE_FORMAT
from service.processing.DocumentProcessingService import DocumentProcessingService
from service.storage.LoggerManager import LoggerManager
from config import DESERTER_TAB_NAME, EXCEL_DATE_FORMAT
from utils.utils import get_strint_fromfloat, get_year_safe
from domain.person_filter import PersonSearchFilter
import re
import os

class ExcelReporter:
    def __init__(self, excelProcessor, log_manager: LoggerManager):
        self.excelProcessor = excelProcessor
        self.logger = log_manager.get_logger()
        self.log_manager = log_manager



    def _is_today(self, cell_value: Any, today_date: datetime.date) -> bool:
        """Перевіряє, чи збігається дата в клітинці з сьогоднішньою."""
        dt_obj = self._parse_date(cell_value)
        return dt_obj.date() == today_date if dt_obj else False

    def _parse_date(self, cell_value: Any) -> Optional[datetime]:
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

    def get_subunit_desertion_stats(self, search_filter: PersonSearchFilter):
        """Збирає повну статистику по підрозділах, званнях та термінах СЗЧ."""
        self.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME)
        try:
            def get_stats_template():
                return {
                    'under_3': 0, 'over_3': 0,
                    'ret_mu': 0, 'ret_res': 0,
                    REVIEW_STATUS_NOT_ASSIGNED: 0,
                    REVIEW_STATUS_EXECUTING: 0,
                    REVIEW_STATUS_CLOSED: 0,
                    REPORT_REVIEW_STATUS_NON_ERDR: 0,
                    REPORT_REVIEW_STATUS_ERDR: 0,
                    REPORT_REVIEW_STATUS_NON_EVIL: 0,
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
            article_idx: Final[int] = self.excelProcessor.header.get(COLUMN_CC_ARTICLE) - 1

            last_row = self.excelProcessor.get_last_row()
            data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value

            people_history = defaultdict(list)

            if data is None:
                return stats

            processed = 0
            for i, row in enumerate(data):
                # filter date
                des_date = row[des_date_idx] # mandatory field
                des_date_year = get_year_safe(des_date)

                ret_mu_date = row[ret_mu_idx]
                ret_mu_date_year = get_year_safe(ret_mu_date)
                ret_res_date = row[ret_res_idx]
                ret_res_date_year = get_year_safe(ret_res_date)

                kpp_date = row[kpp_date_idx]
                kpp_date_year = get_year_safe(kpp_date)
                kpp_num = row[kpp_num_idx]
                dbr_date = row[dbr_date_idx]
                dbr_date_year = get_year_safe(dbr_date)
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

                cc_article = get_strint_fromfloat(str(row[article_idx]))

                suspended = str(row[suspended_idx]).strip()

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ СЗЧ
                if not search_filter.include_402:
                    match_exclude_article = cc_article in REPORT_SUBUNIT_EXCLUDE_ARTICLES
                    if match_exclude_article:
                        continue

                match_des_year = True
                des_year_less_equal = True

                if q_des_year:
                    if isinstance(q_des_year, list):
                        match_des_year = (des_date_year in q_des_year)
                    else:
                        match_des_year = (des_date_year == str(q_des_year))

                    if str(des_date_year).isdigit():
                        row_year_int = int(des_date_year)

                        if isinstance(q_des_year, list) and q_des_year:
                            valid_filter_years = [int(y) for y in q_des_year if str(y).isdigit()]
                            if valid_filter_years:
                                max_filter_year = max(valid_filter_years)
                                des_year_less_equal = (row_year_int <= max_filter_year)
                            else:
                                des_year_less_equal = False
                        else:
                            if str(q_des_year).isdigit():
                                des_year_less_equal = (row_year_int <= int(q_des_year))
                            else:
                                des_year_less_equal = False
                    else:
                        des_year_less_equal = False

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
                review_status = str(row[exp_review_idx]).strip()

                rank_separated_key = 'офіцер' if is_officer else 'сержант' if is_sergeant else 'рядовий'  # для класифіц. звіту
                if des_year_less_equal:
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

                    if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_ERDR]:
                        stats[unit][sub_unit]['all']['rev_dbr_nonerdr'] += 1
                        if is_officer:
                            stats[unit][sub_unit]['офіцер']['rev_dbr_nonerdr'] += 1
                    if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_ERDR]:
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

                    if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_EVIL]:
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

                    if len(cases) > 1:
                        stats[unit][sub_unit][rank]['dupl'] += 1
                    else:
                        service_map = {
                            'призивом': 'st_call',
                            'контрактом': 'st_contr'
                        }
                        service_key = service_map.get(service_type, 'st_term')
                        stats[unit][sub_unit]['all'][service_key] += 1

                        # unique cases
                        stats[unit][sub_unit][rank]['un_des'] += 1
                        if last_case['ret_mu_date'] or last_case['ret_res_date']:
                            stats[unit][sub_unit][rank]['un_ret'] += 1


            return stats
        except Exception as e:
            traceback.print_exc()
            return []

    def get_yearly_desertion_stats(self):
        """Збирає статистику виключно по роках (по року СЗЧ), без жодних фільтрів."""
        self.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME)
        try:
            def get_stats_template():
                return {
                    'under_3': 0, 'over_3': 0, 'ret_mu': 0, 'ret_res': 0,
                    REVIEW_STATUS_NOT_ASSIGNED: 0, REVIEW_STATUS_EXECUTING: 0, REVIEW_STATUS_CLOSED: 0,
                    REPORT_REVIEW_STATUS_NON_ERDR: 0, REPORT_REVIEW_STATUS_ERDR: 0, REPORT_REVIEW_STATUS_NON_EVIL: 0,
                    'dupl': 0, 'un_des': 0, 'un_ret': 0,
                    'st_term': 0, 'st_call': 0, 'st_contr': 0,
                    'pl_ppd': 0, 'pl_rvbz': 0, 'pl_other': 0,
                    'weapon': 0, 'rev_specified': 0, 'rev_dbr_notif': 0, 'rev_dbr_mater': 0,
                    'rev_dbr_nonerdr': 0, 'rev_dbr_erdr': 0, 'rev_suspend': 0,
                    'rev_courts': 0, 'rev_punish': 0, 'rev_nonevil': 0,
                }

            stats = defaultdict(lambda: {
                'рядовий_сержант': get_stats_template(),
                'офіцер': get_stats_template(),
                'сержант': get_stats_template(),
                'рядовий': get_stats_template(),
                'all': get_stats_template(),
            })

            # Отримуємо індекси стовпців
            name_idx: Final[int] = self.excelProcessor.header.get(COLUMN_NAME) - 1
            id_idx: Final[int] = self.excelProcessor.header.get(COLUMN_ID_NUMBER) - 1
            rank_idx: Final[int] = self.excelProcessor.header.get(COLUMN_TITLE_2) - 1
            des_date_idx: Final[int] = self.excelProcessor.header.get(COLUMN_DESERTION_DATE) - 1
            ret_mu_idx: Final[int] = self.excelProcessor.header.get(COLUMN_RETURN_DATE) - 1
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
            article_idx: Final[int] = self.excelProcessor.header.get(COLUMN_CC_ARTICLE) - 1

            last_row = self.excelProcessor.get_last_row()

            data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value
            people_history = defaultdict(list)

            if not data: return stats

            for row in data:
                if not row: continue

                # 1. Визначаємо БАЗОВИЙ РІК (кошик), куди все полетить
                des_date = row[des_date_idx]
                des_date_year = get_year_safe(des_date) or "Невідомо"

                cc_article = get_strint_fromfloat(str(row[article_idx]))
                #if cc_article in REPORT_SUBUNIT_EXCLUDE_ARTICLES:
                #    continue

                ret_mu_date = row[ret_mu_idx]
                ret_mu_date_year = get_year_safe(ret_mu_date)
                ret_res_date = row[ret_res_idx]
                ret_res_date_year = get_year_safe(ret_res_date)

                name = str(row[name_idx]).strip()

                id_number = get_strint_fromfloat(row[id_idx], "")
                where = str(row[where_idx] or "Не вказано").strip()
                service_type = str(row[service_type_idx] or "Не вказано").strip()
                des_type = str(row[des_type_idx] or "Не вказано").strip()
                rank = str(row[rank_idx] or "").lower().strip()

                is_officer = 'офіцер' in rank
                is_sergeant = 'сержант' in rank
                rank_key = 'офіцер' if is_officer else 'рядовий_сержант'
                suspended = str(row[suspended_idx]).strip()
                review_status = str(row[exp_review_idx]).strip()

                name_key = f"{id_number}_{name}"
                rank_separated_key = 'офіцер' if is_officer else 'сержант' if is_sergeant else 'рядовий'

                # Зберігаємо історію для унікального підрахунку
                people_history[name_key].append({
                    'des_date': des_date,
                    'ret_mu_date': ret_mu_date,
                    'ret_res_date': ret_res_date,
                    'rank': rank_separated_key,
                    'service_type': service_type
                })

                # === УСЯ СТАТИСТИКА ЗАПИСУЄТЬСЯ В des_date_year ===

                # 1. СЗЧ Терміни
                try:
                    if ret_mu_date and des_date and isinstance(des_date, (datetime, date)) and isinstance(ret_mu_date, (
                    datetime, date)):
                        days = (ret_mu_date - des_date).days
                    else:
                        days = 4
                except Exception:
                    days = 0

                period_key = 'under_3' if days <= 3 else 'over_3'
                stats[des_date_year][rank_key][period_key] += 1

                # 2. ПОВЕРНЕННЯ
                ret_mu_str = str(ret_mu_date).strip()
                if ret_mu_str and ret_mu_str != 'None':
                    stats[des_date_year][rank_key]['ret_mu'] += 1

                ret_res_str = str(ret_res_date).strip()
                if ret_res_str and ret_res_str != 'None':
                    stats[des_date_year][rank_key]['ret_res'] += 1

                # 3. ІНШІ СТАТУСИ. Відмови ми не рахуємо, памʼятай! 402 статя - лісом!
                for review_key, value in REVIEW_STATUS_MAP.items():
                    if review_status in value:
                        stats[des_date_year]['all'][review_key] += 1

                if where in ['РВБЗ']:
                    stats[des_date_year]['all']['pl_rvbz'] += 1
                elif where in ['ППД']:
                    stats[des_date_year]['all']['pl_ppd'] += 1
                else:
                    stats[des_date_year]['all']['pl_other'] += 1

                if des_type == DESERTION_TYPE_WEAPON_KEYWORD:
                    stats[des_date_year]['all']['weapon'] += 1

                # 4. КПП ТА ДБР
                kpp_val = str(row[kpp_num_idx] or "").strip()
                kpp_date = row[kpp_date_idx]
                kpp_date_year = get_year_safe(kpp_date)

                if kpp_val is not None and kpp_date_year == des_date_year:
                    stats[des_date_year]['all']['rev_dbr_notif'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_dbr_notif'] += 1

                dbr_val = str(row[dbr_num_idx] or "").strip()
                dbr_date = row[dbr_date_idx]
                dbr_date_year = get_year_safe(dbr_date)

                if dbr_val is not None and dbr_date_year == des_date_year:
                    stats[des_date_year]['all']['rev_dbr_mater'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_dbr_mater'] += 1

                if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_ERDR]:
                    stats[des_date_year]['all']['rev_dbr_nonerdr'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_dbr_nonerdr'] += 1
                if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_ERDR]:
                    stats[des_date_year]['all']['rev_dbr_erdr'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_dbr_erdr'] += 1

                if suspended == SUSPENDED_KEYWORD:
                    stats[des_date_year]['all']['rev_suspend'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_suspend'] += 1

                if review_status in REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_EVIL]:
                    stats[des_date_year]['all']['rev_nonevil'] += 1
                    if is_officer: stats[des_date_year]['офіцер']['rev_nonevil'] += 1

            # =======================================================
            # 5. ПІДРАХУНОК УНІКАЛЬНИХ ВИПАДКІВ
            # (також жорстко прив'язаний до року останнього СЗЧ)
            # =======================================================
            for name_key, cases in people_history.items():
                valid_cases = [c for c in cases if c['des_date'] and isinstance(c['des_date'], (datetime, date))]

                # Якщо дат СЗЧ взагалі немає - рахуємо як один випадок у "Невідомо"
                if not valid_cases:
                    last_case = cases[-1]
                    rank = last_case['rank']
                    service_type = last_case['service_type']
                    has_ret_mu = bool(str(last_case['ret_mu_date'] or "").strip() and str(
                        last_case['ret_mu_date'] or "").strip() != 'None')
                    has_ret_res = bool(str(last_case['ret_res_date'] or "").strip() and str(
                        last_case['ret_res_date'] or "").strip() != 'None')

                    if len(cases) > 1:
                        stats["Невідомо"][rank]['dupl'] += 1
                    else:
                        service_map = {'призивом': 'st_call', 'контрактом': 'st_contr'}
                        stats["Невідомо"]['all'][service_map.get(service_type, 'st_term')] += 1
                        if not (has_ret_mu or has_ret_res):
                            stats["Невідомо"][rank]['un_des'] += 1
                        else:
                            stats["Невідомо"][rank]['un_ret'] += 1
                    continue

                # Сортуємо всі випадки людини хронологічно
                valid_cases.sort(key=lambda x: x['des_date'])

                # Групуємо історію людини по роках
                cases_by_year = {}
                for i, case in enumerate(valid_cases):
                    des_year = get_year_safe(case['des_date'])
                    if des_year not in cases_by_year:
                        cases_by_year[des_year] = []
                    # Зберігаємо ПОРЯДКОВИЙ НОМЕР СЗЧ у житті людини (i + 1) та саму справу
                    cases_by_year[des_year].append((i + 1, case))

                # Тепер оцінюємо статус людини у КОЖНОМУ році, коли вона скоювала СЗЧ
                for des_year, year_cases in cases_by_year.items():

                    # Беремо ОСТАННЮ справу людини в межах цього конкретного року
                    historical_count, last_case_of_year = year_cases[-1]

                    rank = last_case_of_year['rank']
                    service_type = last_case_of_year['service_type']

                    has_ret_mu = bool(str(last_case_of_year['ret_mu_date'] or "").strip() and str(
                        last_case_of_year['ret_mu_date'] or "").strip() != 'None')
                    has_ret_res = bool(str(last_case_of_year['ret_res_date'] or "").strip() and str(
                        last_case_of_year['ret_res_date'] or "").strip() != 'None')
                    has_any_return = has_ret_mu or has_ret_res

                    # Якщо на момент цього року це вже НЕ ПЕРШЕ СЗЧ в її житті
                    if historical_count > 1:
                        stats[des_year][rank]['dupl'] += 1
                    else:
                        # Якщо це справді перше СЗЧ у житті (рахується як унікальне)
                        service_map = {'призивом': 'st_call', 'контрактом': 'st_contr'}
                        service_key = service_map.get(service_type, 'st_term')
                        stats[des_year]['all'][service_key] += 1

                        #if not has_any_return:
                        stats[des_year][rank]['un_des'] += 1
                        if has_any_return:
                            stats[des_year][rank]['un_ret'] += 1

            return stats
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {}

    def get_daily_report(self, target_date: date = None) -> List[Dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now().date()

        id_idx = self.excelProcessor.header.get(COLUMN_INCREMENTAL, 1) - 1
        name_idx = self.excelProcessor.header.get(COLUMN_NAME, 1) - 1
        ins_date_idx = self.excelProcessor.header.get(COLUMN_INSERT_DATE, 1) - 1
        des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE, 1) - 1
        ret_date_idx = self.excelProcessor.header.get(COLUMN_RETURN_DATE, 1) - 1
        title_idx = self.excelProcessor.header.get(COLUMN_TITLE_2, 1) - 1
        subunit_idx = self.excelProcessor.header.get(COLUMN_SUBUNIT, 1) - 1
        call_idx = self.excelProcessor.header.get(COLUMN_ENLISTMENT_DATE, 1) - 1
        days_idx = self.excelProcessor.header.get(COLUMN_SERVICE_DAYS, 1) - 1
        des_place_idx = self.excelProcessor.header.get(COLUMN_DESERTION_PLACE, 1) - 1
        des_region_idx = self.excelProcessor.header.get(COLUMN_DESERTION_REGION, 1) - 1
        exp_idx = self.excelProcessor.header.get(COLUMN_EXPERIENCE, 1) - 1
        des_type_idx = self.excelProcessor.header.get(COLUMN_DESERTION_TYPE, 1) - 1

        results = []
        target_sheets = ['А0224', 'А7018']
        for sheet_name in target_sheets:
            try:
                sheet = self.excelProcessor.sheet.book.sheets[sheet_name]
                last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
                data = sheet.range(f"A2:BB{last_row}").value
            except Exception as e:
                print(f"Помилка читання аркуша {sheet_name}: {e}")
                continue
            if not data:
                return results

            for row in data:
                if not row:
                    continue

                raw_ins = row[ins_date_idx] if len(row) > ins_date_idx else None
                raw_des = row[des_date_idx] if len(row) > des_date_idx else None
                raw_ret = row[ret_date_idx] if len(row) > ret_date_idx else None
                raw_call = row[call_idx] if len(row) > call_idx else None

                raw_des_type = row[des_type_idx] if len(row) > des_type_idx else None

                parsed_ins = self._parse_date(raw_ins) if raw_ins else None
                parsed_des = self._parse_date(raw_des) if raw_des else None
                parsed_ret = self._parse_date(raw_ret) if raw_ret else None
                parsed_call = self._parse_date(raw_call) if raw_call else None

                ins_date = parsed_ins.date() if parsed_ins else None
                des_date = parsed_des.date() if parsed_des else None
                ret_date = parsed_ret.date() if parsed_ret else None
                call_date = parsed_call.date() if parsed_call else None
                term_days = row[days_idx]
                raw_place = row[des_place_idx] if len(row) > des_place_idx else None
                raw_region = row[des_region_idx] if len(row) > des_region_idx else None

                des_place_clean = str(raw_place).strip() if raw_place else 'Не вказано'
                des_region_clean = str(raw_region).strip() if raw_region else ''
                des_type_clean = str(raw_des_type).strip().lower() if raw_des_type else ''

                # ==========================================
                # 💡 ДОДАНО: Перевірка на "Подвійну подію"
                # Якщо це несвоєчасне повернення або без поважних причин, людина має потрапити
                # в СЗЧ навіть якщо в неї вже заповнена дата повернення.
                # ==========================================
                is_dual_event = 'сзч' not in des_type_clean

                # Якщо дата знайдена і вона збігається з цільовою
                if ins_date == target_date and (ret_date is None or is_dual_event):
                    results.append({
                        'sheet_name': sheet_name,
                        'ins_date': ins_date,
                        'des_date': des_date,
                        'name': row[name_idx] if len(row) > name_idx else 'Невідомо',
                        'title': row[title_idx] if len(row) > title_idx else 'Не вказано',
                        'subunit': row[subunit_idx] if len(row) > subunit_idx else 'Не вказано',
                        'call_date': call_date,
                        'term_days': get_strint_fromfloat(term_days),
                        'desertion_place': des_place_clean,
                        'desertion_region': des_region_clean,
                        'experience': row[exp_idx] if (row[exp_idx]) else 'Невідомо',
                        'desertion_type': des_type_clean
                    })

        return results

    def get_daily_returns_report(self, target_date: date, exclude_names: List[str] = None, pre_fetched_archive: list = None) -> List[Dict[str, Any]]:
        if exclude_names is None:
            exclude_names = []

        # 💡 ОПТИМІЗАЦІЯ: Якщо файли вже передані з UI, не читаємо їх знову!
        if pre_fetched_archive is not None:
            archive_files = pre_fetched_archive
        else:
            dservice = DocumentProcessingService(self.log_manager)
            archive_files = dservice.get_daily_archive_files(target_date, known_names=[])

        returns_from_files = []
        for file_info in archive_files:
            filename = file_info.get('filename', '').lower()

            is_return_doc = bool(re.search(PATTERN_RETURN_SIGN_IN_FILE, filename)) if PATTERN_RETURN_SIGN_IN_FILE else ('повернення' in filename)
            is_dual_event_doc = 'без поважних' in filename or 'несвоєчасн' in filename

            if (is_return_doc or is_dual_event_doc) and 'неповернення' not in filename and 'не повернення' not in filename:
                names_str = file_info.get('name', '')
                if names_str and names_str not in ('Не вдалося розпізнати', 'Не текстовий документ'):
                    names_list = [n.strip() for n in names_str.split(',')]

                    for name in names_list:
                        last_name = name.split()[0].lower()
                        if not any(last_name in excl_name.lower() for excl_name in exclude_names):
                            returns_from_files.append({
                                'name': name,
                                'ret_date': target_date.strftime('%d.%m.%Y')
                            })

        if not returns_from_files:
            return []

        self.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME, silent=True)

        name_idx = self.excelProcessor.header.get(COLUMN_NAME, 1) - 1
        id_idx = self.excelProcessor.header.get(COLUMN_ID_NUMBER, 1) - 1
        title_idx = self.excelProcessor.header.get(COLUMN_TITLE_2, 1) - 1
        subunit_idx = self.excelProcessor.header.get(COLUMN_SUBUNIT, 1) - 1
        des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE, 1) - 1

        last_row = self.excelProcessor.get_last_row()
        data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value

        excel_dict_by_lastname = {}
        if data:
            for row in data:
                if not row or len(row) <= name_idx: continue

                full_name = str(row[name_idx]).strip()
                if full_name and full_name != 'None':
                    last_name = full_name.split()[0].lower()

                    if last_name not in excel_dict_by_lastname:
                        excel_dict_by_lastname[last_name] = []
                    excel_dict_by_lastname[last_name].append(row)

        final_returns = []
        for ret in returns_from_files:
            person_name = ret['name']
            last_name = person_name.split()[0].lower()

            matching_rows = excel_dict_by_lastname.get(last_name, [])
            best_match_row = None
            if len(matching_rows) == 1:
                best_match_row = matching_rows[0]
            elif len(matching_rows) > 1:
                for row in matching_rows:
                    if str(row[name_idx]).strip().lower() == person_name.lower():
                        best_match_row = row
                        break
                if not best_match_row:
                    best_match_row = matching_rows[0]  # Fallback

            if best_match_row:
                person_id = str(best_match_row[id_idx]).replace('.0', '').strip() if len(best_match_row) > id_idx else 'Не вказано'
                title = best_match_row[title_idx] if len(best_match_row) > title_idx else 'Не вказано'
                subunit = best_match_row[subunit_idx] if len(best_match_row) > subunit_idx else 'Не вказано'

                raw_des_date = best_match_row[des_date_idx] if len(best_match_row) > des_date_idx else None
            else:
                person_id = 'Не знайдено в Excel'
                title = 'Не вказано'
                subunit = 'Не вказано'
                raw_des_date = None

            des_date_str = "Невідомо"
            if isinstance(raw_des_date, datetime):
                des_date_str = raw_des_date.strftime('%d.%m.%Y')
            elif isinstance(raw_des_date, str):
                des_date_str = raw_des_date.strip()

            final_returns.append({
                'name': person_name,
                'id_number': person_id,
                'title': title,
                'subunit': subunit,
                'des_date': des_date_str,
                'ret_date': ret.get('ret_date', 'Не вказано')
            })

        return final_returns

    # from 2022-up to now, the total brief summary, - desertion number, returns number
    def get_brief_summary(self) -> list[dict]:
        """Рахує загальну макро-статистику для таблиці командувача (ВЧ А0224)"""
        des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE, 1) - 1
        return_date_idx = self.excelProcessor.header.get(COLUMN_RETURN_DATE, 1) - 1
        return_reserve_date_idx = self.excelProcessor.header.get(COLUMN_RETURN_TO_RESERVE_DATE, 1) - 1

        total_awol = 0
        returned = 0
        res_returned = 0

        try:
            sheet = self.excelProcessor.sheet.book.sheets['А0224']
            last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
            data = sheet.range(f"A2:BB{last_row}").value

            for row in data:
                if not row: continue

                # Перевіряємо, чи є значення у відповідних клітинках
                has_des = len(row) > des_date_idx and row[des_date_idx]
                has_ret = len(row) > return_date_idx and row[return_date_idx]
                has_res_ret = len(row) > return_reserve_date_idx and row[return_reserve_date_idx]

                if has_des:
                    total_awol += 1
                if has_ret:
                    returned += 1
                if has_res_ret:
                    res_returned += 1

        except Exception as e:
            print(f"Помилка формування таблиці командувача: {e}")

        # Ті, хто ще не повернувся
        in_search = total_awol - (returned + res_returned)

        # Повертаємо масив з одним словником (щоб ui.table легко це з'їв)
        return [{
            'total_awol': total_awol,
            'in_search': in_search,
            'returned': returned,
            'res_returned': res_returned,
            'in_disposal': 0
        }]

    def get_dupp_names_report(self) -> Dict[str, List[Dict[str, Any]]]:
        # Отримуємо індекси колонок (переконайтеся, що константи імпортовані)
        name_idx = self.excelProcessor.header.get(COLUMN_NAME) - 1
        id_idx = self.excelProcessor.header.get(COLUMN_ID_NUMBER) - 1
        birth_idx = self.excelProcessor.header.get(COLUMN_BIRTHDAY) - 1
        des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE) - 1

        last_row = self.excelProcessor.get_last_row()
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

    def get_waiting_for_erdr_report(self, search_filter: PersonSearchFilter):
        results = []

        last_row = self.excelProcessor.get_last_row()

        if last_row < 2:
            return results

        data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value
        if not data:
            return results

        header = self.excelProcessor.header

        pib_idx = header.get(COLUMN_NAME, 1) - 1
        rnokpp_idx = header.get(COLUMN_ID_NUMBER, 1) - 1
        dob_idx = header.get(COLUMN_BIRTHDAY, 1) - 1
        des_date_idx = header.get(COLUMN_DESERTION_DATE, 1) - 1
        rank_idx = header.get(COLUMN_TITLE, 1) - 1
        unit_idx = header.get(COLUMN_SUBUNIT, 1) - 1
        dbr_date_idx = header.get(COLUMN_DBR_DATE, 1) - 1
        dbr_num_idx = header.get(COLUMN_DBR_NUMBER, 1) - 1
        erdr_date_idx = header.get(COLUMN_ERDR_DATE, 1) - 1
        erdr_num_idx = header.get(COLUMN_ERDR_NOTATION, 1) - 1

        q_des_year = search_filter.des_year
        q_des_year = search_filter.des_year
        q_des_date_from = date.fromisoformat(search_filter.des_date_from) if search_filter.des_date_from else None
        q_des_date_to = date.fromisoformat(search_filter.des_date_to) if search_filter.des_date_to else None

        for row in data:
            if not row or not row[pib_idx]:
                continue

            des_date_val = row[des_date_idx]
            des_date_year = None
            des_date_str = ""

            dbr_date_val = row[dbr_date_idx]
            dbr_date_year = None
            dbr_date_str = ""

            erdr_date_val = row[erdr_date_idx]
            erdr_date_year = None
            erdr_date_str = ""

            if isinstance(des_date_val, (datetime, date)):
                des_date_year = str(des_date_val.year)
                des_date_str = des_date_val.strftime(EXCEL_DATE_FORMAT)
            elif des_date_val:
                des_date_str = str(des_date_val).strip()
                if len(des_date_str) >= 4:
                    des_date_year = des_date_str[-4:]

            if isinstance(dbr_date_val, (datetime, date)):
                dbr_date_year = str(dbr_date_val.year)
                dbr_date_str = dbr_date_val.strftime(EXCEL_DATE_FORMAT)
            elif dbr_date_val:
                dbr_date_str = str(dbr_date_val).strip()
                if len(dbr_date_str) >= 4:
                    dbr_date_year = dbr_date_str[-4:]

            if erdr_date_val is not None and isinstance(erdr_date_val, (datetime, date)):
                erdr_date_year = str(erdr_date_val.year)
                erdr_date_str = erdr_date_val.strftime(EXCEL_DATE_FORMAT)
            elif erdr_date_val:
                erdr_date_str = str(erdr_date_val).strip()
                if len(erdr_date_str) >= 4:
                    erdr_date_year = erdr_date_str[-4:]

            # --- ФІЛЬТРАЦІЯ ---
            match_des_year = True
            match_dbr_year = True
            match_erdr_date = erdr_date_val is None

            if q_des_year:
                if isinstance(q_des_year, list):
                    match_des_year = (des_date_year in q_des_year)
                    match_dbr_year = (dbr_date_year in q_des_year)
                else:
                    match_des_year = (des_date_year == str(q_des_year))
                    match_dbr_year = (dbr_date_year == str(q_des_year))

            match_des_year_from = True
            match_des_year_to = True

            if q_des_date_from or q_des_date_to:
                if des_date_val:
                    if isinstance(des_date_val, datetime):
                        row_des_date = des_date_val.date()
                    elif isinstance(des_date_val, date):
                        row_des_date = des_date_val
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

            if not match_period or not match_dbr_year or not match_erdr_date:
                continue

            dob_val = row[dob_idx]
            dob_str = dob_val.strftime(EXCEL_DATE_FORMAT) if isinstance(dob_val, (datetime, date)) else str(dob_val or '')

            # Безпечне отримання РНОКПП (обходимо проблему .0 у Excel)
            rnokpp_raw = row[rnokpp_idx]
            if isinstance(rnokpp_raw, float):
                rnokpp_str = str(int(rnokpp_raw))
            else:
                rnokpp_str = str(rnokpp_raw or '').strip()

            # Додаємо запис у результати
            results.append({
                'des_date': des_date_str,
                'pib': str(row[pib_idx] or '').strip(),
                'rnokpp': rnokpp_str,
                'dob': dob_str.strip(),
                'rank': str(row[rank_idx] or '').strip(),
                'unit': str(row[unit_idx] or '').strip(),
                'dbr_date': dbr_date_str.strip(),
                'dbr_number': str(row[dbr_num_idx] or '').strip() if dbr_num_idx >= 0 else '',
                'erdr_date': erdr_date_str.strip(),
                'erdr_number': str(row[erdr_num_idx] or '').strip() if erdr_num_idx >= 0 else ''

            })

        return results
