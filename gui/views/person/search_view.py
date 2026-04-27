from nicegui import ui
from dics.deserter_xls_dic import *
from domain.person import Person
from gui.services.auth_manager import AuthManager
from gui.views.person.person_view import edit_person
from domain.person_filter import PersonSearchFilter
import config
from dics.security_config import MODULE_PERSON, PERM_EDIT
from utils.utils import format_to_excel_date
from datetime import datetime

ui.add_css('''
    .my-sticky-header-table thead tr th {
        position: sticky;
        z-index: 1;
        background-color: #f3f4f6; /* Це колір bg-gray-100 Tailwind */
        font-weight: bold;
    }
    .my-sticky-header-table thead tr:first-child th {
        top: 0;
    }
''', shared=True)

def results_ui(data, person_ctrl, auth_manager: AuthManager, refresh_callback):
    if not data:
        return
    can_edit = auth_manager.has_access(MODULE_PERSON, PERM_EDIT)
    columns = [
        {'name': 'pib', 'label': COLUMN_NAME, 'field': 'pib', 'align': 'left', 'sortable': True, 'classes': 'whitespace-normal min-w-[150px]'},
        {'name': 'voc_info', 'label': 'Посада (ВОС)', 'field': 'voc_info', 'align': 'left'},
        {'name': 'title2', 'label': COLUMN_TITLE_2, 'field': 'title2', 'sortable': True},
        {'name': 'rnokpp', 'label': COLUMN_ID_NUMBER, 'field': 'rnokpp', 'sortable': True},
        {'name': 'unit', 'label': COLUMN_SUBUNIT, 'field': 'unit', 'sortable': True, 'classes': 'whitespace-normal min-w-[120px]'},
        {'name': 'desertion_date', 'label': COLUMN_DESERTION_DATE, 'field': 'desertion_date', 'sortable': True},
        {'name': 'return_date', 'label': COLUMN_RETURN_DATE, 'field': 'return_date', 'sortable': True},
        {'name': 'return_reserve_date', 'label': COLUMN_RETURN_TO_RESERVE_DATE, 'field': 'return_reserve_date', 'sortable': True},
        {'name': 'desertion_type', 'label': COLUMN_DESERTION_TYPE, 'field': 'desertion_type', 'sortable': True},
        {'name': 'erdr_date', 'label': COLUMN_ERDR_DATE, 'field': 'erdr_date', 'sortable': True},
        {'name': 'erdr_notation', 'label': COLUMN_ERDR_NOTATION, 'field': 'erdr_notation', 'sortable': True, 'classes': 'whitespace-normal min-w-[150px]'},
        {'name': 'action', 'label': 'Дія', 'field': 'action', 'align': 'center'},
    ]

    rows = []
    for person in data:
        rows.append({
            'pib': person.name,
            'voc_info': getattr(person, 'matched_voc_info', ''),
            'title2': person.title2,
            'rnokpp': person.rnokpp,
            'unit': person.subunit,
            'desertion_date': person.desertion_date,
            'return_date': person.return_date,
            'return_reserve_date': person.return_reserve_date,
            'desertion_type': person.desertion_type,
            'erdr_date': person.erdr_date,
            'erdr_notation': person.erdr_notation,
            'raw_model': person.model_dump()
        })

    # 💡 Головна зміна: додаємо .props('wrap-cells') і використовуємо w-full
    table = ui.table(columns=columns, rows=rows, row_key='rnokpp').classes(
        'w-full general-table my-sticky-header-table max-h-[70vh]'
    ).props('wrap-cells flat bordered')

    if can_edit:
        table.add_slot('body-cell-action', '''
                    <q-td :props="props">
                        <q-btn size="sm" color="primary" icon="edit" @click="$parent.$emit('editAction', props.row.raw_model)">
                            Редагувати
                        </q-btn>
                    </q-td>
                ''')

    table.on('editAction', lambda e: edit_person(
        Person(**e.args),
        person_ctrl,
        auth_manager=auth_manager,
        on_close=refresh_callback
    ))

    with ui.row().classes('w-full justify-end mt-2 px-2'):
        ui.label(f'Всього знайдено записів: {len(data)}').classes('text-gray-600 font-bold')

def search_page(person_ctrl, auth_manager: AuthManager):
    state = {
        'last_query': None, 'last_title2': None, 'last_service': None,
        'last_des_year': None, 'last_des_from': None, 'last_des_to': None, 'last_ins_year': None
    }

    ui_options = person_ctrl.get_column_options()
    des_year_options = ui_options.get(COLUMN_DESERTION_DATE, [])
    ins_year_options = ui_options.get(COLUMN_INSERT_DATE, [])
    title2_options = ['Всі'] + [opt for opt in ui_options.get(COLUMN_TITLE_2, []) if opt]
    service_options = ['Всі'] + [opt for opt in ui_options.get(COLUMN_SERVICE_TYPE, []) if opt]
    can_edit = auth_manager.has_access(MODULE_PERSON, PERM_EDIT)

    # --- 1. ДОДАЄМО ASYNC ТА AWAIT В ОБРОБНИКИ ДАТ ---
    async def on_year_change(e):
        if e.value:
            des_date_from.set_value(None)
            des_date_to.set_value(None)
            des_date_from.disable()
            des_date_to.disable()
        else:
            des_date_from.enable()
            des_date_to.enable()
        await do_search(auto_open=False)

    async def on_date_change(e):
        if des_date_from.value or des_date_to.value:
            des_year_filter.set_value(None)
            des_year_filter.disable()
        else:
            des_year_filter.enable()
        await do_search(auto_open=False)

    # --- 2. СТВОРЮЄМО ФУНКЦІЇ-ОБГОРТКИ ДЛЯ КНОПОК І СЕЛЕКТІВ (ЗАМІСТЬ LAMBDA) ---
    async def handle_search(e=None):
        await do_search(auto_open=True)

    async def handle_filter_change(e=None):
        await do_search(auto_open=False)

    # --- ГОЛОВНА ФУНКЦІЯ ПОШУКУ (без змін) ---
    async def do_search(auto_open=True, force_refresh=False):
        query = (search_field.value or "").strip()
        des_year_val = des_year_filter.value if des_year_filter.value else None
        ins_year_val = ins_year_filter.value if ins_year_filter.value else None
        date_from_val = des_date_from.value if des_date_from.value else None
        date_to_val = des_date_to.value if des_date_to.value else None
        title2_val = None if title2_filter.value == 'Всі' else title2_filter.value
        service_val = None if service_filter.value == 'Всі' else service_filter.value
        mil_unit = sheet_select.value

        if not any([query, des_year_val, ins_year_val, date_from_val, date_to_val, title2_val, service_val]):
            ui.notify('Введіть запит або оберіть фільтр для пошуку', type='warning')
            return

        if not force_refresh and (state['last_query'] == query and state['last_des_year'] == des_year_val and
                                  state['last_ins_year'] == ins_year_val and state['last_des_from'] == date_from_val and
                                  state['last_des_to'] == date_to_val and state['last_title2'] == title2_val and state[
                                      'last_service'] == service_val):
            ui.notify('Цей запит вже виконано', type='info')
            return

        state.update({
            'last_query': query, 'last_des_year': des_year_val, 'last_ins_year': ins_year_val,
            'last_des_from': date_from_val, 'last_des_to': date_to_val, 'last_title2': title2_val,
            'last_service': service_val,
            'mil_unit': mil_unit
        })

        results_container.clear()
        with results_container:
            ui.spinner(size='lg').classes('mt-10')

        try:
            search_filter = PersonSearchFilter(
                query=query if query else None, des_year=des_year_val, ins_year=ins_year_val,
                des_date_from=date_from_val, des_date_to=date_to_val, title2=title2_val, service_type=service_val, mil_unit=mil_unit
            )
            data = await auth_manager.execute(person_ctrl.search, auth_manager.get_current_context(), search_filter)
            results_container.clear()

            if not data:
                ui.notify('Нічого не знайдено', type='negative')
                state['last_query'] = None
                return

            # ТУТ lambda працює нормально, бо ui.timer очікує звичайну функцію (не async)
            refresh_cb = lambda: ui.timer(0, lambda: do_search(auto_open=False, force_refresh=True), once=True)
            if len(data) == 1 and auto_open:
                edit_person(data[0], person_ctrl, auth_manager=auth_manager, on_close=refresh_cb)
            if len(data) > config.MAX_QUERY_RESULTS:
                ui.notify(
                    f'⚠️ Знайдено занадто багато результатів ({len(data)}). Показано перші {config.MAX_QUERY_RESULTS}. Будь ласка, уточніть параметри пошуку',
                    type='warning',
                    timeout=8000
                )
                data = data[:config.MAX_QUERY_RESULTS]  # Відсікаємо все зайве
            with results_container:
                results_ui(data, person_ctrl, auth_manager=auth_manager, refresh_callback=refresh_cb)

        except Exception as e:
            results_container.clear()
            state['last_query'] = None
            ui.notify(f'Помилка пошуку: {e}', type='negative')

    # --- 3. МАЛЮЄМО UI ТА ПРИВ'ЯЗУЄМО НОВІ ФУНКЦІЇ ---
    with ui.column().classes('w-full items-center p-4'):
        ui.label('Пошук і редагування подій').classes('text-h4 mb-4')

        with ui.row().classes('w-full max-w-4xl items-center gap-4'):
            # Головний рядок пошуку
            with ui.row().classes('w-full max-w-7xl items-center gap-4'):
                # НОВИЙ ЕЛЕМЕНТ: Вибір ВЧ (листа Excel)
                sheet_select = ui.select(
                    options=MIL_UNITS,
                    value=MIL_UNITS[0],
                    label='ВЧ',
                ).classes('w-32')

                search_field = ui.input(label='Введіть дані (ПІБ або РНОКПП)').classes('flex-grow').props(
                    'autofocus clearable')

                # Замість lambda просто передаємо посилання на handle_search
                search_field.on('keydown.enter', handle_search)
                ui.button('Знайти', icon='search', on_click=handle_search).props('elevated').classes(
                    'h-14 bg-blue-600 text-white')

                if can_edit:  # Перевіряємо права доступу
                    async def create_new_person():
                        # Створюємо пустий об'єкт Person.
                        # Обов'язково вказуємо unit з поточного вибору селектора ВЧ
                        new_p = Person(
                            insert_date=format_to_excel_date(datetime.now()),
                            name="",
                            rnokpp="",
                            subunit="",
                            mil_unit=sheet_select.value,
                            cc_article='407',
                            desertion_type='СЗЧ',
                            review_status=DEFAULT_REVIEW_STATUS
                        )

                        # Викликаємо ту саму форму, що і для редагування
                        edit_person(
                            new_p,
                            person_ctrl,
                            auth_manager=auth_manager,
                            on_close=lambda: do_search(force_refresh=True)  # Оновити список після збереження
                        )

                    ui.button(icon='add', on_click=create_new_person).props('elevated color="positive"').classes('h-14 w-16')
                    with ui.tooltip():
                        ui.label('Додати новий запис вручну')
            # Рядок фільтрів 1
            with ui.row().classes('w-full max-w-7xl items-center gap-4 mt-2'):
                des_year_filter = ui.select(options=des_year_options, multiple=True, label='Рік СЗЧ',
                                            on_change=on_year_change).classes('w-48').props(
                    'use-chips stack-label clearable')
                des_date_from = ui.input('СЗЧ з (дата)', on_change=on_date_change).props('type=date clearable').classes(
                    'w-40')
                des_date_to = ui.input('СЗЧ до (дата)', on_change=on_date_change).props('type=date clearable').classes(
                    'w-40')

                # Замінюємо lambda на посилання handle_filter_change
                ins_year_filter = ui.select(options=ins_year_options, multiple=True, label=COLUMN_INSERT_DATE,
                                            on_change=handle_filter_change).classes('w-48').props(
                    'use-chips stack-label clearable')

            # Рядок фільтрів 2
            with ui.row().classes('w-full max-w-7xl items-center gap-4 mt-2'):
                title2_filter = ui.select(options=title2_options, label=COLUMN_TITLE_2, value='Всі',
                                          on_change=handle_filter_change).classes('flex-grow')
                service_filter = ui.select(options=service_options, label=COLUMN_SERVICE_TYPE, value='Всі',
                                           on_change=handle_filter_change).classes('flex-grow')

        results_container = ui.column().classes('w-full items-center mt-6')