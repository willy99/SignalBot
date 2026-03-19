import re
from nicegui import ui
from config import UI_DATE_FORMAT
from dics.deserter_xls_dic import VALID_PATTERN_DATE
from typing import Any
from datetime import datetime

def date_input(label: str, bind_obj: Any, field: str, blur_handler=None, default_value=None):
    """
    Кастомний компонент вводу дати з календариком та валідацією.
    """
    inp = ui.input(label=label, value=default_value, placeholder='dd.mm.YYYY', validation={
        'Формат має бути dd.mm.YYYY': lambda v: bool(re.match(VALID_PATTERN_DATE, str(v))) if v else True
    }).bind_value(bind_obj, field).props('mask="##.##.####" hide-bottom-space')

    if blur_handler:
        inp.on('blur', blur_handler)

    with inp.add_slot('append'):
        ui.icon('edit_calendar').classes('cursor-pointer')
        with ui.menu():
            ui.date().bind_value(bind_obj, field).props(f'mask="{UI_DATE_FORMAT}"')

    return inp


def fix_date(e):
    val = e.sender.value
    if not val:
        return

    clean_val = val.rstrip('.')
    parts = clean_val.split('.')

    if len(parts) == 2:
        current_year = datetime.now().year
        e.sender.value = f"{clean_val}.{current_year}"


def mark_dirty(*args):
    """Позначає, що на сторінці є незбережені зміни."""
    ui.run_javascript('window.isDirty = true;')

def mark_clean(*args):
    """Скидає статус незбережених змін (наприклад, після успішного збереження)."""
    ui.run_javascript('window.isDirty = false;')