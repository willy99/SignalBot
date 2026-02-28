from nicegui import ui
from gui.services.request_context import RequestContext


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
        })

    # 2. Визначаємо колонки
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
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
        with ui.row().classes('w-full max-w-6xl justify-end mb-4'):
            ui.button('Створити новий пакет супроводів', icon='add',
                      on_click=lambda: ui.navigate.to('/doc_support/create')
                      ).props('color="primary"')

        if not rows:
            ui.label('Пакету супроводів не знайдено').classes('text-center text-gray-400 mt-10 text-lg')
            return

        # 3. Створюємо таблицю
        table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full max-w-7xl general-table')
        table.props('flat bordered separator=cell')

        # 4. Кастомний слот для кнопок "Редагувати" та "Видалити"
        table.add_slot('body-cell-actions', '''
            <q-td :props="props" class="gap-2">
                <q-btn flat dense color="primary" icon="edit" @click="$parent.$emit('edit', props.row.id)">
                    <q-tooltip>Редагувати</q-tooltip>
                </q-btn>
                <q-btn flat dense color="negative" icon="delete" @click="$parent.$emit('delete', props.row.id)">
                    <q-tooltip>Видалити</q-tooltip>
                </q-btn>
            </q-td>
        ''')
        table.add_slot('body-cell-status', '''
                    <q-td :props="props">
                        <q-badge :color="props.row.status === 'Completed' ? 'green' : 'grey'" class="text-bold q-pa-sm">
                            {{ props.row.status }}
                        </q-badge>
                    </q-td>
                ''')

        # 5. Обробники подій для таблиці
        def on_edit(e):
            draft_id = e.args
            ui.navigate.to(f'/doc_support/edit/{draft_id}')

        def on_delete(e):
            draft_id = e.args
            # Видаляємо з бази даних
            controller.delete_draft(ctx, draft_id)

            # Оновлюємо таблицю (залишаємо всі рядки, крім видаленого)
            table.rows = [row for row in table.rows if row['id'] != draft_id]
            table.update()

            ui.notify(f'Пакет супроводів №{draft_id} видалено', type='negative')

        # Прив'язуємо події з Vue/Quasar до наших Python функцій
        table.on('edit', on_edit)
        table.on('delete', on_delete)