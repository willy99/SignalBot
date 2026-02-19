# gui/views/components.py
from nicegui import ui

def menu():
    with ui.header().classes('bg-slate-800 items-center justify-between'):
        ui.label('А0224, RUNNERS AND SOLDIERS').classes('font-bold text-xl text-white')
        with ui.row():
            ui.button('Пошук', on_click=lambda: ui.navigate.to('/')).props('flat text-white')
            ui.button('ЄРДР', on_click=lambda: ui.navigate.to('/reports')).props('flat text-white')