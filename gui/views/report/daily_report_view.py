from nicegui import ui, run
from datetime import datetime
from dics.deserter_xls_dic import *
from gui.services.request_context import RequestContext
from gui.controllers.task_controller import TaskController
from service.constants import TASK_STATUS_IN_PROGRESS
from domain.task import Task

def render_daily_report_page(report_ctrl, task_ctrl: TaskController, ctx: RequestContext):
    ui.label('Щоденний звіт: Додані записи СЗЧ').classes('w-full text-center text-3xl font-bold mb-6')

    state = {'data': [], 'returns': []}

    # Панель керування: Вибір дати та кнопка
    with ui.row().classes(
            'w-full items-center justify-between mb-4 px-4 max-w-7xl mx-auto bg-gray-50 p-4 rounded-lg border'):
        with ui.row().classes('items-center gap-4'):
            ui.label('Оберіть дату:').classes('font-bold text-gray-700')

            date_input = ui.input(value=datetime.now().strftime('%d.%m.%Y')).props('outlined dense')
            with date_input.add_slot('append'):
                ui.icon('edit_calendar').classes('cursor-pointer')
                with ui.menu():
                    ui.date().bind_value(date_input).props('mask="DD.MM.YYYY"')

        generate_btn = ui.button('Сформувати звіт', icon='analytics', on_click=lambda: load_data()) \
            .props('color="primary" elevated')
        export_btn = ui.button('В задачу', icon='add_task', on_click=lambda: create_report_task()) \
            .props('color="secondary" outline') \
            .bind_visibility_from(state, 'data', backward=lambda d: len(d) > 0)  # Показувати тільки якщо є дані
    table_container = ui.column().classes('w-full max-w-7xl mx-auto shadow-md rounded-lg overflow-hidden border')

    async def load_data():
        generate_btn.props('loading')
        table_container.clear()
        try:
            target_date = datetime.strptime(date_input.value, '%d.%m.%Y').date()

            data = await run.io_bound(report_ctrl.get_daily_added_records_report, ctx,
                                      target_date)  # Заберіть ctx, якщо його немає в сигнатурі методу
            state['data'] = data

            # Розділяємо дані по підрозділах
            data_A0224 = [r for r in data if r.get('sheet_name') == 'А0224']
            data_A7018 = [r for r in data if r.get('sheet_name') == 'А7018']

            added_names = [item['name'] for item in data]

            # 2. Завантажуємо ПОВЕРНЕННЯ (з логів + ексель)
            return_data = await run.io_bound(report_ctrl.get_daily_added_files_report, ctx, target_date, added_names)
            state['returns'] = return_data

            columns = [
                {'name': 'ins_date', 'label': COLUMN_INSERT_DATE, 'field': 'ins_date', 'align': 'left'},
                {'name': 'name', 'label': COLUMN_NAME, 'field': 'name', 'align': 'left'},
                {'name': 'title', 'label': COLUMN_TITLE, 'field': 'title', 'align': 'left'},
                {'name': 'subunit', 'label': COLUMN_SUBUNIT, 'field': 'subunit', 'align': 'left'},
                {'name': 'call_date', 'label': COLUMN_ENLISTMENT_DATE, 'field': 'call_date', 'align': 'left'},
                {'name': 'des_date', 'label': COLUMN_DESERTION_DATE, 'field': 'des_date', 'align': 'left',
                 'classes': 'font-bold'},
                {'name': 'term_days', 'label': COLUMN_SERVICE_DAYS, 'field': 'term_days', 'align': 'center'},
            ]

            with table_container:
                if not data:
                    ui.label(f'За {date_input.value} нових записів не знайдено.').classes(
                        'text-gray-500 italic text-lg p-6 text-center w-full')
                else:
                    # ==============================
                    # ТАБЛИЦЯ 1: А0224 (Синя)
                    # ==============================
                    if data_A0224:
                        with ui.row().classes('w-full bg-blue-50 p-3 border-b items-center justify-between'):
                            ui.label(f'ВЧ А0224 | Додано записів: {len(data_A0224)}').classes(
                                'font-bold text-blue-800 text-lg')

                        table_a0224 = ui.table(columns=columns, rows=data_A0224, row_key='name').classes(
                            'w-full mb-6').props('flat bordered')
                        table_a0224.add_slot('body-cell-term_days', '''
                            <q-td :props="props">
                                <q-badge :color="props.value > 30 ? 'green' : 'orange'" class="text-sm font-bold p-1">
                                    {{ props.value }} дн.
                                </q-badge>
                            </q-td>
                        ''')

                    # ==============================
                    # ТАБЛИЦЯ 2: А7018 (Зелена)
                    # ==============================
                    if data_A7018:
                        with ui.row().classes('w-full bg-green-50 p-3 border-b border-t items-center justify-between'):
                            ui.label(f'ВЧ А7018 | Додано записів: {len(data_A7018)}').classes(
                                'font-bold text-green-800 text-lg')

                        table_a7018 = ui.table(columns=columns, rows=data_A7018, row_key='name').classes(
                            'w-full mb-2').props('flat bordered')
                        table_a7018.add_slot('body-cell-term_days', '''
                            <q-td :props="props">
                                <q-badge :color="props.value > 30 ? 'green' : 'orange'" class="text-sm font-bold p-1">
                                    {{ props.value }} дн.
                                </q-badge>
                            </q-td>
                        ''')

                    # ==========================================
                    # ТАБЛИЦЯ 2: ПОВЕРНЕННЯ
                    # ==========================================
                    with ui.row().classes('w-full bg-green-50 p-3 border-b border-t items-center justify-between'):
                        ui.label(f'Повернулися: {len(return_data)}').classes('font-bold text-green-800 text-lg')

                    if not return_data:
                        ui.label('Записів про повернення в логах не знайдено.').classes(
                            'text-gray-500 italic p-4 text-center w-full')
                    else:
                        columns_returns = [
                            {'name': 'id_number', 'label': 'ID Excel', 'field': 'id_number', 'align': 'left'},
                            {'name': 'ret_date', 'label': 'Дата повернення', 'field': 'ret_date', 'align': 'left',
                             'classes': 'text-green-700 font-bold'},
                            {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left',
                                'classes': 'font-bold'},
                            {'name': 'title', 'label': 'Звання', 'field': 'title', 'align': 'left'},
                            {'name': 'subunit', 'label': 'Підрозділ', 'field': 'subunit', 'align': 'left'},
                            {'name': 'des_date', 'label': 'Був в СЗЧ з', 'field': 'des_date', 'align': 'left'},
                        ]

                        ui.table(columns=columns_returns, rows=return_data, row_key='id_number').classes(
                            'w-full').props('flat bordered')
        except ValueError:
            ui.notify('Неправильний формат дати. Використовуйте ДД.ММ.РРРР', type='negative')
        except Exception as e:
            ui.notify(f'Помилка формування звіту: {e}', type='negative')
            print(f"Помилка: {e}")
        finally:
            generate_btn.props(remove='loading')

    ui.timer(0.1, load_data, once=True)

    async def create_report_task():
        # Тепер задача має сенс, якщо є або нові СЗЧ, або повернення
        if not state.get('data') and not state.get('returns'):
            ui.notify('Немає даних для експорту!', type='warning')
            return

        export_btn.props('loading')
        try:
            target_date_str = date_input.value

            # Починаємо формувати HTML
            details = f"<h3>📊 Щоденне: {target_date_str}</h3>"

            # ==========================================
            # 1. ДОДАНІ СЗЧ (Ті що пішли)
            # ==========================================
            added_data = state.get('data', [])
            if added_data:
                details += "<p><b>⬅️ ПІШЛИ В СЗЧ:</b></p>"
                data_A0224 = [r for r in added_data if r.get('sheet_name') == 'А0224']
                data_A7018 = [r for r in added_data if r.get('sheet_name') == 'А7018']

                if data_A0224:
                    details += f"<p>👉 <b>ВЧ А0224 (Додано: {len(data_A0224)})</b></p><ul>"
                    for r in data_A0224:
                        details += f"<li><b>{r['name']}</b> ({r.get('title', 'Не вказано')}, {r.get('subunit', 'Не вказано')}) — СЗЧ з {r.get('desertion_place', 'Не вказано')} ({r.get('term_days', 0)} дн.)</li>"
                    details += "</ul>"

                if data_A7018:
                    details += f"<p>👉 <b>ВЧ А7018 (Додано: {len(data_A7018)})</b></p><ul>"
                    for r in data_A7018:
                        details += f"<li><b>{r['name']}</b> ({r.get('title', 'Не вказано')}, {r.get('subunit', 'Не вказано')}) — СЗЧ з {r.get('desertion_place', 'Не вказано')} ({r.get('term_days', 0)} дн.)</li>"
                    details += "</ul>"

            # ==========================================
            # 2. ПОВЕРНУЛИСЯ З СЗЧ
            # ==========================================
            return_data = state.get('returns', [])
            if return_data:
                details += f"<p><b>↪️ ПОВЕРНУЛИСЯ ({len(return_data)}):</b></p><ul>"
                for r in return_data:
                    name = r.get('name', 'Невідомо')
                    title = r.get('title', 'Не вказано')
                    subunit = r.get('subunit', 'Не вказано')
                    des_date = r.get('des_date', 'Невідомо')
                    ret_date = r.get('ret_date', 'Не вказано')

                    details += f"<li><b>{name}</b> ({title}, {subunit}) — Був у СЗЧ з {des_date}, повернувся {ret_date}</li>"
                details += "</ul>"

            now = datetime.now()
            deadline = now.replace(hour=23, minute=59, second=59)

            task_model = Task(
                created_by=ctx.user_id,
                assignee=ctx.user_id,
                task_status=TASK_STATUS_IN_PROGRESS,
                task_type='Звіти',
                task_subject=f'Звіт по СЗЧ за {target_date_str}',
                task_details=details.strip(),
                task_deadline=deadline
            )

            await run.io_bound(task_ctrl.create_task, ctx, task_model)

            ui.notify('Задачу успішно створено!', type='positive', icon='check_circle')

        except Exception as e:
            ui.notify(f'Помилка створення задачі: {e}', type='negative')
            print(f"Помилка створення задачі: {e}")
        finally:
            export_btn.props(remove='loading')
