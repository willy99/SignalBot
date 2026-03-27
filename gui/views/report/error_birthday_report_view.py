from dics.deserter_xls_dic import COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_INCREMENTAL, COLUMN_BIRTHDAY, MIL_UNITS, COLUMN_INSERT_DATE
from domain.person_filter import PersonSearchFilter
from gui.controllers.report_controller import ReportController
from gui.controllers.person_controller import PersonController  # Додав імпорт
from gui.services.request_context import RequestContext
from domain.person import Person  # Імпорт моделі
from nicegui import ui, run
from datetime import datetime


def render_inn_mismatch_page(report_ctrl: ReportController, person_ctrl: PersonController, ctx: RequestContext):
    # Стейт для зберігання чернеток виправлень
    pending_updates = {}

    # Отримуємо опції для років
    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])
    # Сортуємо роки за спаданням для зручності
    year_options = sorted([str(y) for y in year_options], reverse=True)

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Звіт: Невідповідність ІПН та дати народження').classes('text-h4 mb-2')

        # --- БЛОК ФІЛЬТРІВ ---
        with ui.card().classes('w-full max-w-5xl p-4 mb-4 shadow-md bg-blue-50'):
            with ui.row().classes('w-full items-center justify-center gap-6'):
                unit_select = ui.select(
                    options=MIL_UNITS,
                    value=MIL_UNITS[0],
                    label='Військова частина'
                ).classes('w-48').props('outlined dense bg-white')

                year_select = ui.select(
                    options=['Всі роки'] + year_options,
                    value='Всі роки',
                    label='Рік запису'
                ).classes('w-48').props('outlined dense bg-white')

                generate_btn = ui.button('Знайти помилки', icon='rule', color='teal').props('elevated size=lg').classes('mb-4')

                save_all_btn = ui.button('ЗБЕРЕГТИ ЗМІНИ', icon='cloud_upload', color='orange', on_click=lambda: save_changes()).props('elevated size=lg').classes('hidden mb-4')

        results_container = ui.column().classes('w-full items-center mt-2')

    async def save_changes():
        """Відправляє накопичені зміни в базу"""
        if not pending_updates:
            return

        save_all_btn.disable()
        persons_to_update = []

        for p_id, b_date_str in pending_updates.items():
            # Парсимо рядок назад у об'єкт date для моделі
            dt_obj = datetime.strptime(b_date_str, '%d.%m.%Y').date()
            persons_to_update.append(Person(id=p_id, mil_unit=unit_select.value, birthday=dt_obj))

        try:
            # Викликаємо ваш метод збереження
            success = await run.io_bound(
                person_ctrl.save_persons,
                ctx,
                persons_to_update,
                partial_update=True
            )

            if success:
                ui.notify(f'Успішно оновлено {len(persons_to_update)} записів!', type='positive')
                pending_updates.clear()
                save_all_btn.set_visibility(False)
                await generate_report()  # Перезапускаємо звіт, щоб прибрати виправлені рядки
            else:
                ui.notify('Помилка при збереженні в базу', type='negative')
        except Exception as e:
            ui.notify(f'Критична помилка: {e}', type='negative')
        finally:
            save_all_btn.enable()

    def add_to_updates(table, row):
        """Додає запис у чернетку виправлень"""
        p_id = row['id']
        pending_updates[p_id] = row['expected_birthday']

        for r in table.rows:
            if r['id'] == p_id:
                r['is_fixed'] = True
                break

        save_all_btn.set_visibility(True)
        ui.notify(f"Додано до виправлення: {row['name']}", type='info')
        table.update()

    async def generate_report():
        generate_btn.disable()
        results_container.clear()
        pending_updates.clear()
        save_all_btn.set_visibility(False)

        # Збираємо значення фільтрів
        selected_unit = None if unit_select.value == 'Всі підрозділи' else unit_select.value
        selected_year = None if year_select.value == 'Всі роки' else year_select.value

        with results_container:
            ui.spinner(size='lg').classes('mt-10')

        try:
            # Передаємо фільтри в контролер (переконайтеся, що метод їх приймає)
            search_filter = PersonSearchFilter(mil_unit=selected_unit, ins_year=selected_year)
            mismatches = await run.io_bound(
                report_ctrl.get_error_birthday_report,
                ctx,
                search_filter
            )
            results_container.clear()

            if not mismatches:
                with results_container:
                    ui.icon('verified', color='green', size='4rem')
                    ui.label('Невідповідностей не знайдено за вказаними фільтрами.').classes('text-xl text-green-700 mt-2')
                return

            for m in mismatches:
                m['is_fixed'] = False

            with results_container:
                ui.label(f'Знайдено помилок: {len(mismatches)}').classes('font-bold text-xl mb-4 text-red-800')

                columns = [
                    {'name': 'id', 'label': COLUMN_INCREMENTAL, 'field': 'id', 'align': 'left'},
                    {'name': 'name', 'label': COLUMN_NAME, 'field': 'name', 'align': 'left'},
                    {'name': 'id_number', 'label': COLUMN_ID_NUMBER, 'field': 'id_number', 'align': 'left'},
                    {'name': 'actual_birthday', 'label': 'Дата в базі', 'field': 'actual_birthday', 'align': 'center'},
                    {'name': 'expected_birthday', 'label': 'Має бути', 'field': 'expected_birthday', 'align': 'center'},
                    {'name': 'actions', 'label': 'Дія', 'field': 'actions', 'align': 'center'},
                ]

                table = ui.table(columns=columns, rows=mismatches, row_key='id').classes('w-full max-w-7xl shadow-lg')
                table.props('bordered flat separator=cell')

                table.add_slot('body', '''
                        <q-tr :props="props">
                            <q-td key="id" :props="props">{{ props.row.id }}</q-td>
                            <q-td key="name" :props="props" class="font-bold text-blue-900">{{ props.row.name }}</q-td>
                            <q-td key="id_number" :props="props" class="font-mono text-weight-bold">{{ props.row.id_number }}</q-td>
                            <q-td key="actual_birthday" :props="props" :class="props.row.is_fixed ? 'text-grey' : 'text-red-700 bg-red-50'">
                                {{ props.row.actual_birthday }}
                            </q-td>
                            <q-td key="expected_birthday" :props="props" class="text-green-900 bg-green-50 font-bold">
                                {{ props.row.expected_birthday }}
                            </q-td>
                            <q-td key="actions" :props="props">
                                <q-btn v-if="!props.row.is_fixed" 
                                       flat round icon="auto_fix_high" color="primary" 
                                       @click="() => $parent.$emit('fix', props.row)">
                                    <q-tooltip>Виправити дату</q-tooltip>
                                </q-btn>
                                <q-icon v-else name="check_circle" color="green" size="md"></q-icon>
                            </q-td>
                        </q-tr>
                    ''')

                table.on('fix', lambda e: add_to_updates(table, e.args))

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка: {e}', type='negative')
        finally:
            generate_btn.enable()

    generate_btn.on('click', generate_report)