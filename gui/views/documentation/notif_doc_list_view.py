from nicegui import ui
from gui.services.request_context import RequestContext
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED

def render_notif_drafts_list_page(notif_ctrl, ctx: RequestContext):
    ui.label('Список пакетів для відправки на ДБР').classes('w-full text-center text-3xl font-bold mb-8')

    try:
        drafts = notif_ctrl.get_all_drafts(ctx)
    except Exception as e:
        ui.notify(f'Помилка отримання даних: {e}', type='negative')
        drafts = []

    # 1. Формуємо рядки для таблиці
    rows = []
    for d in drafts:
        # Безпечно отримуємо список людей (може бути порожнім, якщо JSON не розпарсився)
        payload = d.get('payload') or []


        rows.append({
            'id': d.get('id'),
            'out_number': d.get('out_number') or '—',
            'out_date': d.get('out_date') or '—',
            'people_count': len(payload),
            'created_date': d.get('created_date', '—')[:16],  # Відрізаємо секунди для краси
            'status': d.get('status', DOC_STATUS_DRAFT),
        })

    # 2. Визначаємо колонки
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'center', 'sortable': True},
        {'name': 'out_number', 'label': 'Вихідний номер', 'field': 'out_number', 'align': 'left', 'sortable': True},
        {'name': 'out_date', 'label': 'Дата відправки', 'field': 'out_date', 'align': 'left', 'sortable': True},
        {'name': 'people_count', 'label': 'Осіб у пакеті', 'field': 'people_count', 'align': 'center',
         'sortable': True},
        {'name': 'created_date', 'label': 'Створено', 'field': 'created_date', 'align': 'left', 'sortable': True},
        {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center', 'sortable': True},
        {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
    ]

    with ui.column().classes('w-full items-center'):
        with ui.row().classes('w-full max-w-6xl justify-end mb-4'):
            ui.button('Створити новий пакет на ДБР', icon='add',
                      on_click=lambda: ui.navigate.to('/doc_notif/create')
                      ).props('color="primary"')

        if not rows:
            ui.label('Чернеток не знайдено. Створіть новий пакет.').classes('text-center text-gray-500 mt-10 text-lg')
            return

        # 3. Створюємо таблицю
        table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full max-w-6xl shadow-md')
        table.props('flat bordered separator=horizontal row-key="id"')

        # 4. Кастомний слот для статусів
        table.add_slot('body-cell-status', '''
            <q-td :props="props">
                <q-badge :color="props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'green' : 'orange'" class="text-bold q-pa-sm">
                    {{ props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'Відправлено' : 'Чернетка' }}
                </q-badge>
            </q-td>
        ''')

        # 5. Кастомний слот для кнопок "Редагувати" та "Видалити"
        table.add_slot('body-cell-actions', '''
            <q-td :props="props" class="gap-2">
                <q-btn flat dense color="primary" icon="edit" @click="$parent.$emit('edit', props.row.id)">
                    <q-tooltip>Відкрити / Редагувати</q-tooltip>
                </q-btn>
                <q-btn flat dense color="negative" icon="delete" @click="$parent.$emit('delete', props.row.id)">
                    <q-tooltip>Видалити пакет</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        # 6. Обробники подій
        def on_edit(e):
            draft_id = e.args
            ui.navigate.to(f'/doc_notif/edit/{draft_id}')

        async def on_delete(e):
            draft_id = e.args

            # Асинхронний діалог підтвердження
            dialog = ui.dialog()
            with dialog, ui.card().classes('p-6 min-w-[300px]'):
                ui.label('Увага!').classes('text-xl font-bold text-red-600 mb-2')
                ui.label(f'Ви дійсно хочете видалити пакет №{draft_id}?').classes('text-gray-600 mb-6')

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                    ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

            result = await dialog

            if result:
                try:
                    notif_ctrl.delete_doc(ctx, draft_id)

                    table.rows = [row for row in table.rows if row['id'] != draft_id]
                    table.update()

                    ui.notify(f'Пакет №{draft_id} успішно видалено', type='info')
                except Exception as ex:
                    ui.notify(f'Помилка видалення: {ex}', type='negative')

        table.on('edit', on_edit)
        table.on('delete', on_delete)