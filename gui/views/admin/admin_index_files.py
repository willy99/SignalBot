from nicegui import ui
import asyncio
import config
import time

from gui.services.auth_manager import AuthManager
from service.storage.FileCacher import FileCacheManager
from service.storage.ErdrCacher import ErdrCacheManager


def render_indexing_page(doc_manager: FileCacheManager, erdr_manager: ErdrCacheManager, auth_manager: AuthManager):
    # Зберігаємо посилання на те, який менеджер працював останнім,
    # щоб графік не зникав після завершення. За замовчуванням - документи.
    state = {'last_active_manager': doc_manager, 'last_type': 'doc'}

    chart_options = {
        'title': {'text': 'Прогрес індексації за роками'},
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
        ui.label('Керування індексами бази даних').classes('text-2xl font-bold')

        with ui.row().classes('items-center gap-4 w-full'):
            # Кнопка для звичайних документів
            doc_index_btn = ui.button('ІНДЕКСАЦІЯ ДОКУМЕНТІВ', icon='folder_open',
                                      on_click=lambda: start_doc_indexing())
            doc_index_btn.loading = False

            # Кнопка для ЄРДР (інший колір)
            erdr_index_btn = ui.button('ІНДЕКСАЦІЯ ЄРДР', icon='gavel', color='indigo',
                                       on_click=lambda: start_erdr_indexing())
            erdr_index_btn.loading = False

            ui.spinner(size='lg').bind_visibility_from(doc_index_btn, 'loading')
            ui.spinner(size='lg', color='indigo').bind_visibility_from(erdr_index_btn, 'loading')

        with ui.row().classes('items-center gap-4 w-full mt-2'):
            status_text = ui.label('Готовий до роботи').classes('text-gray-500 font-medium')
            active_stats = ui.label('').classes('text-orange-500 font-mono')
            stats_label = ui.label('').classes('text-blue-600 font-bold')

        chart = ui.echart(chart_options).classes('w-full h-96 shadow-lg border rounded-xl p-4')

    def update_ui_from_manager():
        """Синхронізує елементи UI з поточними даними активного менеджера"""
        if doc_index_btn.is_deleted:
            return

        is_doc_running = doc_manager.is_indexing
        is_erdr_running = erdr_manager.is_indexing
        is_any_running = is_doc_running or is_erdr_running

        doc_index_btn.loading = is_doc_running
        erdr_index_btn.loading = is_erdr_running

        # Оновлюємо візуальний стан самої кнопки (щоб зник кружечок всередині кнопки)
        if is_doc_running:
            doc_index_btn.props('loading')
        else:
            doc_index_btn.props(remove='loading')

        if is_erdr_running:
            erdr_index_btn.props('loading')
        else:
            erdr_index_btn.props(remove='loading')

        # 1. Блокуємо/Розблоковуємо кнопки
        if is_any_running:
            doc_index_btn.disable()
            erdr_index_btn.disable()
        else:
            doc_index_btn.enable()
            erdr_index_btn.enable()

        # 2. Керуємо станом завантаження (спінерами в кнопках)
        doc_index_btn.props(f"{'loading' if is_doc_running else 'remove=loading'}")
        erdr_index_btn.props(f"{'loading' if is_erdr_running else 'remove=loading'}")

        # 3. Визначаємо, звідки брати дані для графіка та статистики
        if is_doc_running:
            active_m = doc_manager
            state['last_active_manager'] = doc_manager
            state['last_type'] = 'doc'
            chart.options['series'][0]['itemStyle']['color'] = '#5470c6'  # Синій для документів
            chart.options['title']['text'] = 'Прогрес індексації Документів'
            status_text.set_text('Йде сканування Документів...')
        elif is_erdr_running:
            active_m = erdr_manager
            state['last_active_manager'] = erdr_manager
            state['last_type'] = 'erdr'
            chart.options['series'][0]['itemStyle']['color'] = '#3f51b5'  # Індиго для ЄРДР
            chart.options['title']['text'] = 'Прогрес індексації ЄРДР'
            status_text.set_text('Йде сканування бази ЄРДР...')
        else:
            active_m = state['last_active_manager']
            status_text.set_text('Готовий до роботи')

        # 4. Оновлюємо графік
        stats = getattr(active_m, 'current_stats', {}) or {}
        # Сортуємо ключі як рядки, щоб не було помилок порівняння
        available_keys = sorted([str(k) for k in stats.keys() if k is not None])
        chart_data = [stats.get(k, 0) for k in available_keys]

        if available_keys:
            chart.options['xAxis']['data'] = available_keys
            chart.options['series'][0]['data'] = chart_data
            chart.update()

        # 5. Оновлюємо текстову статистику
        total_f = getattr(active_m, 'total_count', 0)
        total_p = getattr(active_m, 'total_persons', 0)

        if is_any_running and getattr(active_m, 'start_time', None):
            elapsed = int(time.time() - active_m.start_time)
            timer_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            active_stats.set_text(f'⏱ {timer_str} | 📂 Файлів: {total_f} | 👥 Осіб: {total_p}')
            stats_label.set_text('')
        else:
            active_stats.set_text('')
            if total_f > 0:
                doc_type = "Документів" if state['last_type'] == 'doc' else "Витягів ЄРДР"
                stats_label.set_text(f'📊 Результат ({doc_type}): {total_f} файлів | 👥 Знайдено осіб: {total_p}')

    # --- Функції запуску ---
    async def start_doc_indexing():
        if doc_manager.is_indexing or erdr_manager.is_indexing:
            ui.notify('Система вже зайнята індексацією. Дочекайтесь завершення.', type='warning')
            return

        doc_manager.current_stats = {}
        doc_manager.start_time = time.time()
        doc_manager.total_count = 0
        doc_manager.total_persons = 0

        asyncio.create_task(auth_manager.execute(
            doc_manager.build_cache,
            auth_manager.get_current_context(),
            config.DOCUMENT_STORAGE_PATH
        ))

    async def start_erdr_indexing():
        if doc_manager.is_indexing or erdr_manager.is_indexing:
            ui.notify('Система вже зайнята індексацією. Дочекайтесь завершення.', type='warning')
            return

        erdr_manager.current_stats = {}
        erdr_manager.start_time = time.time()
        erdr_manager.total_count = 0
        erdr_manager.total_persons = 0

        asyncio.create_task(auth_manager.execute(
            erdr_manager.build_cache,
            auth_manager.get_current_context(),
            config.ERDR_DOCUMENT_STORAGE_PATH
        ))

    # Таймер автоматично оновлює UI щосекунди
    ui.timer(1.0, update_ui_from_manager)

    # Початкове відмальовування
    update_ui_from_manager()