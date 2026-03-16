from nicegui import ui, run

from dics.deserter_xls_dic import COLUMN_ORDER_ASSIGNMENT_NUMBER, COLUMN_ORDER_ASSIGNMENT_DATE, \
    COLUMN_ORDER_RESULT_NUMBER, COLUMN_ORDER_RESULT_DATE, COLUMN_KPP_NUMBER, COLUMN_KPP_DATE, COLUMN_DBR_NUMBER, \
    COLUMN_DBR_DATE, VALID_PATTERN_DOC_NUM
from gui.controllers.dbr_controller import DbrController
from gui.controllers.person_controller import PersonController
from service.storage.FileCacher import FileCacheManager
from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED
from gui.tools.validation import is_number, is_valid_doc_number
from utils.utils import format_to_excel_date
from gui.tools.ui_components import date_input, fix_date
import re

def render_dbr_page(dbr_ctrl: DbrController, person_ctrl: PersonController, file_cache_manager: FileCacheManager,
                    ctx: RequestContext, dbr_doc_id: int = None):
    ui.label('Масова відправка справ на ДБР').classes('w-full text-center text-3xl font-bold mb-6')

    # Головний стейт сторінки
    state = {
        'status': DOC_STATUS_DRAFT,
        'out_date': None,
        'out_number': '',
        'buffer': [],
        'current_search_results': {},
        'dbr_doc_id': dbr_doc_id,

        'edit_idx': None,
        'current_person': {
            'o_ass_num': '', 'o_ass_date': '',
            'o_res_num': '', 'o_res_date': '',
            'kpp_num': '', 'kpp_date': '',
            'dbr_num': '', 'dbr_date': '',
            'review_status': ''
        }
    }

    with ui.grid(columns=12).classes('w-full gap-6 items-start max-w-7xl mx-auto'):

        # ==========================================
        # ЛІВА ЧАСТИНА: ПОШУК ТА ДОДАВАННЯ
        # ==========================================
        with ui.card().classes('col-span-12 md:col-span-8 w-full shadow-md p-6'):

            # --- 1. Шапка документа (статус, номер, дата) ---
            status_text = state.get('status', DOC_STATUS_DRAFT)
            badge_color = 'green' if status_text == DOC_STATUS_COMPLETED else 'grey'

            with ui.row().classes('w-full items-center gap-5 mb-6 pb-4 border-b border-gray-100'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('Статус:').classes('text-gray-500 font-medium')
                    status_badge = ui.badge(status_text, color=badge_color).classes('text-sm px-2 py-1')

                out_number_input = ui.input('Загальний вих. номер (СЕДО)', placeholder='Наприклад: 642/123', validation={
                   'Формат має бути 642/ХХХХ (до 4 цифр)': lambda v: bool(re.match(VALID_PATTERN_DOC_NUM, v.strip())) if v else True
                    }) \
                    .bind_value(state, 'out_number') \
                    .on_value_change(lambda e: state['current_person'].update({'dbr_num': e.value + '/'})) \
                    .classes('flex-1').props('hide-bottom-space')
                out_date_input = date_input(
                    'Дата відправки', state, 'out_date',
                    blur_handler=fix_date,
                ).classes('flex-1').on_value_change(lambda e: state['current_person'].update({'dbr_date': e.value})) \
                 .classes('flex-1')

            # --- 2. Блок пошуку ---
            ui.label('Додавання військовослужбовців').classes('text-lg font-bold text-gray-700 mb-2')

            with ui.row().classes('w-full gap-2 items-center mb-4'):
                search_input = ui.input('ПІБ або Номер наказу...').classes('flex-grow').props('clearable autofocus outlined')
                search_btn = ui.button('Шукати', icon='search').props('elevated color="primary" size="md"')

            def update_review_badge(status_val):
                """Оновлює колір та текст бейджа статусу"""
                if not status_val:
                    review_status_badge.set_visibility(False)
                    return

                review_status_badge.set_text(f"Статус: {status_val}")
                if status_val.strip().upper() == 'ЄРДР':
                    review_status_badge.props('color="red"')
                else:
                    review_status_badge.props('color="green"')
                review_status_badge.set_visibility(True)

            def on_person_selected(e):
                if not e.value:
                    person_details_container.set_visibility(False)
                    return

                # Заповнюємо форму даними з бази
                data = state['current_search_results'].get(e.value, {})
                db_dbr_num = data.get('dbr_num', '')
                db_dbr_date = data.get('dbr_date', '')
                rev_status = data.get('review_status', '')

                state['current_person'].update({
                    'o_ass_num': data.get('o_ass_num', ''),
                    'o_ass_date': data.get('o_ass_date', ''),
                    'o_res_num': data.get('o_res_num', ''),
                    'o_res_date': data.get('o_res_date', ''),
                    'kpp_num': data.get('kpp_num', ''),
                    'kpp_date': data.get('kpp_date', ''),
                    'dbr_num': db_dbr_num if (db_dbr_num and db_dbr_num != '0') else state.get('out_number', ''),
                    'dbr_date': db_dbr_date if db_dbr_date else state.get('out_date', ''),
                    'review_status': rev_status
                })
                person_details_container.set_visibility(True)
                update_review_badge(rev_status)

            person_select = ui.select(options={}, label='Оберіть особу зі знайдених',
                                      on_change=on_person_selected).classes('w-full mb-4').props('outlined')
            person_select.visible = False

            # --- Форма додаткових полів для бійця ---
            with ui.column().classes(
                    'w-full gap-2 p-4 bg-blue-50 rounded-md border border-blue-100 mb-4') as person_details_container:
                person_details_container.set_visibility(False)
                # Заголовок та бейдж статусу в один рядок
                with ui.row().classes('w-full items-center justify-between mb-2'):
                    ui.label('Деталі справи').classes('text-sm font-bold text-blue-800')
                    review_status_badge = ui.badge('', color='green').classes('text-xs font-bold px-2 py-1 shadow-sm')
                    review_status_badge.set_visibility(False)

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(state['current_person'], 'o_ass_num').classes(
                        'flex-1 bg-white')
                    date_input(COLUMN_ORDER_ASSIGNMENT_DATE, state['current_person'], 'o_ass_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(state['current_person'], 'o_res_num').classes(
                        'flex-1 bg-white')
                    date_input(COLUMN_ORDER_RESULT_DATE, state['current_person'], 'o_res_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input(COLUMN_KPP_NUMBER).bind_value(state['current_person'], 'kpp_num').classes('flex-1 bg-white')
                    date_input(COLUMN_KPP_DATE, state['current_person'], 'kpp_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input(COLUMN_DBR_NUMBER).bind_value(state['current_person'], 'dbr_num').classes('flex-1 bg-white')
                    date_input(COLUMN_DBR_DATE, state['current_person'], 'dbr_date', fix_date).classes(
                        'flex-1 bg-white')

            # --- Логіка пошуку ---
            async def perform_search(e=None):
                query = search_input.value
                if not query or len(query) < 2:
                    ui.notify('Введіть мінімум 2 літери для пошуку', type='warning')
                    return

                search_btn.disable()
                try:
                    if is_number(query):
                        search_filter = PersonSearchFilter(o_ass_num=query)
                    else:
                        search_filter = PersonSearchFilter(query=query)
                    results = await run.io_bound(person_ctrl.search, ctx, search_filter)

                    state['current_search_results'].clear()
                    options = {}

                    if not results:
                        ui.notify('За цим запитом нікого не знайдено', type='warning')
                        person_select.visible = False
                        person_details_container.set_visibility(False)
                        return

                    for p in results:
                        # 2. Фільтруємо: якщо номер є, він не порожній, не '0' і не 'None'
                        raw_dbr = getattr(p, 'dbr_num', '')
                        dbr_num = str(raw_dbr).strip() if raw_dbr else ''
                        if dbr_num and dbr_num != '0' and dbr_num.lower() != 'none':
                            continue  # Пропускаємо цю особу, бо вона вже має номер ДБР

                        id_num = f"{p.rnokpp}_{p.name}_{p.desertion_date}"
                        state['current_search_results'][id_num] = {
                            'rnokpp': p.rnokpp,
                            'name': p.name,
                            'o_ass_num': getattr(p, 'o_ass_num', ''),
                            'o_ass_date': format_to_excel_date(getattr(p, 'o_ass_date', '')),
                            'o_res_num': getattr(p, 'o_res_num', ''),
                            'o_res_date': format_to_excel_date(getattr(p, 'o_res_date', '')),
                            'kpp_num': getattr(p, 'kpp_num', ''),
                            'kpp_date': format_to_excel_date(getattr(p, 'kpp_date', '')),
                            'dbr_num': getattr(p, 'dbr_num', ''),
                            'dbr_date': format_to_excel_date(getattr(p, 'dbr_date', '')),
                            'review_status': getattr(p, 'review_status', '')
                        }
                        options[id_num] = f"{p.name} (РНОКПП: {p.rnokpp} СЗЧ: {p.desertion_date})"

                    # 3. ПЕРЕВІРКА ПІСЛЯ ФІЛЬТРАЦІЇ
                    if not options:
                        ui.notify('Всі знайдені особи вже мають вихідний номер на ДБР!', type='warning')
                        person_select.visible = False
                        person_details_container.set_visibility(False)
                        return

                    person_select.options = options
                    person_select.visible = True
                    person_select.value = list(options.keys())[0]  # Автовибір першого

                    ui.notify(f'Знайдено збігів: {len(options)}', type='info')

                except Exception as ex:
                    ui.notify(f'Помилка пошуку: {ex}', type='negative')
                finally:
                    search_btn.enable()

            search_input.on('keydown.enter', perform_search)
            search_btn.on('click', perform_search)

            # --- Очищення полів ---
            def clear_inputs():
                state['edit_idx'] = None
                search_input.value = ''
                person_select.value = None
                person_select.visible = False
                person_details_container.set_visibility(False)

                # Обнуляємо форму
                for key in state['current_person']:
                    state['current_person'][key] = ''

                add_btn.text = 'Додати до пакету'
                add_btn.props('color="blue" icon="add"')
                cancel_btn.set_visibility(False)

            # --- Додавання до буфера ---
            def on_add_click():
                selected_id = person_select.value
                if not selected_id:
                    ui.notify('Оберіть військовослужбовця зі списку!', type='warning')
                    return

                buffer_data = state['buffer']
                edit_idx = state['edit_idx']

                # Перевірка дублікатів (ігноруємо той запис, який зараз редагуємо)
                existing_ids = [doc['id_number'] for i, doc in enumerate(buffer_data) if i != edit_idx]
                if selected_id in existing_ids:
                    ui.notify(f'Ця особа вже є у списку на відправку!', type='warning')
                    return

                # 2. ВАЛІДАЦІЯ: Перевірка унікальності номера ДБР у поточному списку
                new_dbr_num = state['current_person'].get('dbr_num', '').strip()
                if new_dbr_num:
                    for i, doc in enumerate(buffer_data):
                        if i != edit_idx and doc.get('dbr_num') == new_dbr_num:
                            ui.notify(
                                f'Увага! Номер виходу на ДБР "{new_dbr_num}" вже використовується для іншої особи у цьому списку!',
                                type='negative')
                            return

                selected_person = state['current_search_results'].get(selected_id, {})

                # Формуємо об'єкт для пейлоаду зі зміненими даними з форми
                raw_data = {
                    'id_number': selected_id,
                    'rnokpp': selected_person.get('rnokpp', ''),
                    'name': selected_person.get('name', ''),
                    'desertion_date': selected_person.get('desertion_date', ''),
                    'o_ass_num': state['current_person']['o_ass_num'],
                    'o_ass_date': state['current_person']['o_ass_date'],
                    'o_res_num': state['current_person']['o_res_num'],
                    'o_res_date': state['current_person']['o_res_date'],
                    'kpp_num': state['current_person']['kpp_num'],
                    'kpp_date': state['current_person']['kpp_date'],
                    'dbr_num': state['current_person']['dbr_num'],
                    'dbr_date': state['current_person']['dbr_date'],
                    'review_status': state['current_person']['review_status']
                }

                if edit_idx is not None:
                    buffer_data[edit_idx] = raw_data
                    ui.notify(f"Дані оновлено!", type='positive')
                else:
                    buffer_data.append(raw_data)
                    ui.notify(f"{raw_data['name']} додано до списку!", type='positive')

                refresh_buffer_ui()
                clear_inputs()

            with ui.row().classes('w-full mt-2 gap-2'):
                add_btn = ui.button('Додати до пакету', on_click=on_add_click, icon='add').classes('flex-grow').props(
                    'color="blue"')
                cancel_btn = ui.button('Скасувати', on_click=clear_inputs, icon='close').props('flat').classes(
                    'text-gray-500 bg-gray-200')
                cancel_btn.set_visibility(False)

        # ==========================================
        # ПРАВА ЧАСТИНА: БУФЕР ТА ДІЇ
        # ==========================================
        # СТАЛО:
        with ui.column().classes(
                'col-span-12 md:col-span-4 w-full') as right_panel:
            ui.label('Список на відправку:').classes('text-xl font-bold')
            buffer_container = ui.column().classes(
                'w-full gap-2 p-4 border rounded-lg bg-gray-50 min-h-[300px] shadow-inner')

            async def on_remove_click(idx):
                with right_panel:
                    dialog = ui.dialog()
                    with dialog, ui.card().classes('p-6 min-w-[300px]'):
                        ui.label('Підтвердження').classes('text-xl font-bold text-red-600 mb-2')
                        ui.label('Ви дійсно хочете видалити цю особу зі списку?').classes('text-gray-600 mb-6')

                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                            ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

                result = await dialog

                if result:
                    if 0 <= idx < len(state['buffer']):
                        removed = state['buffer'].pop(idx)
                        ui.notify(f"{removed.get('name', 'Особу')} видалено зі списку", type='info')

                    if state['edit_idx'] == idx:
                        clear_inputs()
                    elif state['edit_idx'] is not None and state['edit_idx'] > idx:
                        state['edit_idx'] -= 1

                    refresh_buffer_ui()

            def on_edit_click(idx):
                state['edit_idx'] = idx
                doc = state['buffer'][idx]
                id_num = doc['id_number']

                search_input.value = doc['name']

                state['current_search_results'][id_num] = doc
                rnokpp_str = doc.get('rnokpp', 'Невідомо')
                des_date_str = doc.get('desertion_date', 'Невідомо')

                # Показуємо всю інформацію у селекті під час редагування
                person_select.options = {id_num: f"{doc['name']} (РНОКПП: {rnokpp_str} СЗЧ: {des_date_str})"}
                person_select.value = id_num
                person_select.visible = True

                update_review_badge(doc.get('review_status', ''))

                # Змінюємо кнопку на "Зберегти"
                add_btn.text = 'Зберегти зміни'
                add_btn.props('color="orange" icon="save"')
                cancel_btn.set_visibility(True)

                ui.notify(f"Редагування...", type='info')

            def refresh_buffer_ui():
                buffer_container.clear()
                buffer_data = state['buffer']

                with buffer_container:
                    if not buffer_data:
                        ui.label('Список порожній. Знайдіть та додайте осіб.').classes(
                            'text-gray-400 italic text-center w-full mt-10')
                    else:
                        ui.label(f'Всього у списку: {len(buffer_data)}').classes('text-sm font-bold text-blue-600 mb-2')
                        for i, p in enumerate(buffer_data):
                            with ui.row().classes(
                                    'w-full justify-between items-center bg-white p-2 border rounded shadow-sm hover:bg-gray-100 transition-colors'):
                                with ui.column().classes('gap-0 w-3/4'):
                                    ui.label(f"{i + 1}. {p['name']}").classes('font-bold text-sm truncate w-full')
                                    # Виводимо частину інформації для розуміння
                                    info_str = f"Нак: {p.get('o_ass_num', '—')} | ДБР: {p.get('dbr_num', '—')}"
                                    ui.label(info_str).classes('text-xs text-gray-500')
                                    if p.get('review_status') == 'ЄРДР':
                                        ui.badge('ЄРДР', color='red').classes('text-[10px] px-1 py-0 mt-1')

                                with ui.row().classes('gap-1'):
                                    edit_button = ui.button(icon='edit', color='blue',
                                                            on_click=lambda idx=i: on_edit_click(idx)).props(
                                        'flat dense size=sm')
                                    delete_button = ui.button(icon='close', color='red',
                                                              on_click=lambda idx=i: on_remove_click(idx)).props(
                                        'flat dense size=sm')

                                    if state['status'] == DOC_STATUS_COMPLETED:
                                        edit_button.disable()
                                        delete_button.disable()

                save_draft_btn.set_visibility(len(buffer_data) > 0)
                complete_btn.set_visibility(len(buffer_data) > 0)

            # --- Збереження та відправка ---
            async def on_save_draft_click():
                save_draft_btn.disable()
                try:
                    dbr_doc_id = await run.io_bound(
                        dbr_ctrl.save_dbr_doc,
                        ctx,
                        state['out_number'],
                        state['out_date'],
                        state['buffer'],
                        state['dbr_doc_id']
                    )
                    state['dbr_doc_id'] = dbr_doc_id
                    ui.notify(f'Чернетку збережено!', type='positive', icon='cloud_done')
                except Exception as e:
                    ui.notify(f'Помилка БД: {e}', type='negative')
                finally:
                    save_draft_btn.enable()


            async def on_send_dbr_click():

                out_num = out_number_input.value.strip()
                if not is_valid_doc_number(out_num):
                    ui.notify('❌ Увага! Невірний формат вихідного номера. Має бути 642/ХХХХ', type='negative')
                    return
                await on_save_draft_click()

                complete_btn.disable()
                complete_btn.props('loading')
                ui.notify('⏳ Оновлюємо дані в Excel, зачекайте...', type='info')

                try:

                    success = await run.io_bound(
                        dbr_ctrl.mark_as_completed,
                        ctx,
                        state['dbr_doc_id'],
                        state['buffer'],
                        state['out_number'],
                        state['out_date'],
                        person_ctrl
                    )

                    if success:
                        state['status'] = DOC_STATUS_COMPLETED
                        refresh_status_ui()
                        ui.notify(f'Справи успішно відправлені на ДБР!', type='positive')
                    else:
                        ui.notify(f'Виникла помилка під час відправки', type='negative')
                except Exception as e:
                    # 3. Перехоплюємо помилки, які ви кидаєте через raise Exception у контролері
                    ui.notify(f'❌ Помилка під час відправки: {e}', type='negative')

                finally:
                    # 4. Обов'язково знімаємо лоадер, розблоковуємо кнопку і прибираємо сповіщення
                    complete_btn.props(remove='loading')
                    if state.get('status') != DOC_STATUS_COMPLETED:
                        complete_btn.enable()

            save_draft_btn = ui.button('ЗБЕРЕГТИ ЧЕРНЕТКУ', on_click=on_save_draft_click, icon='save').classes(
                'w-full mt-4 h-12').props('outline color="primary"')
            complete_btn = ui.button('ПІДТВЕРДИТИ ВІДПРАВКУ', on_click=on_send_dbr_click, icon='send').classes(
                'w-full mt-2 h-12').props('color="green"')

            def refresh_status_ui():
                current_status = state.get('status', DOC_STATUS_DRAFT)
                status_badge.set_text(current_status)

                if current_status == DOC_STATUS_COMPLETED:
                    status_badge.props('color="green"')
                    complete_btn.disable()
                    save_draft_btn.disable()
                else:
                    status_badge.props('color="grey"')
                    complete_btn.enable()
                    save_draft_btn.enable()

            # --- Завантаження існуючої чернетки ---
            def load_draft(d_id: int):
                try:
                    draft = dbr_ctrl.get_dbr_doc_by_id(ctx, d_id)
                    if draft:
                        out_num = draft.get('out_number', '')
                        out_date = draft.get('out_date', '')

                        state['out_number'] = out_num
                        out_number_input.set_value(out_num)

                        state['out_date'] = out_date
                        out_date_input.set_value(out_date)

                        state['buffer'] = draft.get('payload', [])
                        state['status'] = draft.get('status', DOC_STATUS_DRAFT)

                        refresh_status_ui()
                        refresh_buffer_ui()
                        ui.notify(f'Чернетку завантажено', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка завантаження: {e}', type='negative')

            if dbr_doc_id is not None:
                load_draft(dbr_doc_id)
            else:
                refresh_buffer_ui()
