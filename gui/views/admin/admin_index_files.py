from nicegui import ui, run
import asyncio
import config
from service.storage.FileCacher import FileCacheManager
import time


def render_indexing_page(manager: FileCacheManager):
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
            index_btn.loading = False

            ui.spinner(size='lg').bind_visibility_from(index_btn, 'loading')

            status_text = ui.label('Готовий до роботи').classes('text-gray-500 font-medium')

            # Таймер та лічильник під час роботи
            active_stats = ui.label('').classes('text-orange-500 font-mono')

            # Фінальна статистика
            stats_label = ui.label('').classes('text-blue-600 font-bold')

        chart = ui.echart(chart_options).classes('w-full h-96 shadow-lg border rounded-xl p-4')

    async def start_indexing():
        stats_label.set_text('')
        active_stats.set_text('')
        start_time = time.time()
        total_files = 0  # Ця змінна буде оновлюватися через nonlocal
        is_running = True

        index_btn.loading = True
        index_btn.props('loading')
        status_text.set_text('Йде сканування...')

        loop = asyncio.get_event_loop()

        # Функція для оновлення таймера в реальному часі
        async def update_timer():
            while is_running:
                now = time.time()
                elapsed = int(now - start_time)
                # Форматування в 00:00:00
                timer_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
                active_stats.set_text(f'⏱ {timer_str} | 📂 Знайдено: {total_files}')
                await asyncio.sleep(1)

        def handle_progress(stats):
            nonlocal total_files  # ВАЖЛИВО: дозволяє змінювати змінну ззовні
            total_files = sum(stats.values())

            def update():
                available_years = sorted(stats.keys())
                chart.options['xAxis']['data'] = available_years
                chart.options['series'][0]['data'] = [stats.get(y, 0) for y in available_years]
                chart.update()
                # Ми оновлюємо total_files і в таймері, і тут для надійності

            loop.call_soon_threadsafe(update)

        # Запускаємо таймер як фонову задачу NiceGUI
        timer_task = asyncio.create_task(update_timer())

        try:
            await run.io_bound(manager.build_cache,
                               config.DOCUMENT_STORAGE_PATH,
                               progress_callback=handle_progress)
            ui.notify('Індексація завершена!', type='positive')
        except Exception as e:
            ui.notify(f'Помилка: {e}', type='negative')
            status_text.set_text(f'❌ Помилка: {str(e)}')
        finally:
            is_running = False
            timer_task.cancel()  # Зупиняємо таймер

            end_time = time.time()
            duration = int(end_time - start_time)
            time_str = time.strftime('%H:%M:%S', time.gmtime(duration))

            index_btn.loading = False
            index_btn.props(remove='loading')

            status_text.set_text('Готовий до роботи.')
            active_stats.set_text('')  # Прибираємо проміжний статус
            stats_label.set_text(f'📊 Результат: {total_files} файлів. Час виконання: {time_str}')