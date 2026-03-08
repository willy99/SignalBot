from nicegui import ui, run
import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict
from service.constants import TASK_STATUS_COMPLETED, TASK_STATUS_IN_PROGRESS, TASK_STATUS_NEW, MONTHS


def render_calendar_page(task_ctrl, ctx):
    ui.label('Календар задач').classes('w-full text-center text-3xl font-bold mb-6')

    # Головний стейт календаря
    now = datetime.now()
    state = {
        'year': now.year,
        'month': now.month,
        'assignee_id': ctx.user_id,  # За замовчуванням - мої задачі
        'task_type_filter': 'all',
        'tasks': []
    }

    # Словники для фільтрів (замініть на реальні дані з вашої БД, якщо є)
    assignee_options = {
        'all': 'Всі співробітники',
        ctx.user_id: 'Тільки мої задачі'
    }
    task_type_options = {
        'all': 'Всі типи',
        'СЗЧ': 'СЗЧ',
        'Службове розслідування': 'Службове розслідування',
        'Інше': 'Інше'
    }

    # Контейнер для самого календаря, який ми будемо перемальовувати
    calendar_container = ui.column().classes('w-full max-w-7xl mx-auto shadow-md rounded-lg overflow-hidden border')

    # =========================================================
    # 1. ПАНЕЛЬ КЕРУВАННЯ ТА ФІЛЬТРІВ
    # =========================================================
    with ui.row().classes('w-full max-w-7xl mx-auto items-end justify-between mb-4 gap-4'):

        # Блок навігації по місяцях
        with ui.row().classes('items-center gap-4 bg-gray-50 p-2 rounded-lg border'):
            ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round color="primary"')

            # Назва місяця та року
            month_label = ui.label('').classes('text-xl font-bold text-gray-700 w-48 text-center')

            ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round color="primary"')

        # Блок фільтрів
        with ui.row().classes('items-center gap-4 flex-grow justify-end'):
            ui.select(options=assignee_options, label='Виконавець') \
                .bind_value(state, 'assignee_id') \
                .on_value_change(lambda: refresh_data()) \
                .classes('w-48')

            ui.select(options=task_type_options, label='Тип задачі') \
                .bind_value(state, 'task_type_filter') \
                .on_value_change(lambda: refresh_data()) \
                .classes('w-48')

            refresh_btn = ui.button(icon='refresh', on_click=lambda: refresh_data()).props('outline color="primary"')

    # =========================================================
    # 2. ФЕТЧИНГ ДАНИХ ТА МАЛЮВАННЯ КАЛЕНДАРЯ
    # =========================================================
    def refresh_data():
        refresh_btn.props('loading')
        try:
            # Визначаємо перший і останній день місяця для оптимізації запиту
            # (забираємо трохи з запасом - 7 днів назад і 7 вперед для сітки)
            _, days_in_month = calendar.monthrange(state['year'], state['month'])
            start_date = date(state['year'], state['month'], 1) - timedelta(days=7)
            end_date = date(state['year'], state['month'], days_in_month) + timedelta(days=7)

            search_filter = {
                'assignee_id': state['assignee_id'] if state['assignee_id'] != 'all' else None,
                'task_type_filter': state['task_type_filter'],
                'period_filter': 'all',  # Ми беремо 'all', бо відсічемо по датах нижче
                'created_from': start_date.strftime('%Y-%m-%d'),
                'created_to': end_date.strftime('%Y-%m-%d'),
            }

            # Забираємо задачі через ваш контролер
            tasks = task_ctrl.get_all_tasks(ctx, search_filter)
            state['tasks'] = tasks or []

            draw_calendar()
        except Exception as e:
            ui.notify(f'Помилка завантаження задач: {e}', type='negative')
            print(e)
        finally:
            refresh_btn.props(remove='loading')

    def draw_calendar():
        calendar_container.clear()

        # Оновлюємо лейбл (наприклад: "Березень 2026")
        month_label.set_text(f"{MONTHS[state['month']]} {state['year']}")

        # Групуємо задачі по даті дедлайну (ключ: рядок 'YYYY-MM-DD')
        tasks_by_date = defaultdict(list)
        for t in state['tasks']:
            # Використовуємо getattr замість .get() або пряме звернення t.task_deadline
            deadline = getattr(t, 'task_deadline', None)
            if deadline:
                # Відрізаємо час, залишаємо тільки дату
                date_str = str(deadline)[:10]
                tasks_by_date[date_str].append(t)

        with calendar_container:
            # Сітка 7 колонок, gap-[1px] та bg-gray-200 роблять красиві тонкі рамки між клітинками
            with ui.grid(columns=7).classes('w-full bg-gray-200 gap-[1px]'):

                # ШАПКА: Дні тижня
                days_of_week = ['Пн', 'Вв', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
                for day_name in days_of_week:
                    ui.label(day_name).classes('bg-blue-50 text-center font-bold p-2 text-blue-900')

                # ГЕНЕРАЦІЯ КЛІТИНОК
                cal = calendar.Calendar(firstweekday=0)  # Тиждень починається з понеділка
                month_days = cal.monthdatescalendar(state['year'], state['month'])

                today_str = datetime.now().strftime('%Y-%m-%d')

                for week in month_days:
                    for d in week:
                        date_str = d.strftime('%Y-%m-%d')
                        is_current_month = (d.month == state['month'])
                        is_today = (date_str == today_str)

                        # Візуальні стилі клітинки
                        bg_class = 'bg-white' if is_current_month else 'bg-gray-100 text-gray-400'
                        if is_today: bg_class = 'bg-blue-50'  # Підсвічуємо сьогоднішній день

                        # Сама клітинка дня
                        with ui.column().classes(
                                f'{bg_class} p-2 min-h-[120px] w-full hover:bg-gray-50 transition-colors gap-1'):

                            # Номер дня
                            day_lbl_class = 'font-bold text-sm mb-1'
                            if is_today:
                                day_lbl_class += ' bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center'
                            ui.label(str(d.day)).classes(day_lbl_class)

                            # Малюємо бейджі задач для цього дня
                            day_tasks = tasks_by_date.get(date_str, [])
                            for t in day_tasks:
                                # Використовуємо getattr для безпечного доступу до атрибутів об'єкта
                                status = getattr(t, 'task_status', '')
                                subject = getattr(t, 'task_subject', 'Без назви')  # Виправлено на task_subject
                                task_id = getattr(t, 'id', None)

                                # Кольорове кодування
                                color = 'grey'
                                icon = 'task'
                                if status == TASK_STATUS_COMPLETED:
                                    color = 'green'
                                    icon = 'check_circle'
                                elif status == TASK_STATUS_IN_PROGRESS:
                                    color = 'orange'
                                    icon = 'play_circle'
                                elif status == TASK_STATUS_NEW:
                                    color = 'red'
                                    icon = 'fiber_new'

                                # Клікабельний бейдж
                                # Увага: використовуємо tid=task_id у лямбді, щоб уникнути проблеми пізнього зв'язування
                                with ui.button(on_click=lambda tid=task_id: open_task(tid)) \
                                        .props(f'color="{color}" outline size="sm" no-caps align="left"') \
                                        .classes('w-full truncate px-1 py-0 min-h-0 h-6 mb-[2px] shadow-none border'):

                                    with ui.row().classes('items-center gap-1 w-full flex-nowrap'):
                                        ui.icon(icon, size='14px')
                                        ui.label(subject).classes(
                                            'truncate text-[11px] font-medium leading-none').style('max-width: 80%')

    # =========================================================
    # ДОПОМІЖНІ ФУНКЦІЇ
    # =========================================================
    def change_month(delta):
        """Гортає місяць назад/вперед"""
        state['month'] += delta
        if state['month'] > 12:
            state['month'] = 1
            state['year'] += 1
        elif state['month'] < 1:
            state['month'] = 12
            state['year'] -= 1

        # Після зміни місяця оновлюємо дані
        ui.timer(0, refresh_data, once=True)

    def open_task(task_id):
        ui.navigate.to(f'/tasks/edit/{task_id}')

    ui.timer(0.1, refresh_data, once=True)