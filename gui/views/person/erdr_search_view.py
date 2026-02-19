from nicegui import ui
from dics.deserter_xls_dic import *
from gui.model.person import Person
from gui.views.person.person_view import edit_erdr
from gui.views.components import menu

@ui.refreshable
def results_ui(data, person_ctrl):
    if not data:
        return

    columns = [
        {'name': 'pib', 'label': COLUMN_NAME, 'field': 'pib', 'align': 'left'},
        {'name': 'rnokpp', 'label': COLUMN_ID_NUMBER, 'field': 'rnokpp'},
        {'name': 'o_ass_num', 'label': COLUMN_ORDER_ASSIGNMENT_NUMBER, 'field': 'o_ass_num'},
        {'name': 'o_ass_date', 'label': COLUMN_ORDER_ASSIGNMENT_DATE, 'field': 'o_ass_date'},
        {'name': 'action', 'label': 'Дія', 'field': 'action'},
    ]

    rows = []
    for person in data:
        # Важливо: використовуємо модель для відображення
        rows.append({
            'pib': person.name,
            'rnokpp': person.rnokpp,
            'o_ass_num': person.o_ass_num,
            'o_ass_date': person.o_ass_date,
            'raw_model': person.model_dump()
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
    table.on('edit', lambda msg: edit_erdr(
        Person(**msg.args),
        person_ctrl,
        # Після закриття форми ми просто освіжаємо ЦЮ Ж функцію
        on_close=lambda: results_ui.refresh(person_ctrl.search_by_erdr(last_query['o_ass_num'], last_query['name']), person_ctrl)
    ))


# Глобальна змінна для збереження останнього пошуку (щоб знати, що оновлювати)
last_query = {}


def search_page(person_ctrl):
    global last_query
    menu()

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Пошук військовослужбовців').classes('text-h4 mb-4')

        with ui.row().classes('w-full max-w-4xl items-center gap-4'):

            o_ass_num_search_field = ui.input(label=COLUMN_ORDER_ASSIGNMENT_NUMBER) \
                .classes('flex-grow') \
                .props('autofocus')

            name_search_field = ui.input(label='Введіть дані (ПІБ або РНОКПП)') \
                .classes('flex-grow') \
                .props('autofocus')

            # Додаємо пошук по Enter
            o_ass_num_search_field.on('keydown.enter', lambda: do_search())
            name_search_field.on('keydown.enter', lambda: do_search())
            ui.button(icon='search', on_click=lambda: do_search()).props('elevated')

        # 2. Контейнер, який буде порожнім до моменту пошуку
        results_container = ui.column().classes('w-full items-center mt-6')
    o_ass_num_search_field.run_method('focus')

    async def do_search():
        global last_query
        o_ass_num = o_ass_num_search_field.value.strip()
        name = name_search_field.value.strip()

        if not o_ass_num and not name:
            ui.notify('Введіть запит для пошуку', type='warning')
            return

        last_query['o_ass_num'] = o_ass_num
        last_query['name'] = name

        with results_container:
            ui.spinner(size='lg').classes('mt-10')
            ui.label('Пошук у базі даних...').classes('text-grey')

        try:
            from nicegui import run
            data = await run.io_bound(person_ctrl.search_by_erdr, o_ass_num, name)

            results_container.clear()

            if not data:
                ui.notify('Нічого не знайдено', type='negative')
                return

            if len(data) == 1:
                edit_erdr(data[0], person_ctrl, on_close=lambda: do_search())

            with results_container:
                results_ui(data, person_ctrl)

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка пошуку: {e}', type='negative')
