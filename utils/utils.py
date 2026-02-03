import datetime
from datetime import datetime, timedelta
import config

def clean_text(text):
    # .split() без аргументів розбиває рядок по будь-якій кількості
    # пробілів, табуляцій та переносів, а " ".join зшиває їх назад одним пробілом.
    return " ".join(text.split())


def get_effective_date():
    """Визначає 'робочу' дату з урахуванням години переходу."""
    now = datetime.now()

    # Якщо зараз вечір (наприклад, після 16:00), файли йдуть у папку наступного дня
    if now.hour >= config.DAY_ROLLOVER_HOUR:
        return now + timedelta(days=1)

    # ОБОВ'ЯЗКОВО повертаємо поточну дату, якщо година менша за ліміт
    return now