from nicegui import ui
from gui.services.request_context import RequestContext
from service.constants import DOC_STATUS_COMPLETED, DOC_STATUS_DRAFT, DOC_PACKAGE_STANDART


def render_drafts_list_page(controller, ctx: RequestContext):
    ui.label('Список пакетів супроводів').classes('w-full text-center text-3xl font-bold mb-8')

    # Отримуємо дані з БД
    drafts = controller.get_all_drafts(ctx)

    # 1. Формуємо рядки для таблиці
    rows = []
    for d in drafts:
        rows.append({
            'id': d.get('id'),
            'support_number': d.get('support_number') or '—',
            'support_date': d.get('support_date') or '—',
            'city': d.get('city', '—'),
            'people_count': len(d.get('payload', [])),
            'created_date': d.get('created_date', '—'),
            'created_by': d.get('created_by', '—'),
            'status': d.get('status', '—'),
            'package_type': d.get('package_type', '—')
        })

    # 2. Визначаємо колонки
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
        {'name': 'package_type', 'label': 'Тип', 'field': 'package_type', 'align': 'center', 'sortable': True},
        {'name': 'support_number', 'label': 'Номер супроводу', 'field': 'support_number', 'align': 'left','sortable': True},
        {'name': 'support_date', 'label': 'Дата формування', 'field': 'support_date', 'align': 'left', 'sortable': True},
        {'name': 'city', 'label': 'Місто', 'field': 'city', 'align': 'left', 'sortable': True},
        {'name': 'people_count', 'label': 'Кількість у пакеті', 'field': 'people_count', 'align': 'center','sortable': True},
        {'name': 'created_date', 'label': 'Дата створення', 'field': 'created_date', 'align': 'left', 'sortable': True},
        {'name': 'created_by', 'label': 'Ким створено', 'field': 'created_by', 'align': 'left', 'sortable': True},
        {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'left', 'sortable': True},
        {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
    ]

    with ui.column().classes('w-full items-center'):

        with ui.row().classes('w-full max-w-7xl justify-end mb-4 gap-4'):
            ui.button('Новий Зведений (Стандарт)', icon='add',
                      on_click=lambda: ui.navigate.to('/doc_support/s_create')
                      ).props('color="primary"')
            ui.button('Новий Детальний (По документах)', icon='add_circle',
                      on_click=lambda: ui.navigate.to('/doc_support/d_create')
                      ).props('color="secondary" outline')

        if not rows:
            ui.label('Пакету супроводів не знайдено').classes('text-center text-gray-400 mt-10 text-lg')
            return

        # 3. Створюємо таблицю
        table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full max-w-8xl general-table')
        table.props('flat bordered separator=cell')

        # 4. Кастомний слот для кнопок "Редагувати" та "Видалити"
        table.add_slot('body-cell-actions', '''
                    <q-td :props="props" class="gap-2">
                        <q-btn flat dense color="primary" icon="edit" @click="$parent.$emit('edit', props.row)">
                            <q-tooltip>Редагувати</q-tooltip>
                        </q-btn>
                        <q-btn flat dense color="negative" icon="delete" @click="$parent.$emit('delete', props.row.id)">
                            <q-tooltip>Видалити</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')
        table.add_slot('body-cell-status', '''
                    <q-td :props="props">
                        <q-badge :color="props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'green' : 'grey'" class="text-bold q-pa-sm">
                            {{ props.row.status }}
                        </q-badge>
                    </q-td>
                ''')

        table.add_slot('body-cell-package_type', '''
                            <q-td :props="props">
                                <q-badge :color="props.row.package_type === \'''' + DOC_PACKAGE_STANDART + '''\' ? 'blue' : 'purple'" class="text-bold q-pa-sm" outline>
                                    {{ props.row.package_type === \'''' + DOC_PACKAGE_STANDART + '''\' ? 'Стандарт' : 'Детальний' }}
                                </q-badge>
                            </q-td>
                        ''')

        def on_edit(e):
            row_data = e.args
            draft_id = row_data['id']
            p_type = row_data.get('package_type')

            if p_type == DOC_PACKAGE_STANDART:
                ui.navigate.to(f'/doc_support/s_edit/{draft_id}')
            else:
                ui.navigate.to(f'/doc_support/d_edit/{draft_id}')

        async def on_delete(e):
            draft_id = e.args

            dialog = ui.dialog()
            with dialog, ui.card().classes('p-6 min-w-[300px]'):
                ui.label('Увага!').classes('text-xl font-bold text-red-600 mb-2')
                ui.label(f'Ви дійсно хочете видалити пакет №{draft_id}?').classes('text-gray-600 mb-6')

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                    ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

            result = await dialog
            if result:
                controller.delete_draft(ctx, draft_id)
                table.rows = [row for row in table.rows if row['id'] != draft_id]
                table.update()
                ui.notify(f'Пакет супроводів №{draft_id} видалено', type='negative')

        # Прив'язуємо події з Vue/Quasar до наших Python функцій
        table.on('edit', on_edit)
        table.on('delete', on_delete)