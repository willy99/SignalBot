from nicegui import ui, run

from gui.controllers.dbr_controller import DbrController
from gui.controllers.person_controller import PersonController
from service.storage.FileCacher import FileCacheManager
from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from config import UI_DATE_FORMAT
from datetime import datetime, date
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED


def render_dbr_page(dbr_ctrl: DbrController, person_ctrl: PersonController, file_cache_manager: FileCacheManager,
                    ctx: RequestContext, dbr_doc_id: int = None):
    ui.label('Масова відправка справ на ДБР').classes('w-full text-center text-3xl font-bold mb-6')

    # Головний стейт сторінки
    state = {
        'status': DOC_STATUS_DRAFT,
        'out_date': None,
        'out_number': '',
        'buffer': [],  # Тут будуть зберігатися словники обраних осіб
        'current_search_results': {},
        'dbr_doc_id': dbr_doc_id,

        # Стейт для поточного обраного бійця (редагування перед додаванням)
        'edit_idx': None,
        'current_person': {
            'o_ass_num': '', 'o_ass_date': '',
            'o_res_num': '', 'o_res_date': '',
            'kpp_num': '', 'kpp_date': '',
            'dbr_num': '', 'dbr_date': ''
        }
    }

    # Допоміжна функція для форматування дати з БД
    def format_db_date(dt):
        if not dt: return ''
        if isinstance(dt, (datetime, date)): return dt.strftime('%d.%m.%Y')
        return str(dt)

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

                out_number_input = ui.input('Загальний вих. номер (СЄДО)').bind_value(state, 'out_number').classes(
                    'flex-1')
                out_date_input = date_input('Дата відправки', state, 'out_date', blur_handler=fix_date).classes(
                    'flex-1')

            # --- 2. Блок пошуку ---
            ui.label('Додавання військовослужбовців').classes('text-lg font-bold text-gray-700 mb-2')

            with ui.row().classes('w-full gap-2 items-center mb-4'):
                search_input = ui.input('ПІБ або РНОКПП...').classes('flex-grow').props('clearable autofocus outlined')
                search_btn = ui.button('Шукати', icon='search').props('elevated color="primary" size="md"')

            def on_person_selected(e):
                if not e.value:
                    person_details_container.set_visibility(False)
                    return

                # Заповнюємо форму даними з бази
                data = state['current_search_results'].get(e.value, {})
                state['current_person'].update({
                    'o_ass_num': data.get('o_ass_num', ''),
                    'o_ass_date': data.get('o_ass_date', ''),
                    'o_res_num': data.get('o_res_num', ''),
                    'o_res_date': data.get('o_res_date', ''),
                    'kpp_num': data.get('kpp_num', ''),
                    'kpp_date': data.get('kpp_date', ''),
                    'dbr_num': data.get('dbr_num', ''),
                    'dbr_date': data.get('dbr_date', '')
                })
                person_details_container.set_visibility(True)

            person_select = ui.select(options={}, label='Оберіть особу зі знайдених',
                                      on_change=on_person_selected).classes('w-full mb-4').props('outlined')
            person_select.visible = False

            # --- Форма додаткових полів для бійця ---
            with ui.column().classes(
                    'w-full gap-2 p-4 bg-blue-50 rounded-md border border-blue-100 mb-4') as person_details_container:
                person_details_container.set_visibility(False)
                ui.label('Деталі справи (будуть збережені в пейлоад)').classes('text-sm font-bold text-blue-800 mb-2')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input('Наказ призначення №').bind_value(state['current_person'], 'o_ass_num').classes(
                        'flex-1 bg-white')
                    date_input('Дата призначення', state['current_person'], 'o_ass_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input('Наказ результатів №').bind_value(state['current_person'], 'o_res_num').classes(
                        'flex-1 bg-white')
                    date_input('Дата результатів', state['current_person'], 'o_res_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input('Повід. КПП №').bind_value(state['current_person'], 'kpp_num').classes('flex-1 bg-white')
                    date_input('Дата повід. КПП', state['current_person'], 'kpp_date', fix_date).classes(
                        'flex-1 bg-white')

                with ui.row().classes('w-full items-center gap-4'):
                    ui.input('Вих. на ДБР №').bind_value(state['current_person'], 'dbr_num').classes('flex-1 bg-white')
                    date_input('Дата вих. на ДБР', state['current_person'], 'dbr_date', fix_date).classes(
                        'flex-1 bg-white')

            # --- Логіка пошуку ---
            async def perform_search(e=None):
                query = search_input.value
                if not query or len(query) < 2:
                    ui.notify('Введіть мінімум 2 літери для пошуку', type='warning')
                    return

                search_btn.disable()
                try:
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
                        id_num = f"{p.rnokpp}_{p.name}"
                        # Зберігаємо всі поля, які потрібні для редагування
                        state['current_search_results'][id_num] = {
                            'rnokpp': p.rnokpp,
                            'name': p.name,
                            'o_ass_num': getattr(p, 'o_ass_num', ''),
                            'o_ass_date': format_db_date(getattr(p, 'o_ass_date', '')),
                            'o_res_num': getattr(p, 'o_res_num', ''),
                            'o_res_date': format_db_date(getattr(p, 'o_res_date', '')),
                            'kpp_num': getattr(p, 'kpp_num', ''),
                            'kpp_date': format_db_date(getattr(p, 'kpp_date', '')),
                            'dbr_num': getattr(p, 'dbr_num', ''),
                            'dbr_date': format_db_date(getattr(p, 'dbr_date', ''))
                        }
                        options[id_num] = f"{p.name} (РНОКПП: {p.rnokpp})"

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

                selected_person = state['current_search_results'].get(selected_id, {})

                # Формуємо об'єкт для пейлоаду зі зміненими даними з форми
                raw_data = {
                    'id_number': selected_id,
                    'rnokpp': selected_person.get('rnokpp'),
                    'name': selected_person.get('name'),
                    # Забираємо актуальні значення прямо зі state['current_person']
                    'o_ass_num': state['current_person']['o_ass_num'],
                    'o_ass_date': state['current_person']['o_ass_date'],
                    'o_res_num': state['current_person']['o_res_num'],
                    'o_res_date': state['current_person']['o_res_date'],
                    'kpp_num': state['current_person']['kpp_num'],
                    'kpp_date': state['current_person']['kpp_date'],
                    'dbr_num': state['current_person']['dbr_num'],
                    'dbr_date': state['current_person']['dbr_date']
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
        with ui.column().classes('col-span-12 md:col-span-4 w-full'):
            ui.label('Список на відправку:').classes('text-xl font-bold')
            buffer_container = ui.column().classes(
                'w-full gap-2 p-4 border rounded-lg bg-gray-50 min-h-[300px] shadow-inner')

            def on_remove_click(idx):
                if 0 <= idx < len(state['buffer']):
                    removed = state['buffer'].pop(idx)
                    ui.notify(f"{removed['name']} видалено зі списку", type='info')
                if state['edit_idx'] == idx:
                    clear_inputs()
                elif state['edit_idx'] is not None and state['edit_idx'] > idx:
                    state['edit_idx'] -= 1
                refresh_buffer_ui()

            def on_edit_click(idx):
                state['edit_idx'] = idx
                doc = state['buffer'][idx]
                id_num = doc['id_number']

                # Відновлюємо візуальний стан зліва
                search_input.value = doc['name']

                # Тимчасово кладемо в current_search_results, щоб on_person_selected спрацював коректно
                state['current_search_results'][id_num] = doc
                person_select.options = {id_num: f"{doc['name']} (РНОКПП: {doc.get('rnokpp', '')})"}
                person_select.value = id_num
                person_select.visible = True

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
                if not state['out_number'] or not state['out_date']:
                    ui.notify('Обов\'язково заповніть номер та дату відправки!', type='warning')
                    return

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
                        state['out_number'] = draft.get('out_number', '')
                        state['out_date'] = draft.get('out_date', '')
                        state['buffer'] = draft.get('payload', [])
                        state['status'] = draft.get('status', DOC_STATUS_DRAFT)
                        refresh_status_ui()
                        ui.notify(f'Чернетку завантажено', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка завантаження: {e}', type='negative')

            if dbr_doc_id is not None:
                load_draft(dbr_doc_id)

            refresh_buffer_ui()


# --- Допоміжні функції (залишаються без змін) ---
def date_input(label: str, state, field: str, blur_handler=None):
    inp = ui.input(label=label).bind_value(state, field)
    if blur_handler: inp.on('blur', blur_handler)
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