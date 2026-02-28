from nicegui import ui, run
from gui.services.request_context import RequestContext

def render_duplicates_report_page(report_ctrl, ctx: RequestContext):

    with ui.column().classes('w-full items-center p-4'):
        ui.label('Звіт: Співпадіння ПІБ (Різні ІПН)').classes('text-h4 mb-2')
        ui.label(
            'Цей звіт шукає в базі військовослужбовців з однаковим ПІБ, але різними ідентифікаційними номерами, що може свідчити про помилки вводу або дублікати.').classes(
            'text-grey-6 text-center max-w-3xl mb-6')

        generate_btn = ui.button('Сформувати звіт', icon='manage_search', color='blue').props('elevated size=lg')

        results_container = ui.column().classes('w-full items-center mt-6')

    async def generate_report():
        generate_btn.disable()
        results_container.clear()

        with results_container:
            ui.spinner(size='lg').classes('mt-10')
            ui.label('Аналіз бази даних (може зайняти кілька секунд)...').classes('text-grey')

        try:
            duplicates_data = await run.io_bound(report_ctrl.get_dupp_names_report, ctx)

            results_container.clear()

            if not duplicates_data:
                with results_container:
                    ui.icon('check_circle', color='green', size='4rem')
                    ui.label('Ідеально! Проблемних дублікатів не знайдено.').classes('text-xl text-green-700 mt-2')
                return

            rows = []
            bg_class_toggle = False

            for name, records in sorted(duplicates_data.items()):
                bg_color = 'bg-blue-50' if bg_class_toggle else 'bg-white'
                bg_class_toggle = not bg_class_toggle

                for idx, rec in enumerate(records):
                    birth = rec.get('birthday')
                    des = rec.get('des_date')
                    birth_str = birth.strftime('%d.%m.%Y') if hasattr(birth, 'strftime') else str(birth or '')
                    des_str = des.strftime('%d.%m.%Y') if hasattr(des, 'strftime') else str(des or '')

                    rows.append({
                        'name': name if idx == 0 else '',  # Показуємо ім'я тільки в першому рядку групи
                        'id_number': rec.get('id_number', ''),
                        'birthday': birth_str,
                        'des_date': des_str,
                        'bg_color': bg_color  # Зберігаємо колір у даних рядка
                    })

            with results_container:
                ui.label(f'Знайдено осіб з розбіжностями ідентифікаційних номерів: {len(duplicates_data)}').classes(
                    'font-bold text-xl mb-4 text-red-800')

                columns = [
                    {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left'},
                    {'name': 'id_number', 'label': 'ІПН / РНОКПП', 'field': 'id_number', 'align': 'left'},
                    {'name': 'birthday', 'label': 'Дата народження', 'field': 'birthday', 'align': 'center'},
                    {'name': 'des_date', 'label': 'Дата СЗЧ', 'field': 'des_date', 'align': 'center'},
                ]

                table = ui.table(columns=columns, rows=rows, row_key='id_number').classes('w-full max-w-5xl general-table')
                table.props('bordered flat separator=cell')

                table.add_slot('body', '''
                    <q-tr :props="props" :class="props.row.bg_color">
                        <q-td key="name" :props="props" :class="props.row.name ? 'font-bold text-subtitle2 text-blue-900' : ''">
                            {{ props.row.name }}
                        </q-td>

                        <q-td key="id_number" :props="props" class="text-red-800 font-mono font-bold">
                            {{ props.row.id_number || 'ПУСТЕ ПОЛЕ' }}
                        </q-td>

                        <q-td key="birthday" :props="props">
                            {{ props.row.birthday }}
                        </q-td>
                        <q-td key="des_date" :props="props">
                            {{ props.row.des_date }}
                        </q-td>
                    </q-tr>
                ''')

        except Exception as e:
            results_container.clear()
            ui.notify(f'Помилка генерації звіту: {e}', type='negative')
            print(f"Помилка дублікатів: {e}")
        finally:
            generate_btn.enable()

    generate_btn.on('click', generate_report)