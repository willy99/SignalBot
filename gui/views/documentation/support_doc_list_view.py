from nicegui import ui, run

from config import RECORDS_PER_PAGE
from gui.controllers.support_controller import SupportController
from gui.services.request_context import RequestContext
from service.constants import DOC_STATUS_COMPLETED, DOC_STATUS_DRAFT, DOC_PACKAGE_STANDART
from datetime import datetime
from gui.tools.ui_components import date_input, fix_date, confirm_delete_dialog, ServerPagination
from domain.document_filter import DocumentFilter


def render_drafts_list_page(controller: SupportController, ctx: RequestContext):
    ui.label('Список пакетів супроводів').classes('w-full text-center text-3xl font-bold mb-8')

    # Стан фільтрів на UI
    filter_state = {
        'date_from': '',
        'date_to': '',
        'out_number': '',
        'status': 'Всі'
    }

    # Визначаємо колонки
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
        {'name': 'package_type', 'label': 'Тип', 'field': 'package_type', 'align': 'center', 'sortable': True},
        {'name': 'out_number', 'label': 'Номер супроводу', 'field': 'out_number', 'align': 'left', 'sortable': True},
        {'name': 'out_date', 'label': 'Дата формування', 'field': 'out_date', 'align': 'left', 'sortable': True},
        {'name': 'city', 'label': 'Місто', 'field': 'city', 'align': 'left', 'sortable': True},
        {'name': 'people_count', 'label': 'Кількість у пакеті', 'field': 'people_count', 'align': 'center', 'sortable': True},
        {'name': 'created_date', 'label': 'Дата створення', 'field': 'created_date', 'align': 'left', 'sortable': True},
        {'name': 'created_by', 'label': 'Ким створено', 'field': 'created_by', 'align': 'left', 'sortable': True},
        {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'left', 'sortable': True},
        {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
    ]

    with ui.column().classes('w-full items-center'):
        with ui.row().classes('w-full max-w-7xl justify-between items-center mb-4 gap-4 flex-nowrap'):

            # ==========================================
            # БЛОК ФІЛЬТРІВ
            # ==========================================
            with ui.row().classes('items-center gap-3 bg-white p-2 rounded-lg border shadow-sm flex-grow'):
                ui.icon('filter_alt', size='sm').classes('text-gray-400 ml-2')

                date_input('Створено з', filter_state, 'date_from', blur_handler=fix_date).classes('w-28')
                date_input('По', filter_state, 'date_to', blur_handler=fix_date).classes('w-28')

                ui.input('Номер супроводу').bind_value(filter_state, 'out_number').classes('w-32').props('dense outlined clearable')

                status_options = {'Всі': 'Всі', DOC_STATUS_DRAFT: 'Чернетка', DOC_STATUS_COMPLETED: 'Відправлено'}
                ui.select(status_options, label='Статус').bind_value(filter_state, 'status').classes('w-36').props('dense outlined')

                async def apply_filters(reset_page=True):
                    search_btn.props('loading')
                    if reset_page:
                        pager.reset()

                    try:
                        # Пакуємо дані з UI у Dataclass
                        doc_filter = DocumentFilter(
                            date_from=filter_state['date_from'] or None,
                            date_to=filter_state['date_to'] or None,
                            out_number=filter_state['out_number'].strip() if filter_state['out_number'] else None,
                            status=filter_state['status'] if filter_state['status'] != 'Всі' else None,
                            limit=pager.limit,
                            offset=pager.offset
                        )
                        total_count = await run.io_bound(controller.count_search_docs, ctx, doc_filter)
                        pager.update_total(total_count)

                        # Викликаємо контролер
                        drafts = await run.io_bound(controller.search_drafts, ctx, doc_filter)

                        # Форматуємо результати
                        formatted_rows = []
                        for d in drafts:
                            payload = getattr(d, 'payload', []) if not isinstance(d, dict) else d.get('payload', [])
                            c_date = getattr(d, 'created_date', None) if not isinstance(d, dict) else d.get('created_date')

                            if isinstance(c_date, datetime):
                                created_str = c_date.strftime('%Y-%m-%d %H:%M')
                            elif isinstance(c_date, str):
                                created_str = c_date[:16]
                            else:
                                created_str = '—'

                            formatted_rows.append({
                                'id': getattr(d, 'id', d.get('id') if isinstance(d, dict) else None),
                                'out_number': getattr(d, 'out_number', d.get('out_number') if isinstance(d, dict) else None) or '—',
                                'out_date': getattr(d, 'out_date', d.get('out_date') if isinstance(d, dict) else None) or '—',
                                'city': getattr(d, 'city', d.get('city') if isinstance(d, dict) else '—'),
                                'people_count': len(payload),
                                'created_date': created_str,
                                'created_by': getattr(d, 'created_by', d.get('created_by') if isinstance(d, dict) else '—'),
                                'status': getattr(d, 'status', d.get('status') if isinstance(d, dict) else DOC_STATUS_DRAFT),
                                'package_type': getattr(d, 'package_type', d.get('package_type') if isinstance(d, dict) else '—')
                            })

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
                    ui.timer(0.1, apply_filters, once=True)

                search_btn = ui.button(icon='search', on_click=apply_filters).props('color="primary" round dense').tooltip('Застосувати фільтри')
                ui.button(icon='clear_all', on_click=clear_filters).props('color="gray" flat round dense').tooltip('Очистити')

            # ==========================================
            # Кнопки створення пакетів (Права сторона)
            # ==========================================
            with ui.row().classes('items-center gap-2 shrink-0'):
                ui.button('Новий Зведений', icon='add',
                          on_click=lambda: ui.navigate.to('/doc_support/s_create')
                          ).props('color="primary"').classes('h-10')
                ui.button('Новий Детальний', icon='add_circle',
                          on_click=lambda: ui.navigate.to('/doc_support/d_create')
                          ).props('color="secondary" outline').classes('h-10')

        # Створюємо порожню таблицю
        table = ui.table(columns=columns, rows=[], row_key='id').classes('w-full max-w-8xl general-table')
        table.props('flat bordered separator=cell')
        pager = ServerPagination(
            records_per_page=RECORDS_PER_PAGE,
            on_change=lambda: ui.timer(0.1, lambda: apply_filters(reset_page=False), once=True)
        )

        # Кастомні слоти
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
                <q-badge :color="props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'green' : 'orange'" class="text-bold q-pa-sm">
                    {{ props.row.status === \'''' + DOC_STATUS_COMPLETED + '''\' ? 'Відправлено' : 'Чернетка' }}
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

        # Обробники подій
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
            result = await confirm_delete_dialog(f'Ви дійсно хочете видалити пакет №{draft_id}?')
            if result:
                try:
                    await run.io_bound(controller.delete_draft, ctx, draft_id)
                    table.rows = [row for row in table.rows if row['id'] != draft_id]
                    table.update()
                    ui.notify(f'Пакет супроводів №{draft_id} видалено', type='negative')
                except Exception as ex:
                    ui.notify(f'Помилка видалення: {ex}', type='negative')

        table.on('edit', on_edit)
        table.on('delete', on_delete)

    # 💡 Ініціюємо завантаження таблиці
    ui.timer(0.1, apply_filters, once=True)