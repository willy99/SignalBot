import datetime
from datetime import timedelta
import config
import os
from typing import Any
from dics.deserter_xls_dic import NA

def clean_text(text):
    if text is None: return None
    return " ".join(text.split())


def get_effective_date():
    """Визначає 'робочу' дату з урахуванням години переходу."""
    now = datetime.now()

    # Якщо зараз вечір (наприклад, після 16:00), файли йдуть у папку наступного дня
    if now.hour >= config.DAY_ROLLOVER_HOUR:
        return now + timedelta(days=1)

    # ОБОВ'ЯЗКОВО повертаємо поточну дату, якщо година менша за ліміт
    return now


from datetime import datetime


def format_to_excel_date(date_val: Any) -> str:
    """
    Приймає datetime або str.
    Повертає рядок у форматі, визначеному в EXCEL_DATE_FORMAT (напр. 08.02.2026).
    """
    if not date_val or date_val == NA:
        return ""

    # 1. Якщо це вже об'єкт datetime
    if isinstance(date_val, datetime):
        return date_val.strftime(config.EXCEL_DATE_FORMAT)

    # 2. Якщо це рядок
    if isinstance(date_val, str):
        try:
            clean_val = date_val.strip().strip('.')
            parts = clean_val.split('.')

            if len(parts) != 3:
                return date_val  # Повертаємо як є, якщо формат дивний

            # Визначаємо формат року: %Y для 2026, %y для 26
            year_part = parts[2]
            year_fmt = "%Y" if len(year_part) == 4 else "%y"

            # Парсимо в об'єкт datetime
            dt_obj = datetime.strptime(clean_val, f"%d.%m.{year_fmt}")

            # Повертаємо у вашому цільовому форматі з константи
            return dt_obj.strftime(config.EXCEL_DATE_FORMAT)

        except (ValueError, IndexError):
            return date_val

    return str(date_val)

def get_file_name(file_path):
    """
    Повертає ім'я файлу без шляху та без розширення.
    """
    # 1. Отримуємо '06.01.2026 СЗЧ з РВБЗ 1 АЕМР АЕМБ ГАЛАЙКО В.В..doc'
    base_name = os.path.basename(file_path)

    # 2. Відрізаємо розширення (.doc)
    name_without_ext = os.path.splitext(base_name)[0]

    return name_without_ext

def format_ukr_date(date_val):
    if not date_val or str(date_val).lower() in ["none", "nan", ""]:
        return ""

    # 1. Відсікаємо час, якщо він є
    date_str = str(date_val).split(' ')[0].strip()

    # 2. Пробуємо кожен формат із нашого списку
    for fmt in config.EXCEL_DATE_FORMATS_REPORT:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Як тільки знайшли збіг — повертаємо у вашому улюбленому форматі
            return dt.strftime(config.EXCEL_DATE_FORMAT)
        except ValueError:
            continue

    # 3. Якщо жоден формат не підійшов — повертаємо як було (щоб не втратити дані)
    return date_str