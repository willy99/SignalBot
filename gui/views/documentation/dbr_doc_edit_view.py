from nicegui import ui, run

from gui.controllers.dbr_controller import DbrController
from gui.controllers.person_controller import PersonController
from service.storage.FileCacher import FileCacheManager
from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from config import UI_DATE_FORMAT
from datetime import datetime
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED

def render_dbr_page(dbr_ctrl: DbrController, person_ctrl: PersonController, file_cache_manager:FileCacheManager, ctx: RequestContext, dbr_doc_id: int = None):
    ui.label('Масова відправка справ на ДБР').classes('w-full text-center text-3xl font-bold mb-6')

    state = {
        'status': DOC_STATUS_DRAFT,
        'out_date': None,
        'out_number': '',
        'buffer': [],  # Тут будуть зберігатися словники обраних осіб
        'current_search_results': {},
        'dbr_doc_id': dbr_doc_id
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

                out_number_input = ui.input('Вихідний номер (СЄДО)').bind_value(state, 'out_number').classes('flex-1')
                out_date_input = date_input('Дата відправки', state, 'out_date', blur_handler=fix_date).classes(
                    'flex-1')

            # --- 2. Блок пошуку ---
            ui.label('Додавання військовослужбовців').classes('text-lg font-bold text-gray-700 mb-2')

            with ui.row().classes('w-full gap-2 items-center mb-4'):
                search_input = ui.input('ПІБ або РНОКПП...').classes('flex-grow').props('clearable autofocus outlined')
                search_btn = ui.button('Шукати', icon='search').props('elevated color="primary" size="md"')

            person_select = ui.select(options={}, label='Оберіть особу зі знайдених').classes('w-full mb-4').props(
                'outlined')
            person_select.visible = False

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
                        return

                    for person in results:
                        # Створюємо унікальний ключ для селекта
                        id_num = f"{person.rnokpp}_{person.name}"
                        state['current_search_results'][id_num] = {
                            'rnokpp': person.rnokpp,
                            'name': person.name,
                            'o_ass_num': person.o_ass_num,
                            'desertion_date': getattr(person, 'desertion_date', 'Невідомо')  # Якщо є таке поле
                        }
                        options[id_num] = f"{person.name} (РНОКПП: {person.rnokpp}, Наказ: {person.o_ass_num})"

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

            # --- Додавання до буфера ---
            def on_add_click():
                selected_id = person_select.value
                if not selected_id:
                    ui.notify('Оберіть військовослужбовця зі списку!', type='warning')
                    return

                buffer_data = state['buffer']

                if any(doc['id_number'] == selected_id for doc in buffer_data):
                    ui.notify(f'Ця особа вже є у списку на відправку!', type='warning')
                    return

                selected_person = state['current_search_results'].get(selected_id, {})

                # Додаємо в буфер
                buffer_data.append({
                    'id_number': selected_id,
                    'rnokpp': selected_person.get('rnokpp'),
                    'name': selected_person.get('name'),
                    'o_ass_num': selected_person.get('o_ass_num')
                })

                ui.notify(f"{selected_person.get('name')} додано до списку!", type='positive')

                # Очищаємо пошук для наступного
                search_input.value = ''
                person_select.visible = False
                refresh_buffer_ui()

            with ui.row().classes('w-full mt-2'):
                ui.button('Додати до пакету', on_click=on_add_click, icon='add').classes('flex-grow').props(
                    'color="blue"')

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
                refresh_buffer_ui()

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
                                with ui.column().classes('gap-0 w-4/5'):
                                    ui.label(f"{i + 1}. {p['name']}").classes('font-bold text-sm truncate w-full')
                                    ui.label(f"РНОКПП: {p['rnokpp']} | Наказ: {p.get('o_ass_num', '')}").classes(
                                        'text-xs text-gray-500')

                                delete_button = ui.button(icon='close', color='red',
                                                          on_click=lambda idx=i: on_remove_click(idx)).props(
                                    'flat dense size=sm')

                                if state['status'] == DOC_STATUS_COMPLETED:
                                    delete_button.disable()

                save_draft_btn.set_visibility(len(buffer_data) > 0)
                complete_btn.set_visibility(len(buffer_data) > 0)

            # --- Збереження та відправка ---
            async def on_save_draft_click():
                save_draft_btn.disable()
                try:
                    # TODO: Реалізувати в dbr_ctrl збереження в БД
                    dbr_doc_id = await run.io_bound(
                        dbr_ctrl.save_draft,
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

                # TODO: Відправка на ДБР (апдейт статусів людей в Excel/БД)
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

                if current_status == DOC_STATUS_DRAFT:
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
                    # TODO: Реалізувати отримання чернетки з БД
                    draft = dbr_ctrl.get_draft_by_id(ctx, d_id)
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


# --- Допоміжні функції (такі ж, як у вас) ---
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