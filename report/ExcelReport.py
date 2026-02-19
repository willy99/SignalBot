from datetime import datetime
from typing import Any, Optional
import traceback
import config
from dics.deserter_xls_dic import *
from collections import defaultdict
from storage.LoggerManager import LoggerManager
from config import DESERTER_TAB_NAME

class ExcelReporter:
    def __init__(self, excelProcessor, log_manager: LoggerManager):
        # Завантажуємо файл у режимі read_only для швидкості
        self.excelProcessor = excelProcessor
        self.logger = log_manager.get_logger()


    def get_subunit_desertion_stats(self, year_filter):
        """Збирає повну статистику по підрозділах, званнях та термінах СЗЧ."""
        self.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME)
        try:
            # Ініціалізуємо вкладений словник (автоматично створює гілки)
            stats = defaultdict(lambda: defaultdict(lambda: {
                'офіцер': {'under_3': 0, 'over_3': 0, 'ret_mu': 0, 'ret_res': 0},
                'рядовий_сержант': {'under_3': 0, 'over_3': 0, 'ret_mu': 0, 'ret_res': 0}
            }))

            # Отримуємо індекси стовпців з вашого column_map
            unit_idx = self.excelProcessor.header.get(COLUMN_SUBUNIT) - 1
            sub_unit_idx = self.excelProcessor.header.get(COLUMN_SUBUNIT2) - 1
            rank_idx = self.excelProcessor.header.get(COLUMN_TITLE_2) - 1
            days_idx = self.excelProcessor.header.get(COLUMN_DESERTION_TERM) - 1
            des_date_idx = self.excelProcessor.header.get(COLUMN_DESERTION_DATE) - 1
            # ins_date_idx = self.excelProcessor.header.get(COLUMN_INSERT_DATE) - 1
            ret_mu_idx = self.excelProcessor.header.get(COLUMN_RETURN_DATE) -1
            ret_res_idx = self.excelProcessor.header.get(COLUMN_RETURN_TO_RESERVE_DATE) - 1

            # Читаємо весь заповнений діапазон

            last_row = self.excelProcessor.sheet.range((65536, 1)).end('up').row
            data = self.excelProcessor.sheet.range(f"A2:BB{last_row}").value

            if data is None:
                return stats

            for i, row in enumerate(data):
                # filter date
                des_date = row[des_date_idx] # mandatory field
                des_date_year = str(des_date.year) if des_date is not None else None

                ret_mu_date = row[ret_mu_idx]
                ret_mu_date_year = str(ret_mu_date.year) if ret_mu_date is not None else None
                ret_res_date = row[ret_res_idx]
                ret_res_date_year = str(ret_res_date.year) if ret_res_date is not None else None

                unit = str(row[unit_idx] or "Не вказано").strip()
                sub_unit = str(row[sub_unit_idx] or "Не вказано").strip()
                rank = str(row[rank_idx] or "").lower().strip()
                officer_keywords = ['офіцер']
                is_officer = any(word in rank for word in officer_keywords)
                rank_key = 'офіцер' if is_officer else 'рядовий_сержант'

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ СЗЧ
                match_year = (not year_filter or des_date_year in year_filter)
                if match_year: #desertion case
                    try:
                        days = 4 if str(row[days_idx]) == 'більше 3 діб' else 0
                    except ValueError:
                        days = 0
                    period_key = 'under_3' if days <= 3 else 'over_3'
                    stats[unit][sub_unit][rank_key][period_key] += 1

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ ПОВЕРНЕННЯ В ВЧ
                match_year = (not year_filter or ret_mu_date_year in year_filter)
                if match_year: # return to military unit
                    stats[unit][sub_unit][rank_key]['ret_mu'] += 1

                # ЛОГІКА ФІЛЬТРАЦІЇ ДЛЯ ПОВЕРНЕННЯ В РЕЗЕРВ
                match_year = (not year_filter or ret_res_date_year in year_filter)
                if match_year: # return to military unit
                    stats[unit][sub_unit][rank_key]['ret_res'] += 1

            # for unit, sub_units in stats.items():
            #     self.logger.debug(f"### ⚔️ {unit}")
            #     for sub, roles in sub_units.items():
            #         over = roles['рядовий_сержант']['over_3'] + roles['офіцер']['over_3']
            #         under = roles['рядовий_сержант']['under_3'] + roles['офіцер']['under_3']
            #         if over > 0 or under > 0:
            #             self.logger.debug(f"* **{sub}:** 🟢 до 3: {under} | 🔴 понад 3: {over}")
            return stats
        except Exception as e:
            traceback.print_exc()
            return []






    def get_detailed_stats(self):
        """Збирає повну статистику по підрозділах, званнях та термінах СЗЧ."""

        # Ініціалізуємо вкладений словник (автоматично створює гілки)
        stats = defaultdict(lambda: defaultdict(lambda: {
            'офіцер': {'under_3': 0, 'over_3': 0},
            'рядовий_сержант': {'under_3': 0, 'over_3': 0}
        }))

        # Отримуємо індекси стовпців з вашого column_map
        unit_idx = self.excelProcessor.column_map.get(COLUMN_SUBUNIT.lower())  # Підрозділ
        sub_unit_idx = self.excelProcessor.column_map.get(COLUMN_SUBUNIT2.lower())  # Саб-підрозділ
        rank_idx = self.excelProcessor.column_map.get(COLUMN_TITLE_2.lower())  # Звання
        days_idx = self.excelProcessor.column_map.get(COLUMN_DESERTION_TERM.lower())  # К-сть днів в СЗЧ
        des_date_idx = self.excelProcessor.column_map.get(COLUMN_DESERTION_DATE.lower())

        # Читаємо весь заповнений діапазон
        sheet = self.excelProcessor.sheet
        last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
        if last_row < 2: return {}

        # Завантажуємо дані в пам'ять (Data Matrix)
        data = sheet.range((2, 1), (last_row, sheet.used_range.columns.count)).value
        if last_row == 2: data = [data]

        for row in data:
            unit = str(row[unit_idx - 1] or "Не вказано").strip()
            sub_unit = str(row[sub_unit_idx - 1] or "Не вказано").strip()
            rank = str(row[rank_idx - 1] or "").lower().strip()
            des_date = row[des_date_idx - 1]
            if not self.accept_date(des_date, [2026]):
                continue

            # Логіка визначення терміну (припускаємо, що в колонці число днів)
            try:
                days = 4 if str(row[days_idx - 1]) == 'більше 3 діб' else 0
            except ValueError:
                days = 0

            period_key = 'under_3' if days <= 3 else 'over_3'

            # Групування по званнях
            # Додай сюди всі варіації офіцерських звань, які є в базі
            officer_keywords = ['офіцер']
            is_officer = any(word in rank for word in officer_keywords)
            rank_key = 'офіцер' if is_officer else 'рядовий_сержант'

            # Інкремент статистики
            stats[unit][sub_unit][rank_key][period_key] += 1

        for unit, sub_units in stats.items():
            self.logger.debug(f"### ⚔️ {unit}")
            for sub, roles in sub_units.items():
                over = roles['рядовий_сержант']['over_3'] + roles['офіцер']['over_3']
                under = roles['рядовий_сержант']['under_3'] + roles['офіцер']['under_3']
                if over > 0 or under > 0:
                    self.logger.debug(f"* **{sub}:** 🟢 до 3: {under} | 🔴 понад 3: {over}")
        return self.format_detailed_report(stats)

    def format_detailed_report(self, stats):
        # Заголовок таблиці
        header = f"{'ПІДРОЗДІЛ':<18} | {'Р/С <3':<6} | {'Р/С >3':<6} | {'ОФ <3':<5} | {'ОФ >3':<5}"
        separator = "-" * len(header)

        lines = [
            "📊 *ЗВІТ ПО ПІДРОЗДІЛАХ (2026)*",
            "```",  # Початок моноширинного блоку
            header,
            "━" * len(header)
        ]

        for unit, sub_units in stats.items():
            lines.append(f"{unit}")  # Назва батальйону/дивізіону

            for sub, roles in sub_units.items():
                # Отримуємо значення
                rs_u3 = roles['рядовий_сержант']['under_3']
                rs_o3 = roles['рядовий_сержант']['over_3']
                of_u3 = roles['офіцер']['under_3']
                of_o3 = roles['офіцер']['over_3']

                # Пропускаємо порожні підрозділи (якщо треба)
                if rs_u3 == 0 and rs_o3 == 0 and of_u3 == 0 and of_o3 == 0:
                    continue

                # Форматуємо рядок:
                # -- назва (15 симв), значення центровані в колонках
                row = f"-- {sub[:15]:<15} | {rs_u3:^6} | {rs_o3:^6} | {of_u3:^5} | {of_o3:^5}"
                lines.append(row)

            lines.append(separator)

        lines.append("```")  # Кінець моноширинного блоку
        return "\n".join(lines)

    def accept_date(self, raw_date, year_set):
        # Перевірка: чи це взагалі дата і чи вона за 2026 рік
        if not isinstance(raw_date, datetime):
            # Якщо Excel віддав рядок замість дати, спробуємо перетворити (опціонально)
            try:
                if isinstance(raw_date, str):
                    # Формат залежить від того, як введено в Excel (напр. 12.02.2026)
                    raw_date = datetime.strptime(raw_date, "%d.%m.%Y")
                else:
                    return False
                    #continue  # Пропускаємо, якщо порожньо або не дата
            except:
                return False

        # Фільтр по року
        if raw_date.year in year_set:
            return True

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

    def get_all_names_report(self) -> str:
        """Генерує повний список усіх ПІБ, які є в базі (алфавітний порядок)."""
        all_names = []

        # Отримуємо індекс стовпця ПІБ
        pib_idx = self.excelProcessor.column_map.get(COLUMN_NAME.lower())
        insertion_idx = self.excelProcessor.column_map.get(COLUMN_INSERT_DATE.lower())


        if not pib_idx or not insertion_idx:
            return "❌ Помилка: Стовпець ПІБ / Дата не знайдено."

        # Проходимо по всіх рядках
        for row in self.excelProcessor.sheet.iter_rows(min_row=2, values_only=True):
            pib_value = row[pib_idx - 1]
            date_value = row[insertion_idx - 1]

            if pib_value and str(pib_value).strip():
                all_names.append(str(date_value) + ':: ' + str(pib_value).strip())

        # Сортуємо список за алфавітом
        # all_names.sort()

        if not all_names:
            return "📭 База порожня. Немає записів для відображення."

        # Формуємо текст списку
        formatted_list = "\n".join([f"{i + 1}. {name}" for i, name in enumerate(all_names)])

        total_count = len(all_names)

        # Заголовок звіту
        header = (
            "📜 *ПОВНИЙ СПИСОК ПРІЗВИЩ У БАЗІ*\n"
            "━━━━━━━━━━━━━━━\n"
        )
        footer = (
            "\n━━━━━━━━━━━━━━━\n"
            f"📊 Всього у базі: *{total_count}* осіб.\n"
            f"🕒 Дата формування: {datetime.now().strftime('%d.%m.%Y')}"
        )

        # Якщо список занадто довгий для одного повідомлення (Telegram limit ~4096 chars)
        full_report = f"{header}{formatted_list}{footer}"

        self.logger.debug(full_report)

        if len(full_report) > 4000:
            return (f"{header}_Список занадто довгий для відображення в одному повідомленні._\n"
                    f"📊 Всього записів: *{total_count}*\n"
                    f"💡 Рекомендую використовувати пошук або звіт за місяць.")

        return full_report

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