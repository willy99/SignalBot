from datetime import datetime
from typing import Any, Optional

import config
from dics.deserter_xls_dic import *
from collections import defaultdict

class ExcelReporter:
    def __init__(self, excelProcessor):
        # Завантажуємо файл у режимі read_only для швидкості
        self.excelProcessor = excelProcessor

    def get_summary_report(self) -> str:
        """Генерує текстовий звіт по СЗЧ."""
        total_count = 0
        today_count = 0

        # Отримуємо сьогоднішню дату у форматі, як вона в Екселі (наприклад, '2/6/26')
        # Або порівнюємо як об'єкти datetime
        today = datetime.now().date()

        # Індекси стовпців (зменшуємо на 1, якщо використовуємо iter_rows)
        pib_idx = self.excelProcessor.column_map.get(COLUMN_NAME.lower())
        date_added_idx = self.excelProcessor.column_map.get(COLUMN_INSERT_DATE.lower())
        id_idx = self.excelProcessor.column_map.get(COLUMN_INCREMEMTAL.lower())

        if not id_idx or not pib_idx or not date_added_idx:
            return "❌ Помилка: Не знайдено необхідні стовпці для звіту."

        # Пропускаємо заголовок (min_row=2)
        for row in self.excelProcessor.sheet.iter_rows(min_row=2, values_only=True):
            pib_value = row[pib_idx - 1]
            date_val = row[date_added_idx - 1]
            id_value = row[id_idx - 1]

            # 1. Рахуємо загальну кількість (якщо є ПІБ)
            if pib_value and str(pib_value).strip():
                total_count += 1

                # 2. Рахуємо кількість за сьогодні
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

        print(full_report)

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