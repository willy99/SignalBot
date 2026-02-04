import datetime
from datetime import datetime, timedelta
import config

def clean_text(text):
    # .split() без аргументів розбиває рядок по будь-якій кількості
    # пробілів, табуляцій та переносів, а " ".join зшиває їх назад одним пробілом.
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


def format_to_excel_date(date_val):
    """
    Приймає datetime або str (ДД.ММ.РРРР або ДД.ММ.РР)
    Повертає рядок у форматі m/d/yy (напр. 8/29/84)
    """
    if not date_val or date_val == "N/A":
        return ""

    if isinstance(date_val, str):
        try:
            date_val = date_val.strip().strip('.')
            parts = date_val.split('.')
            if len(parts) != 3:
                return date_val

            # Визначаємо формат року: %Y для 2025, %y для 25
            year_fmt = "%Y" if len(parts[2]) == 4 else "%y"
            date_val = datetime.strptime(date_val, f"%d.%m.{year_fmt}")
        except ValueError:
            return date_val

    # Твоя оригінальна логіка форматування
    formatted = date_val.strftime("%m/%d/%y").replace("/0", "/")
    if formatted.startswith("0"):
        formatted = formatted[1:]

    return formatted


import os


def get_file_name(file_path):
    """
    Повертає ім'я файлу без шляху та без розширення.
    """
    # 1. Отримуємо '06.01.2026 СЗЧ з РВБЗ 1 АЕМР АЕМБ ГАЛАЙКО В.В..doc'
    base_name = os.path.basename(file_path)

    # 2. Відрізаємо розширення (.doc)
    name_without_ext = os.path.splitext(base_name)[0]

    return name_without_ext
