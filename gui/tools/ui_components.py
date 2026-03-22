import re
from nicegui import ui
from config import UI_DATE_FORMAT
from dics.deserter_xls_dic import VALID_PATTERN_DATE
from typing import Any, Callable
from datetime import datetime
import math

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

async def confirm_delete_dialog(text: str):
    dialog = ui.dialog()
    with dialog, ui.card().classes('p-6 min-w-[300px]'):
        ui.label('Видалення').classes('text-xl font-bold text-red-600 mb-2')
        ui.label(text).classes('text-gray-600 mb-6')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
            ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

    return await dialog


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


class ServerPagination:
    def __init__(self, records_per_page: int, on_change: Callable[[], None]):
        """
        Компонент серверної пагінації.
        :param records_per_page: Кількість записів на одну сторінку
        :param on_change: Колбек-функція, яка викликається при зміні сторінки (натисканні кнопок)
        """
        self.records_per_page = records_per_page
        self.on_change = on_change

        self.current_page = 1
        self.total_records = 0
        self.total_pages = 1
        self._is_updating = False

        self._build_ui()

    def _build_ui(self):
        with ui.row().classes('w-full max-w-6xl justify-between items-center mt-4 px-2'):
            self.total_label = ui.label('Всього записів: 0').classes('text-gray-500 font-bold')

            self.pagination = ui.pagination(min=1, max=1, direction_links=True) \
                .props('max-pages=7 boundary-links active-color="primary" active-text-color="white"') \
                .on_value_change(self._on_ui_change)

    def _on_ui_change(self, e):
        # Якщо подія викликана нашим власним кодом (наприклад, функцією reset), ігноруємо
        if self._is_updating:
            return

        new_page = e.value
        # Перевіряємо, чи дійсно змінилася сторінка
        if new_page and new_page != self.current_page:
            self.current_page = new_page
            # Викликаємо колбек для завантаження нових даних
            self.on_change()

    def update_total(self, total_records: int):
        self._is_updating = True
        self.total_records = total_records
        self.total_pages = max(1, math.ceil(self.total_records / self.records_per_page))

        self.total_label.set_text(f"Всього записів: {self.total_records}")

        self.pagination._props['max'] = self.total_pages
        self.pagination.value = self.current_page
        self.pagination.update()

        self._is_updating = False

    def reset(self):
        self._is_updating = True
        self.current_page = 1
        self.pagination.value = 1
        self.pagination.update()
        self._is_updating = False

    @property
    def offset(self) -> int:
        """Повертає поточний offset для SQL-запиту"""
        return (self.current_page - 1) * self.records_per_page

    @property
    def limit(self) -> int:
        """Повертає поточний limit для SQL-запиту"""
        return self.records_per_page