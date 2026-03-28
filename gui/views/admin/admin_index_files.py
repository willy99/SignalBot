from nicegui import ui, run, app
import asyncio
import config
import time

from gui.services.auth_manager import AuthManager
from service.storage.FileCacher import FileCacheManager


async def render_indexing_page(manager: FileCacheManager, auth_manager: AuthManager):
    chart_options = {
        'title': {'text': 'Прогрес індексації за роками та папками'},
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'xAxis': {'type': 'category', 'data': []},
        'yAxis': {'type': 'value', 'name': 'Файлів', 'minInterval': 1},
        'series': [{
            'name': 'Кількість файлів',
            'type': 'bar',
            'data': [],
            'itemStyle': {'color': '#5470c6'},
            'label': {'show': True, 'position': 'top'}
        }]
    }

    with ui.column().classes('w-full p-8 gap-4'):
        ui.label('Керування індексом документів').classes('text-2xl font-bold')

        with ui.row().classes('items-center gap-4 w-full'):
            index_btn = ui.button('ЗАПУСТИТИ ІНДЕКСАЦІЮ', icon='play_arrow',
                                  on_click=lambda: start_indexing())

            # --- ВИПРАВЛЕННЯ 1: Додаємо атрибут вручну, щоб bind спрацював ---
            index_btn.loading = False

            ui.spinner(size='lg').bind_visibility_from(index_btn, 'loading')

            status_text = ui.label('Готовий до роботи').classes('text-gray-500 font-medium')
            active_stats = ui.label('').classes('text-orange-500 font-mono')
            stats_label = ui.label('').classes('text-blue-600 font-bold')

        chart = ui.echart(chart_options).classes('w-full h-96 shadow-lg border rounded-xl p-4')

    def update_ui_from_manager():
        """Синхронізує елементи UI з поточними даними в менеджері"""
        # --- ВИПРАВЛЕННЯ 2: Перевірка на існування елементів (захист від RuntimeError) ---
        if index_btn.is_deleted:
            return 0

        stats = manager.current_stats or {}
        available_years = sorted(stats.keys())

        chart.options['xAxis']['data'] = available_years
        chart.options['series'][0]['data'] = [stats.get(y, 0) for y in available_years]
        chart.update()

        total = sum(stats.values())

        if manager.is_indexing and manager.start_time:
            elapsed = int(time.time() - manager.start_time)
            timer_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            active_stats.set_text(f'⏱ {timer_str} | 📂 Знайдено: {total}')
            index_btn.loading = True
            index_btn.props('loading')
        else:
            index_btn.loading = False
            index_btn.props(remove='loading')
            active_stats.set_text('')
            if total > 0:
                stats_label.set_text(f'📊 Результат: {total} файлів.')

        return total

    async def start_indexing():
        if manager.is_indexing:
            ui.notify('Індексація вже триває', type='warning')
            return

        manager.current_stats = {}
        manager.start_time = time.time()
        stats_label.set_text('')

        index_btn.loading = True
        index_btn.props('loading')
        status_text.set_text('Йде сканування...')

        # Запускаємо процес
        asyncio.create_task(auth_manager.execute(manager.build_cache, auth_manager.get_current_context(), config.DOCUMENT_STORAGE_PATH))

    # --- ВИПРАВЛЕННЯ 3: Використовуємо ui.timer замість нескінченного циклу ---
    # Він автоматично зупиниться, коли ви підете зі сторінки
    ui.timer(1.0, update_ui_from_manager)

    # Початкове оновлення при вході
    update_ui_from_manager()