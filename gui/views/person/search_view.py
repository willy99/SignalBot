from nicegui import ui
from dics.deserter_xls_dic import COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_SUBUNIT, COLUMN_DESERTION_DATE, \
    COLUMN_RETURN_DATE, COLUMN_INSERT_DATE
from gui.model.person import Person
from gui.views.person.person_view import edit_person
from gui.components import menu

@ui.refreshable
def results_ui(data, person_ctrl):
    if not data:
        return

    columns = [
        {'name': 'pib', 'label': COLUMN_NAME, 'field': 'pib', 'align': 'left'},
        {'name': 'rnokpp', 'label': COLUMN_ID_NUMBER, 'field': 'rnokpp'},
        {'name': 'unit', 'label': COLUMN_SUBUNIT, 'field': 'unit'},
        {'name': 'desertion_date', 'label': COLUMN_DESERTION_DATE, 'field': 'desertion_date'},
        {'name': 'return_date', 'label': COLUMN_RETURN_DATE, 'field': 'return_date'},
        {'name': 'action', 'label': 'Дія', 'field': 'action'},
    ]

    rows = []
    for person in data:
        # Важливо: використовуємо модель для відображення
        rows.append({
            'pib': person.name,
            'rnokpp': person.rnokpp,
            'unit': person.subunit,
            'desertion_date': person.desertion_date,
            'return_date': person.return_date,
            'raw_model': person.model_dump()  # Словник для передачі в JS (Socket.io)
        })

    table = ui.table(columns=columns, rows=rows, row_key='rnokpp').classes('w-full max-w-5xl')

    # Слот для кнопки "Редагувати"
    table.add_slot('body-cell-action', '''
        <q-td :props="props">
            <q-btn size="sm" color="primary" @click="$parent.$emit('edit', props.row.raw_model)">
                Редагувати
            </q-btn>
        </q-td>
    ''')

    # Обробка натискання кнопки
    table.on('edit', lambda msg: edit_person(
        Person(**msg.args),
        person_ctrl,
        # Після закриття форми ми просто освіжаємо ЦЮ Ж функцію
        on_close=lambda: results_ui.refresh(person_ctrl.search_people(last_query['year'], last_query['query']), person_ctrl)
    ))


# Глобальна змінна для збереження останнього пошуку (щоб знати, що оновлювати)
last_query = {}


def search_page(person_ctrl):
    global last_query
    menu()

    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Пошук і редагування військовослужбовців').classes('text-h4 mb-4')

        with ui.row().classes('w-full max-w-4xl items-center gap-4'):

            year_filter = ui.select(
                options=year_options,
                multiple=True,
                label=COLUMN_INSERT_DATE
            ).classes('w-64').props('use-chips stack-label').on('update:model-value', lambda: do_search())

            search_field = ui.input(label='Введіть дані (ПІБ або РНОКПП)') \
                .classes('flex-grow') \
                .props('autofocus')

            # Додаємо пошук по Enter
            search_field.on('keydown.enter', lambda: do_search())
            ui.button(icon='search', on_click=lambda: do_search()).props('elevated')

        # 2. Контейнер, який буде порожнім до моменту пошуку
        results_container = ui.column().classes('w-full items-center mt-6')

    async def do_search():
        global last_query
        query = search_field.value.strip()
        selected_year = year_filter.value
        year_val = None if selected_year == 'Всі роки' or not selected_year else selected_year

        if not query:
            ui.notify('Введіть запит для пошуку', type='warning')
            return

        last_query['query'] = query
        last_query['year'] = year_val

        with results_container:
            ui.spinner(size='lg').classes('mt-10')  # Великий спіннер по центру
            ui.label('Пошук у базі даних...').classes('text-grey')

        try:
            # 2. Виконуємо важку операцію пошуку
            # Якщо пошук у Excel займає багато часу, краще обгорнути його в run.io_bound
            from nicegui import run
            data = await run.io_bound(person_ctrl.search_people, year_val, query)

            # 3. Очищуємо спіннер після отримання даних
            results_container.clear()

            if not data:
                ui.notify('Нічого не знайдено', type='negative')
                return

            # Якщо один результат - відкриваємо відразу
            if len(data) == 1:
                edit_person(data[0], person_ctrl, on_close=lambda: do_search())

            # 4. Малюємо таблицю з результатами
            with results_container:
                results_ui(data, person_ctrl)

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка пошуку: {e}', type='negative')
