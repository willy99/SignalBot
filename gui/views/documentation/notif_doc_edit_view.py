from nicegui import ui, run

from gui.controllers.notif_controller import NotifController
from gui.services.request_context import RequestContext
from gui.controllers.person_controller import PersonController
from domain.person_filter import PersonSearchFilter, YES
from config import UI_DATE_FORMAT, EXCEL_DATE_FORMAT
from datetime import datetime, timedelta
from dics.deserter_xls_dic import COLUMN_TITLE_2, PATTERN_DOC_NUM, COLUMN_INSERT_DATE, REVIEW_STATUS_MAP, \
    REVIEW_STATUS_NON_ERDR, COLUMN_REVIEW_STATUS, COLUMN_DESERTION_DATE, COLUMN_NAME, COLUMN_DESERTION_REGION
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED
from utils.utils import is_valid_doc_number, format_to_excel_date
import re


def render_notif_page(notif_ctrl: NotifController, person_ctrl: PersonController,
                      ctx: RequestContext, notif_doc_id: int = None):

    with ui.row().classes('w-full max-w-7xl mx-auto items-center justify-between mb-6'):
        # Заголовок ліворуч (прибрали w-full та text-center)
        ui.label('Масове повідомлення на КПП').classes('text-3xl font-bold')

        # Група кнопок праворуч
        with ui.row().classes('items-center gap-4'):
            save_draft_btn = ui.button('ЗБЕРЕГТИ ЧЕРНЕТКУ', icon='save').props('outline color="primary"').classes(
                'h-10')
            generate_docs_btn = ui.button('СФОРМУВАТИ (WORD)', icon='description').props('color="blue"').classes('h-10')
            complete_btn = ui.button('ВІДПРАВКА НА КПП', icon='send').props('color="green"').classes('h-10')

    ui_options = person_ctrl.get_column_options()
    title_options = ui_options.get(COLUMN_TITLE_2, [])
    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])
    title_dict = {t: t for t in title_options if t}
    desertion_region_options = person_ctrl.get_column_options().get(COLUMN_DESERTION_REGION)

    # Головний стейт сторінки
    state = {
        'status': DOC_STATUS_DRAFT,
        'out_date': None,
        'out_number': '',
        'buffer': [],
        'notif_doc_id': notif_doc_id,

        # Стейт для фільтрів пошуку
        'filter_year': '',
        'filter_date_from': '',
        'filter_date_to': '',
        'filter_title': None,
        'filter_des_region': None,

        # Стейт для результатів пошуку
        'search_results': [],
        'selected_candidates': set()  # Множина id_number вибраних людей
    }

    with ui.grid(columns=12).classes('w-full gap-6 items-start max-w-7xl mx-auto'):

        # ==========================================
        # ЛІВА ЧАСТИНА: ФІЛЬТРИ ТА СПИСОК КАНДИДАТІВ
        # ==========================================
        with ui.card().classes('col-span-12 md:col-span-8 w-full shadow-md p-6'):

            # --- 1. Шапка документа (статус, номер, дата) ---
            status_text = state.get('status', DOC_STATUS_DRAFT)
            badge_color = 'green' if status_text == DOC_STATUS_COMPLETED else 'grey'

            with ui.row().classes('w-full items-center gap-5 mb-6 pb-4 border-b border-gray-100'):
                with ui.row().classes('items-center gap-3'):
                    ui.label('Статус:').classes('text-gray-500 font-medium')
                    status_badge = ui.badge(status_text, color=badge_color).classes('text-sm px-2 py-1')

                out_number_input = ui.input('Вихідний номер на КПП', placeholder='Наприклад: 642/123', validation={
                    'Формат має бути 642/ХХХХ': lambda v: bool(re.match(PATTERN_DOC_NUM, v.strip())) if v else True
                }).bind_value(state, 'out_number').classes('flex-1').props('hide-bottom-space')

                out_date_input = date_input(
                    'Дата відправки', state, 'out_date', blur_handler=fix_date
                ).classes('flex-1')

                des_region_input = ui.select(desertion_region_options, label=COLUMN_DESERTION_REGION).bind_value(state, 'filter_des_region').props('clearable').classes('w-32')

            # --- 2. Блок фільтрів ---
            ui.label('Пошук військовослужбовців без КПП').classes('text-lg font-bold text-gray-700 mb-2')

            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.select(year_options, label='Рік СЗЧ').bind_value(state, 'filter_year').props('clearable').classes('w-32')
                date_input('З дати', state, 'filter_date_from', fix_date).classes('flex-1').props('clearable')
                date_input('По дату', state, 'filter_date_to', fix_date).classes('flex-1').props('clearable')
                ui.select(title_dict, label='Військове звання').bind_value(state, 'filter_title').props(
                    'clearable').classes('flex-1')

            search_btn = ui.button('Знайти кандидатів', icon='person_search').classes('w-full mb-4').props(
                'elevated color="primary"')

            # Контейнер кнопок масового додавання
            actions_row = ui.row().classes('w-full justify-between items-center mt-2 transition-all')
            actions_row.set_visibility(False)

            actions_row = ui.row().classes('w-full justify-between items-center mb-2 transition-all')
            actions_row.set_visibility(False)
            with actions_row:
                selected_count_label = ui.label('Вибрано: 0').classes('font-bold text-blue-600')
                add_selected_btn = ui.button('Додати вибраних до списку', icon='arrow_forward').props(
                    'color="secondary"')

            # --- Контейнер для списку результатів ---
            search_results_container = ui.column().classes(
                'w-full gap-2 p-4 bg-gray-50 rounded-md border border-gray-200 max-h-[400px] overflow-y-auto')

            # --- Логіка пошуку ---
            async def perform_search():
                search_btn.disable()
                search_results_container.clear()
                state['search_results'].clear()
                state['selected_candidates'].clear()
                update_selection_ui()

                with search_results_container:
                    ui.spinner('dots', size='lg', color='primary').classes('mx-auto my-4')

                try:
                    # Формуємо фільтр
                    year_val = state.get('filter_year')
                    year_val = str(year_val).strip() if year_val else ''
                    des_region_val = state.get('filter_des_region')

                    now = datetime.now()
                    minus_4_days = (now - timedelta(days=4)).strftime(EXCEL_DATE_FORMAT)

                    filter_obj = PersonSearchFilter(
                        des_year=[year_val] if year_val else [],
                        des_date_from=state['filter_date_from'],
                        des_date_to=state['filter_date_to'] if state['filter_date_to'] else minus_4_days,
                        title2=state['filter_title'],
                        review_statuses=REVIEW_STATUS_MAP[REVIEW_STATUS_NON_ERDR],
                        empty_kpp=YES,  # Шукаємо тільки тих, у кого немає повідомлення на КПП
                        desertion_region=des_region_val
                    )

                    results = await run.io_bound(person_ctrl.search, ctx, filter_obj)
                    if results and len(results) > 50:
                        ui.notify(f'Знайдено {len(results)} осіб. Показано перші 50.', type='warning')
                        results = results[:50]

                    search_results_container.clear()

                    if not results:
                        with search_results_container:
                            ui.label('Кандидатів не знайдено. Змініть параметри пошуку.').classes(
                                'text-gray-500 italic text-center w-full py-4')
                        return

                    # Зберігаємо результати
                    state['search_results'] = results

                    with search_results_container:
                        # Заголовок таблиці
                        with ui.row().classes(
                                'w-full items-center justify-between border-b border-gray-300 pb-2 mb-2 font-bold text-sm text-gray-600'):
                            with ui.row().classes('items-center gap-2 w-3/4'):
                                def toggle_all(e):
                                    state['selected_candidates'].clear()
                                    if e.value:
                                        for p in state['search_results']:
                                            id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}"
                                            state['selected_candidates'].add(id_num)
                                    # Оновлюємо UI чекбоксів (це тригерне їх on_change автоматично)
                                    for cb in candidate_checkboxes.values():
                                        cb.value = e.value
                                    update_selection_ui()

                                ui.checkbox(on_change=toggle_all)
                                ui.label(COLUMN_NAME).classes('w-1/2')
                                ui.label(COLUMN_TITLE_2).classes('w-1/4')
                                ui.label(COLUMN_DESERTION_DATE).classes('w-1/4')
                                ui.label(COLUMN_REVIEW_STATUS).classes('w-1/4')

                        # Список знайдених
                        candidate_checkboxes = {}

                        def on_check(e, id_num):
                            if e.value:
                                state['selected_candidates'].add(id_num)
                            else:
                                state['selected_candidates'].discard(id_num)
                            update_selection_ui()

                        for p in results:
                            id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}"
                            # Перевіряємо, чи ця людина вже є в буфері праворуч
                            is_in_buffer = any(doc['id_number'] == id_num for doc in state['buffer'])

                            row_class = 'w-full items-center justify-between py-1 border-b border-gray-100 hover:bg-gray-100'
                            if is_in_buffer:
                                row_class += ' opacity-50 bg-gray-50'

                            with ui.row().classes(row_class):
                                with ui.row().classes('items-center gap-2 w-3/4'):
                                    cb = ui.checkbox(on_change=lambda e, idx=id_num: on_check(e, idx))
                                    if is_in_buffer:
                                        cb.disable()
                                        cb.tooltip('Вже додано до чернетки праворуч')
                                    candidate_checkboxes[id_num] = cb

                                    with ui.column().classes('gap-0 w-1/2'):
                                        ui.label(p.name).classes('font-bold text-sm')
                                        ui.label(str(p.rnokpp)).classes('text-xs text-gray-500')

                                    ui.label(getattr(p, 'title', '')).classes('w-1/4 text-sm')
                                    ui.label(format_to_excel_date(p.desertion_date)).classes(
                                        'w-1/4 text-sm text-red-600')
                                    ui.label(getattr(p, 'review_status', '')).classes('w-1/4 text-sm')

                    ui.notify(f'Знайдено {len(results)} кандидатів', type='info')

                except Exception as ex:
                    ui.notify(f'Помилка пошуку: {ex}', type='negative')
                finally:
                    search_btn.enable()

            search_btn.on('click', perform_search)

            def update_selection_ui():
                count = len(state['selected_candidates'])
                selected_count_label.set_text(f'Вибрано: {count}')
                actions_row.set_visibility(count > 0)

            # --- Додавання до буфера (Масове) ---
            def on_add_selected_click():
                if not state['selected_candidates']:
                    return

                buffer_data = state['buffer']
                added_count = 0

                # Знаходимо моделі вибраних людей
                for p in state['search_results']:
                    id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}"

                    if id_num in state['selected_candidates']:
                        # Перевіряємо, чи немає його вже в буфері
                        if not any(doc['id_number'] == id_num for doc in buffer_data):
                            raw_data = {
                                'id_number': id_num,
                                'rnokpp': p.rnokpp,
                                'name': p.name,
                                'title': getattr(p, 'title', ''),
                                'review_status': getattr(p, 'review_status', ''),
                                'desertion_date': format_to_excel_date(p.desertion_date),
                                'birthday': format_to_excel_date(getattr(p, 'birthday', '')),
                                'desertion_conditions': getattr(p, 'desertion_conditions', ''),
                                'desertion_region': getattr(p, 'desertion_region', state.get('filter_des_region'))
                            }
                            buffer_data.append(raw_data)
                            added_count += 1

                # Скидаємо виділення
                state['selected_candidates'].clear()

                # Оновлюємо інтерфейс пошуку (щоб задизейблити чекбокси доданих)
                # Найпростіше - просто перемалювати список результатів
                ui.timer(0.1, perform_search, once=True)

                refresh_buffer_ui()
                ui.notify(f'Додано {added_count} осіб до чернетки!', type='positive')

            add_selected_btn.on('click', on_add_selected_click)

        # ==========================================
        # ПРАВА ЧАСТИНА: БУФЕР ТА ДІЇ
        # ==========================================
        with ui.column().classes('col-span-12 md:col-span-4 w-full') as right_panel:
            ui.label('Список на відправку (КПП):').classes('text-xl font-bold')
            buffer_container = ui.column().classes(
                'w-full gap-2 p-4 border rounded-lg bg-gray-50 min-h-[300px] shadow-inner')

            async def on_remove_click(idx):
                with right_panel:
                    dialog = ui.dialog()
                    with dialog, ui.card().classes('p-6 min-w-[300px]'):
                        ui.label('Підтвердження').classes('text-xl font-bold text-red-600 mb-2')
                        ui.label('Видалити особу зі списку чернетки?').classes('text-gray-600 mb-6')
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                            ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

                if await dialog:
                    if 0 <= idx < len(state['buffer']):
                        state['buffer'].pop(idx)
                    await perform_search()
                    refresh_buffer_ui()

            def refresh_buffer_ui():
                buffer_data = state['buffer']

                # 1. БЕЗПЕЧНА ЗОНА: Оновлюємо стан комбобокса ДО очищення контейнера
                if buffer_data:
                    des_region_input.disable()
                else:
                    des_region_input.enable()

                # 2. Очищуємо контейнер
                buffer_container.clear()

                with buffer_container:
                    if not buffer_data:
                        ui.label('Чернетка порожня. Знайдіть та додайте осіб ліворуч.').classes(
                            'text-gray-400 italic text-center w-full mt-10')
                    else:
                        ui.label(f'Всього у чернетці: {len(buffer_data)}').classes(
                            'text-sm font-bold text-blue-600 mb-2')
                        for i, p in enumerate(buffer_data):
                            with ui.row().classes(
                                    'w-full justify-between items-center bg-white p-2 border rounded shadow-sm hover:bg-gray-100 transition-colors'):
                                with ui.column().classes('gap-0 w-3/4'):
                                    ui.label(f"{i + 1}. {p['name']}").classes('font-bold text-sm truncate w-full')
                                    info_str = f"РНОКПП: {p.get('rnokpp', '—')} | СЗЧ: {p.get('desertion_date', '—')}"
                                    ui.label(info_str).classes('text-xs text-gray-500')

                                with ui.row().classes('gap-1'):
                                    delete_button = ui.button(icon='close', color='red',
                                                              on_click=lambda idx=i: on_remove_click(idx)).props(
                                        'flat dense size=sm')

                                    if state['status'] == DOC_STATUS_COMPLETED:
                                        delete_button.disable()

                save_draft_btn.set_visibility(len(buffer_data) > 0)
                generate_docs_btn.set_visibility(len(buffer_data) > 0)
                complete_btn.set_visibility(len(buffer_data) > 0)

            # --- Збереження та відправка ---
            async def on_save_draft_click():
                save_draft_btn.disable()
                try:
                    notif_doc_id = await run.io_bound(
                        notif_ctrl.save_doc,
                        ctx,
                        state['out_number'],
                        state['out_date'],
                        state['buffer'],
                        state['notif_doc_id']
                    )
                    state['notif_doc_id'] = notif_doc_id
                    ui.notify(f'Чернетку збережено!', type='positive', icon='cloud_done')
                except Exception as e:
                    ui.notify(f'Помилка БД: {e}', type='negative')
                finally:
                    save_draft_btn.enable()

            async def on_generate_docs_click():
                out_num = out_number_input.value.strip()
                region = des_region_input.value.strip()
                if not out_num or not state['out_date']:
                    ui.notify('Заповніть дату та номер на КПП!', type='warning')
                    return
                if not is_valid_doc_number(out_num):
                    ui.notify('❌ Формат номера має бути 642/ХХХХ', type='negative')
                    return

                await on_save_draft_click()

                generate_docs_btn.props('loading')
                ui.notify('⏳ Генеруємо повідомлення...', type='info')
                try:
                    file_bytes, file_name = await run.io_bound(
                        notif_ctrl.generate_document,
                        ctx,
                        region,
                        out_num,
                        state['out_date'],
                        state['buffer']
                    )
                    ui.download(file_bytes, file_name)
                    ui.notify('✅ Документ успішно згенеровано!', type='positive')
                except Exception as e:
                    ui.notify(f'❌ Помилка генерації: {e}', type='negative')
                finally:
                    generate_docs_btn.props(remove='loading')

            async def on_send_kpp_click():
                out_num = out_number_input.value.strip()
                if not is_valid_doc_number(out_num):
                    ui.notify('❌ Невірний формат вихідного номера!', type='negative')
                    return
                await on_save_draft_click()

                complete_btn.disable()
                complete_btn.props('loading')
                ui.notify('⏳ Оновлюємо дані в Excel, зачекайте...', type='info')

                try:
                    success = await run.io_bound(
                        notif_ctrl.mark_as_completed,
                        ctx,
                        state['notif_doc_id'],
                        state['buffer'],
                        state['out_number'],
                        state['out_date'],
                        person_ctrl
                    )

                    if success:
                        state['status'] = DOC_STATUS_COMPLETED
                        refresh_status_ui()
                        ui.notify(f'✅ Справи успішно відправлені на КПП!', type='positive')
                    else:
                        ui.notify(f'⚠️ Виникла помилка під час відправки', type='negative')
                except Exception as e:
                    ui.notify(f'❌ Помилка під час відправки: {e}', type='negative')
                finally:
                    complete_btn.props(remove='loading')
                    if state.get('status') != DOC_STATUS_COMPLETED:
                        complete_btn.enable()

            save_draft_btn.on('click', on_save_draft_click)
            generate_docs_btn.on('click', on_generate_docs_click)
            complete_btn.on('click', on_send_kpp_click)

            def refresh_status_ui():
                current_status = state.get('status', DOC_STATUS_DRAFT)
                status_badge.set_text(current_status)

                if current_status == DOC_STATUS_COMPLETED:
                    status_badge.props('color="green"')
                    complete_btn.disable()
                    save_draft_btn.disable()
                    generate_docs_btn.disable()
                else:
                    status_badge.props('color="grey"')
                    complete_btn.enable()
                    save_draft_btn.enable()
                    generate_docs_btn.enable()

            def load_draft(d_id: int):
                try:
                    draft = notif_ctrl.get_doc_by_id(ctx, d_id)
                    if draft:
                        state['out_number'] = draft.get('out_number', '')
                        state['out_date'] = draft.get('out_date', '')
                        state['buffer'] = draft.get('payload', [])
                        state['status'] = draft.get('status', DOC_STATUS_DRAFT)
                        if state['buffer']:
                            first_person_region = state['buffer'][0].get('desertion_region', '')
                            state['filter_des_region'] = first_person_region

                        refresh_status_ui()
                        ui.notify(f'Чернетку завантажено', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка завантаження: {e}', type='negative')

            if notif_doc_id is not None:
                load_draft(notif_doc_id)

            refresh_buffer_ui()


def date_input(label: str, state, field: str, blur_handler=None):
    inp = ui.input(label=label).bind_value(state, field)
    if blur_handler:
        inp.on('blur', blur_handler)
    with inp.add_slot('append'):
        ui.icon('edit_calendar').classes('cursor-pointer')
        with ui.menu():
            ui.date().bind_value(state, field).props(f'mask="{UI_DATE_FORMAT}"')
    return inp


def fix_date(e):
    val = e.sender.value
    if not val: return
    parts = val.split('.')
    if len(parts) == 2:
        e.sender.value = f"{val}.{datetime.now().year}"