from nicegui import ui, run
from gui.controllers.notif_controller import NotifController
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from gui.controllers.person_controller import PersonController
from domain.person_filter import PersonSearchFilter, YES
from datetime import datetime, timedelta
from dics.deserter_xls_dic import *
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED, DB_DATE_FORMAT
from utils.utils import format_to_excel_date
from gui.tools.validation import is_valid_doc_number
import re
from gui.tools.ui_components import date_input, fix_date, mark_clean, mark_dirty, confirm_delete_dialog


def render_notif_page(notif_ctrl: NotifController, person_ctrl: PersonController,
                      auth_manager: AuthManager, notif_doc_id: int = None):
    state = {
        'status': DOC_STATUS_DRAFT,
        'out_date': None,
        'out_number': '',
        'region': '',
        'buffer': [],
        'notif_doc_id': notif_doc_id,
        'filter_year': '',
        'filter_date_from': '',
        'filter_date_to': '',
        'filter_title': None,
        'filter_des_region': None,
        'search_results': [],
        'selected_candidates': set(),
        'dragged_idx': None
    }

    async def on_save_draft_click():
        has_error = await validate_out_number()
        if has_error:
            ui.notify('Виправте помилки перед збереженням!', type='negative')
            return

        save_draft_btn.disable()
        mark_clean()
        current_out_num = state.get('out_number', '').strip()
        current_out_date = state.get('out_date', '')
        current_region = state.get('filter_des_region', '')

        for doc in state['buffer']:
            doc['kpp_num'] = current_out_num
            doc['kpp_date'] = current_out_date
        try:
            notif_doc_id = await auth_manager.execute(
                notif_ctrl.save_doc,
                auth_manager.get_current_context(),
                current_region,
                current_out_num,
                current_out_date,
                state['buffer'],
                state['notif_doc_id']
            )
            state['notif_doc_id'] = notif_doc_id
            ui.notify('Чернетку збережено!', type='positive', icon='cloud_done')
        except Exception as e:
            ui.notify(f'Помилка БД: {e}', type='negative')
        finally:
            save_draft_btn.enable()

    async def on_generate_docs_click():
        out_num = state.get('out_number', '').strip()
        region = state.get('filter_des_region', '')

        if not out_num or not state['out_date']:
            ui.notify('Заповніть дату та номер на КПП!', type='warning')
            return
        if not is_valid_doc_number(out_num):
            ui.notify('❌ Формат номера має бути 642/ХХХХX', type='negative')
            return

        await on_save_draft_click()

        generate_docs_btn.props('loading')
        ui.notify('⏳ Генеруємо повідомлення...', type='info')
        try:
            file_bytes, file_name = await auth_manager.execute(notif_ctrl.generate_document, auth_manager.get_current_context(), region, out_num, state['out_date'], state['buffer'])
            ui.download(file_bytes, file_name)
            ui.notify('✅ Документ успішно згенеровано!', type='positive')
        except Exception as e:
            ui.notify(f'❌ Помилка генерації: {e}', type='negative')
        finally:
            generate_docs_btn.props(remove='loading')

    async def on_generate_indiv_docs_click():
        out_num = state.get('out_number', '').strip()
        region = state.get('filter_des_region', '')

        if not out_num or not state['out_date']:
            ui.notify('Заповніть дату та номер на КПП!', type='warning')
            return
        if not is_valid_doc_number(out_num):
            ui.notify('❌ Формат номера має бути 642/ХХХХ', type='negative')
            return

        await on_save_draft_click()

        generate_indiv_docs_btn.props('loading')
        ui.notify('⏳ Формуємо архів з документами...', type='info')
        try:
            file_bytes, file_name = await auth_manager.execute(notif_ctrl.generate_individual_documents, auth_manager.get_current_context(), region, out_num, state['out_date'], state['buffer'])
            ui.download(file_bytes, file_name)
            ui.notify('✅ Архів успішно згенеровано!', type='positive')
        except Exception as e:
            ui.notify(f'❌ Помилка генерації: {e}', type='negative')
        finally:
            generate_indiv_docs_btn.props(remove='loading')

    async def on_send_kpp_click():
        out_num = state.get('out_number', '').strip()
        if not is_valid_doc_number(out_num):
            ui.notify('❌ Невірний формат вихідного номера!', type='negative')
            return

        await on_save_draft_click()

        complete_btn.disable()
        complete_btn.props('loading')
        ui.notify('⏳ Оновлюємо дані в Excel, зачекайте...', type='info')

        try:
            success = await auth_manager.execute(notif_ctrl.mark_as_completed, auth_manager.get_current_context(), state['notif_doc_id'], state['buffer'], state['out_number'], state['out_date'], person_ctrl)
            if success:
                state['status'] = DOC_STATUS_COMPLETED
                refresh_status_ui()
                ui.notify('✅ Справи успішно помічені, як відправлені!', type='positive')
            else:
                ui.notify('⚠️ Виникла помилка під час відправки', type='negative')
        except Exception as e:
            ui.notify(f'❌ Помилка під час відправки: {e}', type='negative')
        finally:
            complete_btn.props(remove='loading')
            if state.get('status') != DOC_STATUS_COMPLETED:
                complete_btn.enable()

    with ui.row().classes('w-full px-4 items-center justify-between mb-6'):
        ui.label('Масова відправка повідомлень').classes('text-3xl font-bold')

        with ui.row().classes('items-center gap-4'):
            save_draft_btn = ui.button('ЗБЕРЕГТИ ЧЕРНЕТКУ', icon='save', on_click=on_save_draft_click).props('outline color="primary"').classes('h-10')
            save_draft_btn.disable()

            generate_docs_btn = ui.button('WORD: Разом', icon='description', on_click=on_generate_docs_click).props('color="blue"').classes('h-10')
            generate_docs_btn.disable()

            generate_indiv_docs_btn = ui.button('WORD (Окремо)', icon='file_copy', on_click=on_generate_indiv_docs_click).props('color="blue"').classes('h-10')
            generate_indiv_docs_btn.disable()

            complete_btn = ui.button('ВІДПРАВКА', icon='send', on_click=on_send_kpp_click).props('color="green"').classes('h-10')
            complete_btn.disable()

    ui_options = person_ctrl.get_column_options()
    title_options = ui_options.get(COLUMN_TITLE_2, [])
    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])
    title_dict = {t: t for t in title_options if t}
    desertion_region_options = person_ctrl.get_column_options().get(COLUMN_DESERTION_REGION)

    with ui.grid(columns=12).classes('w-full px-4 gap-6 items-start'):

        with ui.card().classes('col-span-12 md:col-span-8 w-full shadow-md p-6'):

            status_text = state.get('status', DOC_STATUS_DRAFT)
            badge_color = 'green' if status_text == DOC_STATUS_COMPLETED else 'grey'

            with ui.row().classes('w-full items-center gap-5 mb-6 pb-4 border-b border-gray-100'):
                with ui.row().classes('items-center gap-3'):
                    ui.label('Статус:').classes('text-gray-500 font-medium')
                    status_badge = ui.badge(status_text, color=badge_color).classes('text-sm px-2 py-1')

                out_number_input = ui.input('Вихідний номер на КПП', placeholder='Наприклад: 642/123').bind_value(state, 'out_number').classes('flex-1').props('hide-bottom-space')

                async def validate_out_number(e=None):
                    num = state.get('out_number', '').strip()
                    out_number_input.props(remove='error error-message')
                    if not num:
                        return False

                    if not re.match(VALID_PATTERN_DOC_NUM, num):
                        out_number_input.props('error error-message="Формат має бути 642/ХХХХX (до 5 цифр)"')
                        return True
                    is_dup = await auth_manager.execute(notif_ctrl.is_existing_num, auth_manager.get_current_context(), num, state.get('notif_doc_id'))

                    if is_dup:
                        out_number_input.props('error error-message="Цей номер вже існує в базі!"')
                        ui.notify(f'Увага! Номер {num} вже зайнятий.', type='warning')
                        return True
                    return False

                out_number_input.on('blur', validate_out_number)

                out_date_input = date_input(
                    'Дата відправки', state, 'out_date', blur_handler=fix_date
                ).classes('flex-1')

                des_region_input = ui.select(desertion_region_options, label=COLUMN_DESERTION_REGION).bind_value(state, 'filter_des_region').props('clearable').classes('w-32')

            ui.label('Пошук військовослужбовців без КПП').classes('text-lg font-bold text-gray-700 mb-2')

            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.select(year_options, label='Рік СЗЧ').bind_value(state, 'filter_year').props('clearable').classes('w-32')
                date_input('З дати', state, 'filter_date_from', fix_date).classes('flex-1').props('clearable')
                date_input('По дату', state, 'filter_date_to', fix_date).classes('flex-1').props('clearable')
                ui.select(title_dict, label='Військове звання').bind_value(state, 'filter_title').props('clearable').classes('flex-1')

            search_btn = ui.button('Знайти кандидатів', icon='person_search').classes('w-full mb-4').props('elevated color="primary"')

            actions_row = ui.row().classes('w-full justify-between items-center mb-2 transition-all')
            actions_row.set_visibility(False)
            with actions_row:
                selected_count_label = ui.label('Вибрано: 0').classes('font-bold text-blue-600')
                add_selected_btn = ui.button('Додати вибраних до списку', icon='arrow_forward').props('color="secondary"')

            search_results_container = ui.column().classes('w-full gap-2 p-4 bg-gray-50 rounded-md border border-gray-200 max-h-[400px] overflow-y-auto')

            async def perform_search():
                des_region_val = state.get('filter_des_region')
                if not des_region_val:
                    ui.notify('❌ Обов\'язково оберіть регіон СЗЧ перед пошуком!', type='warning')
                    return

                search_btn.disable()
                search_results_container.clear()
                state['search_results'].clear()
                state['selected_candidates'].clear()
                update_selection_ui()

                with search_results_container:
                    ui.spinner('dots', size='lg', color='primary').classes('mx-auto my-4')

                try:
                    year_val = state.get('filter_year')
                    year_val = str(year_val).strip() if year_val else ''

                    def to_iso(date_str):
                        if not date_str: return None
                        try:
                            return datetime.strptime(date_str, '%d.%m.%Y').strftime(DB_DATE_FORMAT)
                        except ValueError:
                            return date_str

                    now = datetime.now()
                    minus_4_days_iso = (now - timedelta(days=4)).strftime(DB_DATE_FORMAT)

                    date_from_iso = to_iso(state['filter_date_from'])
                    date_to_iso = to_iso(state['filter_date_to']) if state['filter_date_to'] else minus_4_days_iso

                    filter_obj = PersonSearchFilter(
                        des_year=[year_val] if year_val else [],
                        des_date_from=date_from_iso,
                        des_date_to=date_to_iso,
                        title2=state['filter_title'],
                        review_statuses=REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_ERDR],
                        empty_kpp=YES,
                        desertion_region=des_region_val,
                        include_402=False
                    )

                    results = await auth_manager.execute(person_ctrl.search, auth_manager.get_current_context(), filter_obj)
                    if results and len(results) > 50:
                        ui.notify(f'Знайдено {len(results)} осіб. Показано перші 50.', type='warning')
                        results = results[:50]

                    search_results_container.clear()

                    if not results:
                        with search_results_container:
                            ui.label('Кандидатів не знайдено. Змініть параметри пошуку.').classes('text-gray-500 italic text-center w-full py-4')
                        return

                    state['search_results'] = results

                    with search_results_container:
                        with ui.row().classes('w-full items-center border-b border-gray-300 pb-2 mb-2 font-bold text-sm text-gray-600 flex-nowrap gap-2'):
                            def toggle_all(e):
                                state['selected_candidates'].clear()
                                if e.value:
                                    for p in state['search_results']:
                                        id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}_{p.mil_unit}"
                                        state['selected_candidates'].add(id_num)
                                for cb in candidate_checkboxes.values():
                                    cb.value = e.value
                                update_selection_ui()

                            ui.checkbox(on_change=toggle_all)
                            ui.label(COLUMN_NAME).classes('flex-1')
                            ui.label(COLUMN_TITLE_2).classes('w-32 shrink-0')
                            ui.label(COLUMN_DESERTION_DATE).classes('w-24 shrink-0 text-center')
                            ui.label(COLUMN_REVIEW_STATUS).classes('w-24 shrink-0 text-center')

                        candidate_checkboxes = {}

                        def on_check(e, id_num):
                            if e.value:
                                state['selected_candidates'].add(id_num)
                            else:
                                state['selected_candidates'].discard(id_num)
                            update_selection_ui()

                        for p in results:
                            id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}_{p.mil_unit}"
                            is_in_buffer = any(doc['id_number'] == id_num for doc in state['buffer'])
                            mil_unit_val = getattr(p, 'mil_unit', '')

                            row_class = 'w-full items-center py-1 border-b border-gray-100 hover:bg-gray-100 flex-nowrap gap-2'
                            if is_in_buffer:
                                row_class += ' opacity-50 bg-gray-50'

                            with ui.row().classes(row_class):
                                with ui.row().classes('items-center gap-2 w-3/4'):
                                    cb = ui.checkbox(on_change=lambda e, idx=id_num: on_check(e, idx))
                                    if is_in_buffer:
                                        cb.disable()
                                        cb.tooltip('Вже додано до чернетки праворуч')
                                    candidate_checkboxes[id_num] = cb

                                    with ui.column().classes('gap-0 flex-1 overflow-hidden'):
                                        with ui.row().classes('items-center gap-1'):
                                            ui.label(p.name).classes('font-bold text-sm truncate')
                                            if mil_unit_val == 'А7018':
                                                ui.badge('БРЕЗ', color='orange').classes('text-[10px] px-1 py-0')
                                        ui.label(str(p.rnokpp)).classes('text-xs text-gray-500 truncate w-full')

                                    ui.label(getattr(p, 'title', '')).classes('w-32 shrink-0 text-sm truncate')
                                    ui.label(format_to_excel_date(p.desertion_date)).classes('w-24 shrink-0 text-sm text-red-600 text-center')
                                    ui.label(getattr(p, 'review_status', '')).classes('w-24 shrink-0 text-sm text-center truncate')

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

            def on_add_selected_click():
                if not state['selected_candidates']:
                    return

                buffer_data = state['buffer']
                added_count = 0

                for p in state['search_results']:
                    id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}_{p.mil_unit}"

                    if id_num in state['selected_candidates']:
                        if not any(doc['id_number'] == id_num for doc in buffer_data):
                            raw_data = {
                                'id_number': id_num,
                                'seq_num': 0,
                                'rnokpp': p.rnokpp,
                                'name': p.name,
                                'title': getattr(p, 'title', ''),
                                'review_status': getattr(p, 'review_status', ''),
                                'mil_unit': getattr(p, 'mil_unit', ''),
                                'desertion_date': format_to_excel_date(p.desertion_date),
                                'birthday': format_to_excel_date(getattr(p, 'birthday', '')),
                                'desertion_conditions': getattr(p, 'desertion_conditions', ''),
                                'desertion_region': getattr(p, 'desertion_region', state.get('filter_des_region')),
                                'kpp_num': state.get('out_number', ''),
                                'kpp_date': state.get('out_date', '')
                            }
                            buffer_data.append(raw_data)
                            added_count += 1

                if added_count > 0:
                    mark_dirty()

                state['selected_candidates'].clear()
                ui.timer(0.1, perform_search, once=True)
                refresh_buffer_ui()
                ui.notify(f'Додано {added_count} осіб до чернетки!', type='positive')

            add_selected_btn.on('click', on_add_selected_click)

        with ui.column().classes('col-span-12 md:col-span-4 w-full') as right_panel:
            ui.label('Список на відправку (КПП):').classes('text-xl font-bold')
            buffer_container = ui.column().classes('w-full gap-2 p-4 border rounded-lg bg-gray-50 min-h-[300px] shadow-inner')

            async def on_remove_click(idx):
                with right_panel:
                    result = await confirm_delete_dialog('Видалити особу зі списку чернетки?')
                if result:
                    if 0 <= idx < len(state['buffer']):
                        state['buffer'].pop(idx)
                    await perform_search()
                    mark_dirty()
                    refresh_buffer_ui()

            def refresh_buffer_ui():
                buffer_data = state['buffer']
                for index, doc in enumerate(buffer_data):
                    doc['seq_num'] = index + 1

                if buffer_data:
                    des_region_input.disable()
                else:
                    des_region_input.enable()

                buffer_container.clear()

                def handle_dragstart(idx):
                    state['dragged_idx'] = idx

                def handle_drop(target_idx):
                    dragged_idx = state.get('dragged_idx')
                    # Якщо ми кидаємо елемент на інше місце
                    if dragged_idx is not None and dragged_idx != target_idx:
                        # Витягуємо елемент зі старого місця
                        item = state['buffer'].pop(dragged_idx)
                        # Вставляємо на нове місце
                        state['buffer'].insert(target_idx, item)
                        state['dragged_idx'] = None

                        mark_dirty()
                        refresh_buffer_ui()  # Перемальовуємо список (seq_num оновляться самі)

                with buffer_container:
                    if not buffer_data:
                        ui.label('Чернетка порожня. Знайдіть та додайте осіб ліворуч.').classes('text-gray-400 italic text-center w-full mt-10')
                    else:
                        ui.label(f'Всього у чернетці: {len(buffer_data)}').classes('text-sm font-bold text-blue-600 mb-2')
                        for i, p in enumerate(buffer_data):
                            is_completed = state['status'] == DOC_STATUS_COMPLETED
                            # Налаштовуємо стилі рядка. Додаємо cursor-move, якщо можна тягати
                            row_classes = 'w-full justify-between items-center bg-white p-2 border rounded shadow-sm hover:bg-gray-100 transition-colors'
                            if not is_completed:
                                row_classes += ' cursor-move'

                            # Створюємо сам рядок
                            item_row = ui.row().classes(row_classes)

                            # 💡 ВАЖЛИВО: Вішаємо події перетягування
                            if not is_completed:
                                item_row.props('draggable="true"')
                                item_row.on('dragstart', lambda e, idx=i: handle_dragstart(idx))
                                # dragover.prevent - це команда браузеру "сюди МОЖНА кидати об'єкти"
                                item_row.on('dragover.prevent', lambda e: None)
                                item_row.on('drop', lambda e, idx=i: handle_drop(idx))

                            with item_row:
                                with ui.column().classes('gap-0 w-3/4 pointer-events-none'):
                                    # pointer-events-none запобігає перехопленню drag-подій внутрішніми текстами
                                    ui.label(f"{p['seq_num']}. {p['name']}").classes('font-bold text-sm truncate w-full')
                                    info_str = f"РНОКПП: {p.get('rnokpp', '—')} | СЗЧ: {p.get('desertion_date', '—')}"
                                    ui.label(info_str).classes('text-xs text-gray-500')

                                    with ui.row().classes('gap-1 mt-1'):
                                        if p.get('review_status') == 'ЄРДР':
                                            ui.badge('ЄРДР', color='red').classes('text-[10px] px-1 py-0 w-min')
                                        if p.get('mil_unit') == 'А7018':
                                            ui.badge('БРЕЗ', color='orange').classes('text-[10px] px-1 py-0 w-min')

                                with ui.row().classes('gap-1'):
                                    delete_button = ui.button(icon='close', color='red', on_click=lambda idx=i: on_remove_click(idx)).props('flat dense size=sm')

                                    if is_completed:
                                        delete_button.disable()

                if len(buffer_data) > 0 and state['status'] != DOC_STATUS_COMPLETED:
                    save_draft_btn.enable()
                    generate_docs_btn.enable()
                    generate_indiv_docs_btn.enable()
                    complete_btn.enable()
                else:
                    if state['status'] != DOC_STATUS_COMPLETED:
                        save_draft_btn.disable()
                        generate_docs_btn.disable()
                        generate_indiv_docs_btn.disable()
                        complete_btn.disable()

            def refresh_status_ui():
                current_status = state.get('status', DOC_STATUS_DRAFT)
                status_badge.set_text(current_status)

                if current_status == DOC_STATUS_COMPLETED:
                    status_badge.props('color="green"')
                    complete_btn.disable()
                    save_draft_btn.disable()
                    generate_docs_btn.disable()
                    generate_indiv_docs_btn.disable()
                else:
                    status_badge.props('color="grey"')
                    if state['buffer']:
                        complete_btn.enable()
                        save_draft_btn.enable()
                        generate_docs_btn.enable()
                        generate_indiv_docs_btn.enable()

            def load_draft(d_id: int):
                try:
                    draft = notif_ctrl.get_doc_by_id(auth_manager.get_current_context(), d_id)
                    if draft:
                        state['out_number'] = draft.get('out_number', '')
                        state['out_date'] = draft.get('out_date', '')
                        state['region'] = draft.get('region', '')
                        state['buffer'] = draft.get('payload', [])
                        state['status'] = draft.get('status', DOC_STATUS_DRAFT)
                        saved_region = draft.get('region', '')
                        if saved_region:
                            state['filter_des_region'] = saved_region
                        elif state['buffer']:
                            state['filter_des_region'] = state['buffer'][0].get('desertion_region', '')

                        refresh_status_ui()
                        ui.notify('Чернетку завантажено', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка завантаження: {e}', type='negative')

            if notif_doc_id is not None:
                load_draft(notif_doc_id)

            refresh_buffer_ui()