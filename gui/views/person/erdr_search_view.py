from nicegui import ui
from dics.deserter_xls_dic import *
from domain.person import Person
from gui.views.person.person_view import edit_erdr
from domain.person_filter import PersonSearchFilter
from gui.services.request_context import RequestContext
from config import MAX_QUERY_RESULTS

@ui.refreshable
def results_ui(data, person_ctrl, ctx, refresh_callback):
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
        rows.append({
            'pib': person.name,
            'rnokpp': person.rnokpp,
            'o_ass_num': person.o_ass_num,
            'o_ass_date': person.o_ass_date,
            'raw_model': person.model_dump()
        })

    table = ui.table(columns=columns, rows=rows, row_key='rnokpp').classes('w-full max-w-5xl general-table')

    table.add_slot('body-cell-action', '''
        <q-td :props="props">
            <q-btn size="sm" color="primary" @click="$parent.$emit('edit', props.row.raw_model)">
                Редагувати
            </q-btn>
        </q-td>
    ''')

    table.on('edit', lambda msg: edit_erdr(
        Person(**msg.args),
        person_ctrl,
        ctx=ctx,
        on_close=refresh_callback
    ))


def search_page(person_ctrl, ctx: RequestContext):
    state = {
        'last_query': None, 'o_ass_num': None
    }

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Пошук військовослужбовців, Відправка справи на ДБР').classes('text-h4 mb-4')

        with ui.row().classes('w-full max-w-4xl items-center gap-4'):

            o_ass_num_search_field = ui.input(label=COLUMN_ORDER_ASSIGNMENT_NUMBER) \
                .classes('flex-grow') \
                .props('autofocus')

            name_search_field = ui.input(label='Введіть дані (ПІБ або РНОКПП)') \
                .classes('flex-grow') \
                .props('autofocus')

            o_ass_num_search_field.on('keydown.enter', lambda: do_search())
            name_search_field.on('keydown.enter', lambda: do_search())
            ui.button(icon='search', on_click=lambda: do_search()).props('elevated')

        results_container = ui.column().classes('w-full items-center mt-6')
    o_ass_num_search_field.run_method('focus')

    def do_search(auto_open=True):
        o_ass_num = o_ass_num_search_field.value.strip()
        name = name_search_field.value.strip()

        if not o_ass_num and not name:
            ui.notify('Введіть запит для пошуку', type='warning')
            return

        with results_container:
            ui.spinner(size='lg').classes('mt-10')
            ui.label('Пошук у базі даних...').classes('text-grey')

        try:
            state.update({
                'last_query': query, 'last_des_year': des_year_val, 'last_ins_year': ins_year_val,
                'last_des_from': date_from_val, 'last_des_to': date_to_val, 'last_title2': title2_val,
                'last_service': service_val
            })

            search_filter = PersonSearchFilter(
                query=name,
                o_ass_num=o_ass_num,
            )

            data = person_ctrl.search(ctx, search_filter)
            results_container.clear()


            if not data:
                ui.notify('Нічого не знайдено', type='negative')
                return

            refresh_cb = lambda: ui.timer(0, lambda: do_search(auto_open=False), once=True)
            if len(data) == 1 and auto_open:
                edit_erdr(data[0], person_ctrl, ctx=ctx, on_close=lambda: do_search(auto_open=False))
            if len(data) > MAX_QUERY_RESULTS:
                ui.notify(
                    f'⚠️ Знайдено занадто багато результатів ({len(data)}). Показано перші {MAX_QUERY_RESULTS}. Будь ласка, уточніть параметри пошуку',
                    type='warning',
                    timeout=8000
                )
                data = data[:MAX_QUERY_RESULTS]  # Відсікаємо все зайве
            with results_container:
                results_ui(data, person_ctrl, ctx, refresh_callback=refresh_cb)

            with results_container:
                results_ui(data, person_ctrl, ctx)

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка пошуку: {e}', type='negative')
