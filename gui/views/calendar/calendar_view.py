from nicegui import ui, run
import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict

from dics.deserter_xls_dic import TASK_TYPES
from service.constants import TASK_STATUS_COMPLETED, TASK_STATUS_IN_PROGRESS, TASK_STATUS_NEW, MONTHS, DB_DATETIME_FORMAT, DB_DATE_FORMAT


def render_calendar_page(task_ctrl, ctx):
    ui.label('Календар задач').classes('w-full text-center text-3xl font-bold mb-6')

    # Головний стейт календаря
    now = datetime.now()
    state = {
        'year': now.year,
        'month': now.month,
        'assignee_id': ctx.user_id,
        'task_type_filter': 'all',
        'tasks': []
    }

    assignee_options = {
        'all': 'Всі співробітники',
        ctx.user_id: 'Тільки мої задачі'
    }

    task_type_options = {'all': 'Всі типи'}
    for t in TASK_TYPES.keys():
        task_type_options[t] = t

    calendar_container = ui.column().classes('w-full max-w-7xl mx-auto shadow-md rounded-lg overflow-hidden border')

    # =========================================================
    # 1. ПАНЕЛЬ КЕРУВАННЯ ТА ФІЛЬТРІВ
    # =========================================================
    with ui.row().classes('w-full max-w-7xl mx-auto items-end justify-between mb-4 gap-4 flex-wrap'):

        # Блок навігації по місяцях
        with ui.row().classes('items-center gap-2 sm:gap-4 bg-gray-50 p-2 rounded-lg border flex-grow sm:flex-grow-0 justify-center'):
            ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round color="primary"')
            month_label = ui.label('').classes('text-lg sm:text-xl font-bold text-gray-700 w-32 sm:w-48 text-center')
            ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round color="primary"')

        # Блок фільтрів
        with ui.row().classes('items-center gap-2 sm:gap-4 flex-grow justify-start sm:justify-end flex-wrap'):
            ui.select(options=assignee_options, label='Виконавець') \
                .bind_value(state, 'assignee_id') \
                .on_value_change(lambda: refresh_data()) \
                .classes('w-full sm:w-48')

            ui.select(options=task_type_options, label='Тип задачі') \
                .bind_value(state, 'task_type_filter') \
                .on_value_change(lambda: refresh_data()) \
                .classes('w-full sm:w-48')

            refresh_btn = ui.button(icon='refresh', on_click=lambda: refresh_data()).props('outline color="primary"').classes('w-full sm:w-auto')

    # =========================================================
    # 2. ФЕТЧИНГ ДАНИХ ТА МАЛЮВАННЯ КАЛЕНДАРЯ
    # =========================================================
    def refresh_data():
        refresh_btn.props('loading')
        try:
            _, days_in_month = calendar.monthrange(state['year'], state['month'])
            start_date = date(state['year'], state['month'], 1) - timedelta(days=7)
            end_date = date(state['year'], state['month'], days_in_month) + timedelta(days=7)

            search_filter = {
                'assignee_id': state['assignee_id'] if state['assignee_id'] != 'all' else None,
                'task_type_filter': state['task_type_filter'],
                'period_filter': 'all',
                'created_from': start_date.strftime(DB_DATE_FORMAT),
                'created_to': end_date.strftime(DB_DATE_FORMAT),
            }

            tasks = task_ctrl.get_all_tasks(ctx, search_filter)
            state['tasks'] = tasks or []
            draw_calendar()
        except Exception as e:
            ui.notify(f'Помилка завантаження задач: {e}', type='negative')
        finally:
            refresh_btn.props(remove='loading')

    def draw_calendar():
        calendar_container.clear()
        month_label.set_text(f"{MONTHS[state['month']]} {state['year']}")

        tasks_by_date = defaultdict(list)
        for t in state['tasks']:
            # MODIFICATION: Use created_date if task_deadline is None so tasks show up somewhere
            target_date = getattr(t, 'task_deadline', None) or getattr(t, 'created_date', None)

            if target_date:
                # Ensure it's a string in YYYY-MM-DD format
                if isinstance(target_date, datetime):
                    date_str = target_date.strftime(DB_DATE_FORMAT)
                elif isinstance(target_date, str):
                    date_str = target_date[:10]
                else:
                    continue  # Skip if unparseable

                tasks_by_date[date_str].append(t)

        with calendar_container:
            with ui.grid(columns=7).classes('w-full bg-gray-200 gap-[1px]'):
                days_of_week = ['Пн', 'Вв', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
                for day_name in days_of_week:
                    ui.label(day_name).classes('bg-blue-50 text-center font-bold p-1 sm:p-2 text-blue-900 text-xs sm:text-base')

                cal = calendar.Calendar(firstweekday=0)
                month_days = cal.monthdatescalendar(state['year'], state['month'])
                today_str = datetime.now().strftime(DB_DATE_FORMAT)

                for week in month_days:
                    for d in week:
                        date_str = d.strftime(DB_DATE_FORMAT)
                        is_current_month = (d.month == state['month'])
                        is_today = (date_str == today_str)

                        bg_class = 'bg-white' if is_current_month else 'bg-gray-100'
                        text_class = 'text-gray-800' if is_current_month else 'text-gray-400'
                        if is_today: bg_class = 'bg-blue-50'

                        with ui.column().classes(f'{bg_class} p-1 sm:p-2 min-h-[80px] sm:min-h-[120px] w-full hover:bg-gray-50 transition-colors gap-1'):
                            day_lbl_class = f'font-bold text-xs sm:text-sm mb-1 {text_class}'
                            if is_today:
                                day_lbl_class += ' bg-blue-500 !text-white rounded-full w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center'
                            ui.label(str(d.day)).classes(day_lbl_class)

                            day_tasks = tasks_by_date.get(date_str, [])
                            for t in day_tasks:
                                status = getattr(t, 'task_status', '')
                                subject = getattr(t, 'task_subject', 'Без назви')
                                task_id = getattr(t, 'id', None)

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

                                with ui.button(on_click=lambda tid=task_id: open_task(tid)) \
                                        .props(f'color="{color}" outline size="sm" no-caps align="left"') \
                                        .classes('w-full truncate px-1 py-0 min-h-0 h-5 sm:h-6 mb-[2px] shadow-none border'):
                                    with ui.row().classes('items-center gap-1 w-full flex-nowrap'):
                                        ui.icon(icon, size='12px').classes('hidden sm:block')
                                        ui.label(subject).classes('truncate text-[10px] sm:text-[11px] font-medium leading-none').style('max-width: 90%')

    # =========================================================
    # ДОПОМІЖНІ ФУНКЦІЇ
    # =========================================================
    def change_month(delta):
        state['month'] += delta
        if state['month'] > 12:
            state['month'] = 1
            state['year'] += 1
        elif state['month'] < 1:
            state['month'] = 12
            state['year'] -= 1
        ui.timer(0, refresh_data, once=True)

    def open_task(task_id):
        if task_id:
            ui.navigate.to(f'/tasks/edit/{task_id}')

    ui.timer(0.1, refresh_data, once=True)