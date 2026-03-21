from nicegui import ui, run

from gui.controllers.dbr_controller import DbrController
from gui.services.request_context import RequestContext
from service.constants import DOC_STATUS_DRAFT, DOC_STATUS_COMPLETED
from datetime import datetime
from gui.tools.ui_components import date_input, fix_date
from domain.document_filter import DocumentFilter  # 💡 Імпортуємо наш новий фільтр


def render_dbr_drafts_list_page(dbr_ctrl: DbrController, ctx: RequestContext):
    ui.label('Список пакетів для відправки на ДБР').classes('w-full text-center text-3xl font-bold mb-8')

    # Стан фільтрів на UI
    filter_state = {
        'date_from': '',
        'date_to': '',
        'out_number': '',
        'status': 'Всі'
    }

    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'center', 'sortable': True},
        {'name': 'out_number', 'label': 'Вихідний номер', 'field': 'out_number', 'align': 'left', 'sortable': True},
        {'name': 'out_date', 'label': 'Дата відправки', 'field': 'out_date', 'align': 'left', 'sortable': True},
        {'name': 'people_count', 'label': 'Осіб у пакеті', 'field': 'people_count', 'align': 'center', 'sortable': True},
        {'name': 'created_date', 'label': 'Створено', 'field': 'created_date', 'align': 'left', 'sortable': True},
        {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center', 'sortable': True},
        {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
    ]

    with ui.column().classes('w-full items-center'):
        with ui.row().classes('w-full max-w-6xl justify-between items-center mb-4 gap-4 flex-nowrap'):

            # ==========================================
            # БЛОК ФІЛЬТРІВ (Збирає дані для бекенду)
            # ==========================================
            with ui.row().classes('items-center gap-3 bg-white p-2 rounded-lg border shadow-sm flex-grow'):
                ui.icon('filter_alt', size='sm').classes('text-gray-400 ml-2')

                date_input('Створено з', filter_state, 'date_from', blur_handler=fix_date).classes('w-28')
                date_input('По', filter_state, 'date_to', blur_handler=fix_date).classes('w-28')

                ui.input('Вихідний номер').bind_value(filter_state, 'out_number').classes('w-32').props('dense outlined clearable')

                status_options = {'Всі': 'Всі', DOC_STATUS_DRAFT: 'Чернетка', DOC_STATUS_COMPLETED: 'Відправлено'}
                ui.select(status_options, label='Статус').bind_value(filter_state, 'status').classes('w-36').props('dense outlined')

                # 💡 Асинхронна функція, яка смикає БД
                async def apply_filters():
                    search_btn.props('loading')
                    try:
                        # 1. Пакуємо дані з UI у наш Dataclass
                        doc_filter = DocumentFilter(
                            date_from=filter_state['date_from'] or None,
                            date_to=filter_state['date_to'] or None,
                            out_number=filter_state['out_number'].strip() if filter_state['out_number'] else None,
                            status=filter_state['status'] if filter_state['status'] != 'Всі' else None
                        )

                        # 2. Викликаємо контролер (виконується в окремому потоці, щоб не блокувати UI)
                        drafts = await run.io_bound(dbr_ctrl.search_drafts, ctx, doc_filter)

                        # 3. Форматуємо отримані сирі дані для таблиці
                        formatted_rows = []
                        for d in drafts:
                            payload = d.get('payload') or []
                            c_date = d.get('created_date')

                            if isinstance(c_date, datetime):
                                created_str = c_date.strftime('%Y-%m-%d %H:%M')
                            elif isinstance(c_date, str):
                                created_str = c_date[:16]
                            else:
                                created_str = '—'

                            formatted_rows.append({
                                'id': d.get('id'),
                                'out_number': d.get('out_number') or '—',
                                'out_date': d.get('out_date') or '—',
                                'people_count': len(payload),
                                'created_date': created_str,
                                'status': d.get('status', DOC_STATUS_DRAFT),
                            })

                        # 4. Оновлюємо таблицю
                        table.rows = formatted_rows
                        table.update()

                    except Exception as e:
                        ui.notify(f'Помилка пошуку: {e}', type='negative')
                    finally:
                        search_btn.props(remove='loading')

                def clear_filters():
                    filter_state['date_from'] = ''
                    filter_state['date_to'] = ''
                    filter_state['out_number'] = ''
                    filter_state['status'] = 'Всі'
                    ui.timer(0.1, apply_filters, once=True)  # Запускаємо пошук після очищення

                search_btn = ui.button(icon='search', on_click=apply_filters).props('color="primary" round dense').tooltip('Застосувати фільтри')
                ui.button(icon='clear_all', on_click=clear_filters).props('color="gray" flat round dense').tooltip('Очистити')

            ui.button('Створити новий пакет', icon='add',
                      on_click=lambda: ui.navigate.to('/doc_dbr/create')
                      ).props('color="primary"').classes('shrink-0 h-10')

        # Створюємо порожню таблицю (вона заповниться при першому виклику apply_filters)
        table = ui.table(columns=columns, rows=[], row_key='id').classes('w-full max-w-6xl shadow-md')
        table.props('flat bordered separator=horizontal row-key="id"')

        # Кастомні слоти
        table.add_slot('body-cell-status', '''
            <q-td :props="props">
                <q-badge :color="props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'green' : 'orange'" class="text-bold q-pa-sm">
                    {{ props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'Відправлено' : 'Чернетка' }}
                </q-badge>
            </q-td>
        ''')

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

        # Обробники подій таблиці
        table.on('edit', lambda e: ui.navigate.to(f'/doc_dbr/edit/{e.args}'))

        async def on_delete(e):
            draft_id = e.args
            dialog = ui.dialog()
            with dialog, ui.card().classes('p-6 min-w-[300px]'):
                ui.label('Увага!').classes('text-xl font-bold text-red-600 mb-2')
                ui.label(f'Ви дійсно хочете видалити пакет №{draft_id}?').classes('text-gray-600 mb-6')
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                    ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

            if await dialog:
                try:
                    await run.io_bound(dbr_ctrl.delete_dbr_doc, ctx, draft_id)
                    table.rows = [row for row in table.rows if row['id'] != draft_id]
                    table.update()
                    ui.notify(f'Пакет №{draft_id} успішно видалено', type='info')
                except Exception as ex:
                    ui.notify(f'Помилка видалення: {ex}', type='negative')

        table.on('delete', on_delete)

    # 💡 Викликаємо пошук при завантаженні сторінки, щоб відмалювати всі записи за замовчуванням
    ui.timer(0.1, apply_filters, once=True)