from nicegui import ui
from gui.components import menu

def notif_view_doc():
    # Робимо контейнер на всю висоту екрана (h-screen) і центруємо вміст
    with ui.column().classes('w-full h-[80vh] items-center justify-center bg-gray-50'):
        # Картка для красивого оформлення
        with ui.card().classes('items-center p-12 shadow-lg rounded-2xl bg-white w-full max-w-lg text-center'):
            # Велика іконка будівництва/розробки (можна змінити на 'build' або 'code')
            ui.icon('engineering', size='120px', color='orange-5').classes('mb-4')

            # Головний напис
            ui.label('Сторінка в процесі розробки').classes('text-3xl font-bold text-gray-800')

            # Підзаголовок
            ui.label('...Зачекайте').classes('text-xl text-gray-500 mt-2 mb-8 animate-pulse')

            # Прогрес-бар (value від 0.0 до 1.0, тому 0.5 - це 50%)
            ui.linear_progress(value=0.5).props('color="orange" rounded size="20px"').classes('w-full')

            # Текст під прогрес-баром
            ui.label('Готовність: 50%').classes('text-sm text-gray-400 mt-2 font-mono')
