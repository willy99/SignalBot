from nicegui import ui, run
from dics.deserter_xls_dic import COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_SUBUNIT, COLUMN_DESERTION_DATE, \
    COLUMN_RETURN_DATE, COLUMN_INSERT_DATE
from gui.model.person import Person
from gui.views.person.person_view import edit_person
from gui.views.components import menu

last_query = {}

def search_page(report_ctrl, person_ctrl):
    global last_query
    menu()

    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Звіт Додаток №2').classes('text-h4 mb-4')

        with ui.row().classes('w-full max-w-4xl items-center gap-4'):

            year_filter = ui.select(
                options=year_options,
                multiple=True,
                label=COLUMN_INSERT_DATE
            ).classes('w-64').props('use-chips stack-label').on('update:model-value', lambda: do_report())

            # Додаємо пошук по Enter
            ui.button(icon='search', on_click=lambda: do_report()).props('elevated')

        results_container = ui.column().classes('w-full items-center mt-6')


    async def do_report():
        global last_query
        selected_year = year_filter.value
        year_val = None if selected_year == 'Всі роки' or not selected_year else selected_year

        if not year_val:
            ui.notify('Введіть рік для репорту', type='warning')
            return

        last_query['year'] = year_val

        with results_container:
            ui.spinner(size='lg').classes('mt-10')
            ui.label('Компайлінг звіту...').classes('text-grey')

        try:
            data = await run.io_bound(report_ctrl.do_subunit_desertion_report,year_val)

            # 3. Очищуємо спіннер після отримання даних
            results_container.clear()

            if not data:
                ui.notify('Нічого не скомпілілося. А чого?', type='negative')
                return

            # 4. Малюємо таблицю з результатами
            with results_container:
                results_ui(data, report_ctrl)

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка пошуку: {e}', type='negative')


def results_ui(data, report_ctrl):
    if not data:
        ui.label('Дані відсутні').classes('text-grey')
        return

    rows = []

    # 1. Створюємо об'єкт для глобального підсумку (Разом по всій частині)
    grand_total = {
        'main': 'РАЗОМ ПО ЧАСТИНІ',
        'sub': '',
        's_under': 0, 'o_under': 0, 's_over': 0, 'o_over': 0, 's_ret_mu': 0, 's_ret_res': 0, 'o_ret': 0,
        'is_grand_total': True  # Спеціальний прапорець для стилізації
    }

    # Сортуємо ключі для стабільного виведення
    for main_unit in sorted(data.keys()):
        sub_units_data = data[main_unit]

        # Спочатку рахуємо суму для всього основного підрозділу
        unit_total = {
            'main': main_unit,
            'sub': 'ВСЬОГО',  # Мітка для ідентифікації підсумкового рядка
            's_under': 0, 'o_under': 0, 's_over': 0, 'o_over': 0, 's_ret_mu': 0, 's_ret_res': 0, 'o_ret': 0,
            'is_total': True  # Прапорець для стилізації
        }

        temp_sub_rows = []
        for sub_unit, stats in sub_units_data.items():
            s_under = stats['рядовий_сержант']['under_3']
            s_over = stats['рядовий_сержант']['over_3']
            o_under = stats['офіцер']['under_3']
            o_over = stats['офіцер']['over_3']
            s_ret_mu = stats['рядовий_сержант']['ret_mu']
            s_ret_res = stats['рядовий_сержант']['ret_res']
            o_ret_mu = stats['офіцер']['ret_mu']

            # Додаємо до підсумку підрозділу
            unit_total['s_under'] += s_under
            unit_total['s_over'] += s_over
            unit_total['o_under'] += o_under
            unit_total['o_over'] += o_over
            unit_total['s_ret_mu'] += s_ret_mu
            unit_total['s_ret_res'] += s_ret_res
            unit_total['o_ret'] += o_ret_mu

            # Додаємо до ГЛОБАЛЬНОГО підсумку
            grand_total['s_under'] += s_under
            grand_total['s_over'] += s_over
            grand_total['o_under'] += o_under
            grand_total['o_over'] += o_over
            grand_total['s_ret_mu'] += s_ret_mu
            grand_total['s_ret_res'] += s_ret_res
            grand_total['o_ret'] += o_ret_mu

            temp_sub_rows.append({
                'main': '',  # Порожньо, щоб не дублювати назву
                'sub': sub_unit,
                's_under': s_under,
                'o_under': o_under,
                's_over': s_over,
                'o_over': o_over,
                's_ret_mu': s_ret_mu,
                's_ret_res': s_ret_res,
                'o_ret': o_ret_mu,
                'is_total': False
            })

        # Рахуємо фінальні суми для підсумкового рядка
        unit_total['s_total'] = unit_total['s_under'] + unit_total['s_over']
        unit_total['o_total'] = unit_total['o_under'] + unit_total['o_over']
        unit_total['s_total_ret'] = unit_total['s_ret_mu'] + unit_total['s_ret_res']

        # Додаємо в загальний список: спочатку підсумок підрозділу, потім деталізацію
        # Додаємо підрозділ у загальний список
        rows.append(unit_total)
        rows.extend(temp_sub_rows)

    # 3. Рахуємо фінальні суми для ГЛОБАЛЬНОГО підсумку
    grand_total['s_total'] = grand_total['s_under'] + grand_total['s_over']
    grand_total['o_total'] = grand_total['o_under'] + grand_total['o_over']
    grand_total['s_total_ret'] = grand_total['s_ret_mu'] + grand_total['s_ret_res']

    # ВСТАВЛЯЄМО ГЛОБАЛЬНИЙ ПІДСУМОК НА ПОЧАТОК
    rows.insert(0, grand_total)

    # Визначення колонок (залишається майже таким самим)
    columns = [
        {'name': 'main', 'label': 'Підрозділ', 'field': 'main', 'align': 'left'},
        {'name': 'sub', 'label': 'Саб-підрозділ', 'field': 'sub', 'align': 'left'},
        {'name': 's_under', 'label': '< 3 (С/С)', 'field': 's_under'},
        {'name': 'o_under', 'label': '< 3 (Офіц.)', 'field': 'o_under'},
        {'name': 's_over', 'label': '>= 3 (С/С)', 'field': 's_over'},
        {'name': 'o_over', 'label': '>= 3 (Офіц.)', 'field': 'o_over'},

        {'name': 's_total', 'label': 'Всього (С/С)', 'field': 's_total', 'header_classes': 'bg-blue-100'},
        {'name': 'o_total', 'label': 'Всього (Офіц.)', 'field': 'o_total', 'header_classes': 'bg-blue-100'},
        {'name': 's_ret_mu', 'label': 'У В/Ч (С/С)', 'field': 's_ret_mu'},
        {'name': 's_ret_res', 'label': 'У Рез (С/С)', 'field': 's_ret_res'},
        {'name': 's_total_ret', 'label': 'Всього (С/С)', 'field': 's_total_ret', 'header_classes': 'bg-blue-100'},
        {'name': 'o_ret', 'label': 'У В/Ч (Офіц.)', 'field': 'o_ret'},
    ]

    table = ui.table(columns=columns, rows=rows, row_key='index').classes('w-full')

    # Додаємо складний хедер (як у минулому кроці)
    table.add_slot('header', '''
            <q-tr>
                <q-th colspan="2" class="text-center">Підрозділи</q-th>
                <q-th colspan="4" class="text-center bg-grey-2">Випадки СЗЧ</q-th>
                <q-th colspan="2" class="text-center bg-blue-2 text-bold">Разом</q-th>
                <q-th colspan="4" class="text-center bg-grey-2">Повернення</q-th>
            </q-tr>
            <q-tr>
                <q-th v-for="col in props.cols" :key="col.name" :props="props" :class="col.header_classes">
                    {{ col.label }}
                </q-th>
            </q-tr>
        ''')

    # КАСТОМНЕ ВІДОБРАЖЕННЯ РЯДКІВ (Стилізація підсумків)
    table.add_slot('body', '''
            <q-tr :props="props" :class="props.row.is_grand_total ? 'bg-orange-100 font-bold' : (props.row.is_total ? 'bg-blue-50 font-bold' : '')">
                <q-td v-for="col in props.cols" :key="col.name" :props="props" 
                    :class="(col.name === 's_total' || col.name === 'o_total' || col.name === 's_total_ret') ? 'bg-blue-100' : ''">

                    <template v-if="col.name === 'sub' && props.row.is_total">
                        <q-badge color="primary">Підсумок</q-badge>
                    </template>
                    <template v-else-if="col.name === 'main' && props.row.is_grand_total">
                        <q-icon name="star" color="orange" /> {{ col.value }}
                    </template>
                    <template v-else>
                        {{ col.value }}
                    </template>

                </q-td>
            </q-tr>
        ''')