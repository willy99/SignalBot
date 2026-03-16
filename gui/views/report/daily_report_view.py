from nicegui import ui, run
from datetime import datetime
from dics.deserter_xls_dic import *
from gui.controllers.report_controller import ReportController
from gui.services.request_context import RequestContext
from gui.controllers.task_controller import TaskController
from service.constants import TASK_STATUS_IN_PROGRESS
from domain.task import Task
from gui.tools.ui_components import date_input, fix_date

def get_rank_category(title: str) -> str:
    """Визначає категорію військовослужбовця за званням."""
    if not title:
        return 'Солдати'
    title = str(title).lower()
    if any(x in title for x in ['лейтенант', 'капітан', 'майор', 'полковник']):
        return 'Офіцери'
    if any(x in title for x in ['сержант', 'старшина']):
        return 'Сержанти'
    return 'Солдати'


def render_daily_report_page(report_ctrl: ReportController, task_ctrl: TaskController, ctx: RequestContext):
    ui.label('Щоденний звіт').classes('w-full text-center text-3xl font-bold mb-6')

    state = {'data': [], 'returns': [], 'archive': [], 'matrix1_rows': [], 'matrix1_cols': [], 'matrix2_rows': [], 'matrix2_cols': []}

    with ui.row().classes('w-full items-center justify-between mb-4 px-4 max-w-7xl mx-auto bg-gray-50 p-4 rounded-lg border'):
        with ui.row().classes('items-center gap-4'):
            ui.label('Оберіть дату:').classes('font-bold text-gray-700')

            date_filter = date_input('Дата формування', state, 'support_date', default_value=datetime.now().strftime('%d.%m.%Y'),
                                     blur_handler=fix_date).classes('flex-1')

            #di = ui.input(value=datetime.now().strftime('%d.%m.%Y')).props('outlined dense')
            with date_filter.add_slot('append'):
                ui.icon('edit_calendar').classes('cursor-pointer')
                with ui.menu():
                    ui.date().bind_value(date_filter).props('mask="DD.MM.YYYY"')

        generate_btn = ui.button('Сформувати звіт', icon='analytics', on_click=lambda: load_data()).props('color="primary" elevated')
        export_btn = ui.button('В задачу', icon='add_task', on_click=lambda: create_report_task()) \
            .props('color="secondary" outline') \
            .bind_visibility_from(state, 'data', backward=lambda d: len(d) > 0 or len(state['returns']) > 0 or len(state['archive']) > 0)

    table_container = ui.column().classes('w-full max-w-7xl mx-auto shadow-md rounded-lg overflow-hidden border bg-white')

    async def load_data():
        generate_btn.props('loading')
        table_container.clear()
        try:
            target_date = datetime.strptime(date_filter.value, '%d.%m.%Y').date()

            cmd_summary = await run.io_bound(report_ctrl.get_brief_report, ctx)
            state['cmd_summary'] = cmd_summary

            # 1. СЗЧ
            data = await run.io_bound(report_ctrl.get_daily_added_records_report, ctx, target_date)
            state['data'] = data
            data_A0224 = [r for r in data if r.get('sheet_name') == 'А0224']
            data_A7018 = [r for r in data if r.get('sheet_name') == 'А7018']
            added_names = [item['name'] for item in data]

            # 2. ПОВЕРНЕННЯ
            return_data = await run.io_bound(report_ctrl.get_daily_added_files_report, ctx, target_date, added_names)
            state['returns'] = return_data
            returned_names = [item['name'] for item in return_data]

            # 3. АРХІВ (Інші документи)
            all_known_names = added_names + returned_names
            archive_data = await run.io_bound(report_ctrl.get_daily_archive_files, target_date, all_known_names)
            state['archive'] = archive_data

            # ==========================================
            # АНАЛІТИКА (Зведені таблиці ТІЛЬКИ для А0224)
            # ==========================================
            unique_places = sorted(list(set(item.get('desertion_place', 'Не вказано') for item in data_A0224)))
            unique_subunits = sorted(list(set(item.get('subunit', 'Не вказано') for item in data_A0224)))
            rank_categories = ['Офіцери', 'Сержанти', 'Солдати']

            # --- ТАБЛИЦЯ 1: Підрозділ / Звідки СЗЧ ---
            m1_data = {s: {p: 0 for p in unique_places} for s in unique_subunits}
            for item in data_A0224:
                p = item.get('desertion_place', 'Не вказано')
                s = item.get('subunit', 'Не вказано')
                m1_data[s][p] += 1

            state['matrix1_cols'] = [{'name': 'subunit', 'label': 'Підрозділ', 'field': 'subunit', 'align': 'left', 'classes': 'font-bold bg-gray-100'}]
            for p in unique_places:
                state['matrix1_cols'].append({'name': p, 'label': p, 'field': p, 'align': 'center'})
            state['matrix1_cols'].append({'name': 'total', 'label': 'Всього', 'field': 'total', 'align': 'center', 'classes': 'font-bold bg-gray-100'})

            state['matrix1_rows'] = []
            m1_col_totals = {p: 0 for p in unique_places}  # Акумулятор для колонок
            m1_grand_total = 0  # Загальна сума

            for s in unique_subunits:
                row = {'subunit': s}
                total = 0
                for p in unique_places:
                    val = m1_data[s][p]
                    row[p] = val if val > 0 else '-'
                    total += val
                    m1_col_totals[p] += val  # Додаємо до підсумку колонки

                row['total'] = total if total > 0 else '-'
                m1_grand_total += total
                state['matrix1_rows'].append(row)

            # Додаємо фінальний рядок "Підсумок" для Таблиці 1
            m1_summary_row = {'subunit': 'Всього:'}
            for p in unique_places:
                m1_summary_row[p] = m1_col_totals[p] if m1_col_totals[p] > 0 else '-'
            m1_summary_row['total'] = m1_grand_total if m1_grand_total > 0 else '-'
            state['matrix1_rows'].append(m1_summary_row)

            # --- ТАБЛИЦЯ 2: Звідки СЗЧ / Склад ---
            m2_data = {p: {r: 0 for r in rank_categories} for p in unique_places}
            for item in data_A0224:
                p = item.get('desertion_place', 'Не вказано')
                r = get_rank_category(item.get('title'))
                m2_data[p][r] += 1

            state['matrix2_cols'] = [{'name': 'place', 'label': 'Обставини', 'field': 'place', 'align': 'left', 'classes': 'font-bold bg-gray-100'}]
            for r in rank_categories:
                state['matrix2_cols'].append({'name': r, 'label': r, 'field': r, 'align': 'center'})
            state['matrix2_cols'].append({'name': 'total', 'label': 'Всього', 'field': 'total', 'align': 'center', 'classes': 'font-bold bg-gray-100'})

            state['matrix2_rows'] = []
            m2_col_totals = {r: 0 for r in rank_categories}  # Акумулятор для колонок
            m2_grand_total = 0  # Загальна сума

            for p in unique_places:
                row = {'place': p}
                total = 0
                for r in rank_categories:
                    val = m2_data[p][r]
                    row[r] = val if val > 0 else '-'
                    total += val
                    m2_col_totals[r] += val  # Додаємо до підсумку колонки

                row['total'] = total if total > 0 else '-'
                m2_grand_total += total
                state['matrix2_rows'].append(row)

            # Додаємо фінальний рядок "Підсумок" для Таблиці 2
            m2_summary_row = {'place': 'Всього:'}
            for r in rank_categories:
                m2_summary_row[r] = m2_col_totals[r] if m2_col_totals[r] > 0 else '-'
            m2_summary_row['total'] = m2_grand_total if m2_grand_total > 0 else '-'
            state['matrix2_rows'].append(m2_summary_row)

            # --- ТАБЛИЦЯ 3: Досвід ---
            experienced_count = 0
            newcomer_count = 0

            for item in data_A0224:
                # Враховано можливу опечатку в назві поля (experince / experience)
                exp = item.get('experience', item.get('experince', '')).strip().lower()
                if exp == 'experienced':
                    experienced_count += 1
                elif exp == 'newcomer':
                    newcomer_count += 1

            state['exp_summary_rows'] = [
                {'category': 'З бойовим досвідом', 'count': experienced_count},
                {'category': 'Новачки', 'count': newcomer_count},
                {'category': 'Повернень', 'count': len(return_data)}
            ]
            state['exp_summary_cols'] = [
                {'name': 'category', 'label': 'Категорія', 'field': 'category', 'align': 'left', 'classes': 'font-bold'},
                {'name': 'count', 'label': 'Кількість', 'field': 'count', 'align': 'center'}
            ]

            with table_container:

                # ==============================
                # ⭐️ ЗАВДАННЯ ВІД КОМАНДУВАЧА
                # ==============================
                if cmd_summary:
                    cmd_cols = [
                        {'name': 'total_awol', 'label': 'Здійснили СЗЧ', 'field': 'total_awol', 'align': 'center', 'classes': 'text-xl font-bold'},
                        {'name': 'in_search', 'label': 'Знаходяться в розшуку', 'field': 'in_search', 'align': 'center', 'classes': 'text-xl font-bold text-red-600'},
                        {'name': 'returned', 'label': 'Повернулися з СЗЧ', 'field': 'returned', 'align': 'center', 'classes': 'text-xl font-bold text-green-600'},
                        {'name': 'res_returned', 'label': 'Повернулися в БРЕЗ', 'field': 'res_returned', 'align': 'center', 'classes': 'text-xl font-bold text-green-600'},
                        {'name': 'in_disposal', 'label': 'Перебувають в розпорядженні', 'field': 'in_disposal', 'align': 'center', 'classes': 'text-xl font-bold'},
                    ]

                    with ui.row().classes('w-full bg-yellow-50 p-3 border-b items-center justify-between'):
                        ui.label('⭐️ Загальний стан ВЧ А0224').classes('font-bold text-yellow-900 text-lg uppercase tracking-wide')

                    ui.table(columns=cmd_cols, rows=cmd_summary).classes('w-full mb-4').props('flat bordered')

                if not data:
                    ui.label(f'За {date_filter.value} нових записів не знайдено.').classes('text-gray-500 italic text-lg p-6 text-center w-full')
                else:
                    # ==============================
                    # РЕНДЕР АНАЛІТИКИ
                    # ==============================
                    with ui.row().classes('w-full bg-indigo-50 p-3 border-b items-center justify-between'):
                        ui.label('📊 Аналітична довідка за день').classes('font-bold text-indigo-800 text-lg')

                    with ui.column().classes('w-full p-4 gap-4'):

                        with ui.row().classes('w-full gap-6 items-start'):
                            with ui.column().classes('flex-1 min-w-[300px]'):
                                ui.label('Розподіл по підрозділах').classes('font-bold text-gray-700 mb-2')
                                ui.label('Бажаю здоровʼя, за добу станом на 18:00').classes('font-bold text-gray-900 mb-2')
                                ui.table(columns=state['matrix1_cols'], rows=state['matrix1_rows']).classes('w-full analytics-table').props('dense flat bordered')

                            with ui.column().classes('flex-1 min-w-[300px]'):
                                ui.label('Розподіл за складом').classes('font-bold text-gray-700 mb-2')
                                ui.label('Бажаю здоровʼя, за добу станом на 18:00').classes('font-bold text-gray-900 mb-2')
                                ui.table(columns=state['matrix2_cols'], rows=state['matrix2_rows']).classes('w-full analytics-table').props('dense flat bordered')

                        with ui.row().classes('flex-1 mt-2'):
                            ui.table(columns=state['exp_summary_cols'], rows=state['exp_summary_rows']).classes('w-72').props('dense flat bordered hide-header')
                    # ==============================
                    # РЕНДЕР ДЕТАЛЬНИХ СПИСКІВ
                    # ==============================
                    columns = [
                        {'name': 'ins_date', 'label': COLUMN_INSERT_DATE, 'field': 'ins_date', 'align': 'left'},
                        {'name': 'name', 'label': COLUMN_NAME, 'field': 'name', 'align': 'left', 'classes': 'font-bold'},
                        {'name': 'title', 'label': COLUMN_TITLE, 'field': 'title', 'align': 'left'},
                        {'name': 'subunit', 'label': COLUMN_SUBUNIT, 'field': 'subunit', 'align': 'left'},
                        {'name': 'desertion_place', 'label': 'Обставини', 'field': 'desertion_place', 'align': 'left'},
                        {'name': 'des_date', 'label': COLUMN_DESERTION_DATE, 'field': 'des_date', 'align': 'left'},
                    ]

                    if data_A0224:
                        with ui.row().classes('w-full bg-blue-50 p-3 border-b border-t items-center justify-between mt-4'):
                            ui.label(f'ВЧ А0224 | Додано записів: {len(data_A0224)}').classes('font-bold text-blue-800 text-lg')
                        ui.table(columns=columns, rows=data_A0224, row_key='name').classes('w-full').props('flat bordered dense')

                    if data_A7018:
                        with ui.row().classes('w-full bg-green-50 p-3 border-b border-t items-center justify-between mt-4'):
                            ui.label(f'ВЧ А7018 | Додано записів: {len(data_A7018)}').classes('font-bold text-green-800 text-lg')
                        ui.table(columns=columns, rows=data_A7018, row_key='name').classes('w-full').props('flat bordered dense')

                    # ==============================
                    # ПОВЕРНЕННЯ
                    # ==============================
                    with ui.row().classes('w-full bg-teal-50 p-3 border-b border-t items-center justify-between mt-4'):
                        ui.label(f'Повернулися: {len(return_data)}').classes('font-bold text-teal-800 text-lg')

                    if return_data:
                        columns_returns = [
                            {'name': 'ret_date', 'label': 'Дата повернення', 'field': 'ret_date', 'align': 'left', 'classes': 'text-green-700 font-bold'},
                            {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left', 'classes': 'font-bold'},
                            {'name': 'title', 'label': 'Звання', 'field': 'title', 'align': 'left'},
                            {'name': 'subunit', 'label': 'Підрозділ', 'field': 'subunit', 'align': 'left'},
                            {'name': 'des_date', 'label': 'Був в СЗЧ з', 'field': 'des_date', 'align': 'left'},
                        ]
                        ui.table(columns=columns_returns, rows=return_data, row_key='id_number').classes('w-full').props('flat bordered dense')
                    else:
                        ui.label('Записів про повернення не знайдено.').classes('text-gray-500 italic p-4 text-center w-full')

                    # ==============================
                    # АРХІВ (Інші документи)
                    # ==============================
                    with ui.row().classes('w-full bg-gray-100 p-3 border-b border-t items-center justify-between mt-4'):
                        ui.label(f'🗄️ Інші документи (Архів): {len(archive_data)}').classes('font-bold text-gray-800 text-lg')

                    if archive_data:
                        columns_archive = [
                            {'name': 'name', 'label': 'Розпізнане ПІБ', 'field': 'name', 'align': 'left', 'classes': 'font-bold'},
                            {'name': 'filename', 'label': 'Назва файлу', 'field': 'filename', 'align': 'left', 'classes': 'text-gray-600 italic'},
                        ]
                        ui.table(columns=columns_archive, rows=archive_data, row_key='filename').classes('w-full').props('flat bordered dense')
                    else:
                        ui.label('Інших документів за цей день немає.').classes('text-gray-500 italic p-4 text-center w-full')

        except Exception as e:
            ui.notify(f'Помилка формування звіту: {e}', type='negative')
            print(f"Помилка: {e}")
        finally:
            generate_btn.props(remove='loading')

    ui.timer(0.1, load_data, once=True)

    async def create_report_task():
        if not state.get('data') and not state.get('returns'):
            ui.notify('Немає даних для експорту!', type='warning')
            return

        export_btn.props('loading')
        try:
            target_date_str = date_filter.value
            details = f"<h3>📊 Щоденне: {target_date_str}</h3>"

            # 0. ГЕНЕРУЄМО HTML ДЛЯ ТАБЛИЦІ КОМАНДУВАЧА
            cmd_summary = state.get('cmd_summary')
            if cmd_summary:
                row = cmd_summary[0]
                details += "<br><b>⭐️ Загальний стан ВЧ А0224 (Доповідь):</b><br>"
                details += "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse: collapse; text-align: center; width: 100%;'>"
                details += "<tr style='background:#fefce8;'><th>Здійснили СЗЧ</th><th>В розшуку</th><th>Повернулися</th><th>В розпорядженні</th></tr>"
                details += f"<tr><td><b>{row['total_awol']}</b></td><td style='color:red;'><b>{row['in_search']}</b></td><td style='color:green;'><b>{row['returned']}</b></td><td><b>{row['in_disposal']}</b></td></tr>"
                details += "</table><br>"

            # 1. ГЕНЕРУЄМО HTML ДЛЯ ЗВЕДЕНИХ ТАБЛИЦЬ У ТЕКСТ ЗАДАЧІ
            if state.get('matrix1_rows'):
                details += "<br><b>Розподіл по підрозділах:</b><br>"
                details += "<table border='1' cellspacing='0' cellpadding='4' style='border-collapse: collapse;'>"
                # Шапка
                details += "<tr>" + "".join([f"<th style='background:#f3f4f6;'>{c['label']}</th>" for c in state['matrix1_cols']]) + "</tr>"
                # Тіло
                for row in state['matrix1_rows']:
                    details += "<tr>" + "".join([f"<td align='{c.get('align', 'left')}'>{row.get(c['name'], '')}</td>" for c in state['matrix1_cols']]) + "</tr>"
                details += "</table><br>"

                details += "<b>Розподіл за складом:</b><br>"
                details += "<table border='1' cellspacing='0' cellpadding='4' style='border-collapse: collapse;'>"
                details += "<tr>" + "".join([f"<th style='background:#f3f4f6;'>{c['label']}</th>" for c in state['matrix2_cols']]) + "</tr>"
                for row in state['matrix2_rows']:
                    details += "<tr>" + "".join([f"<td align='{c.get('align', 'left')}'>{row.get(c['name'], '')}</td>" for c in state['matrix2_cols']]) + "</tr>"
                details += "</table><br>"

            # 2. ДЕТАЛІЗАЦІЯ ПІШЛИ
            added_data = state.get('data', [])
            if added_data:
                details += "<p><b>⬅️ ДЕТАЛІЗАЦІЯ (ПІШЛИ В СЗЧ):</b></p>"
                data_A0224 = [r for r in added_data if r.get('sheet_name') == 'А0224']
                data_A7018 = [r for r in added_data if r.get('sheet_name') == 'А7018']

                if data_A0224:
                    details += f"<p>👉 <b>ВЧ А0224 ({len(data_A0224)})</b></p><ul>"
                    for r in data_A0224:
                        details += f"<li><b>{r['name']}</b> ({r.get('title', '')}, {r.get('subunit', '')}) — {r.get('desertion_place', '')}</li>"
                    details += "</ul>"

                if data_A7018:
                    details += f"<p>👉 <b>ВЧ А7018 ({len(data_A7018)})</b></p><ul>"
                    for r in data_A7018:
                        details += f"<li><b>{r['name']}</b> ({r.get('title', '')}, {r.get('subunit', '')}) — {r.get('desertion_place', '')}</li>"
                    details += "</ul>"

            # 3. ДЕТАЛІЗАЦІЯ ПОВЕРНУЛИСЯ
            return_data = state.get('returns', [])
            if return_data:
                details += f"<p><b>↪️ ПОВЕРНУЛИСЯ ({len(return_data)}):</b></p><ul>"
                for r in return_data:
                    details += f"<li><b>{r.get('name', '')}</b> ({r.get('title', '')}, {r.get('subunit', '')}) — Був з {r.get('des_date', '')}, повернувся {r.get('ret_date', '')}</li>"
                details += "</ul>"

            # 4. ДЕТАЛІЗАЦІЯ АРХІВУ
            archive_data = state.get('archive', [])
            if archive_data:
                details += f"<p><b>🗄️ ІНШІ ДОКУМЕНТИ В АРХІВІ ({len(archive_data)}):</b></p><ul>"
                for r in archive_data:
                    details += f"<li><b>{r.get('name', 'Невідомо')}</b> (Файл: <i>{r.get('filename', '')}</i>)</li>"
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