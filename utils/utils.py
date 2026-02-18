import datetime
from datetime import timedelta
from datetime import datetime, date
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



def to_html_date(val):
    """Перетворює будь-який вхідний формат дати в YYYY-MM-DD для браузера"""
    if not val:
        return ""

    # 1. Якщо прийшов об'єкт datetime від xlwings
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')

    # 2. Якщо прийшов рядок (наприклад, з вашого config.EXCEL_DATE_FORMAT)
    try:
        dt = datetime.strptime(str(val).strip(), config.EXCEL_DATE_FORMAT)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 3. Якщо формат невідомий, пробуємо стандартний ISO
        try:
            return datetime.fromisoformat(str(val)).strftime('%Y-%m-%d')
        except:
            return ""

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

def get_typed_value(value):
        if isinstance(value, str):
            try:
                valid_date = datetime.strptime(value, config.EXCEL_DATE_FORMAT)
                return valid_date
            except ValueError:
                return value
        else:
            return value


def check_birthday_id_number(birthday: datetime, idn: str)-> bool:
    if idn is None or birthday is None or idn == '':
        return True
    # Обчислюємо дату з РНОКПП
    base_date = datetime(1899, 12, 31)
    days_count = int(idn[:5])
    birthday_calculated_dt = base_date + timedelta(days=days_count)
    birthday_calculated = format_ukr_date(birthday_calculated_dt).strip()
    birthday_table = format_ukr_date(birthday).strip() if birthday else None
    if birthday_table != birthday_calculated:
        print('------ ⚠️ В таблиці:' + str(birthday_table) + ' А шо винно бути:' + str(birthday_calculated))
        return False
    return True
