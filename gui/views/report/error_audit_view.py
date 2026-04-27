import asyncio
from nicegui import ui, run

from gui.controllers.report_controller import ReportController
from gui.services.auth_manager import AuthManager
from gui.controllers.person_controller import PersonController
from domain.audit_filter import AuditSearchFilter
from domain.person import Person
import dics.deserter_xls_dic as col


def render_audit_page(report_ctrl: ReportController, person_ctrl: PersonController, auth_manager: AuthManager):
    ui.label('Аудит бази даних ЄРДР').classes('w-full text-center text-3xl font-bold mb-8 text-indigo-900')

    audit_filter = AuditSearchFilter()
    pending_updates = {}  # Стейт для збереження чернеток { 'unit_id_col': {'id': 1, 'unit': 'А0224', 'col': '...', 'val': '...'} }

    year_options = person_ctrl.get_column_options().get(col.COLUMN_INSERT_DATE, [])
    year_options = sorted([str(y) for y in year_options], reverse=True)

    # Список всіх доступних колонок для випадаючого списку при виправленні
    all_columns = [
        col.COLUMN_NAME, col.COLUMN_ID_NUMBER, col.COLUMN_BIRTHDAY,
        col.COLUMN_DESERTION_DATE, col.COLUMN_RETURN_DATE, col.COLUMN_RETURN_TO_RESERVE_DATE,
        col.COLUMN_TITLE, col.COLUMN_SERVICE_TYPE, col.COLUMN_INCREMENTAL
    ]

    stats_container = ui.row().classes('w-full justify-center gap-8 mb-6 py-4 bg-gray-50 rounded-xl border border-gray-200 shadow-sm')

    with stats_container:
        status_lbl = ui.label('Готовий до перевірки').classes('text-lg font-medium text-gray-600')
        error_count_lbl = ui.label('').classes('text-lg font-bold text-red-600 hidden')

    with ui.card().classes('w-full max-w-4xl mx-auto mb-8 bg-white border border-gray-100 shadow-md'):
        ui.label('Параметри перевірки').classes('text-xl font-bold mb-4 text-gray-800')

        with ui.row().classes('w-full mb-4 items-center justify-between'):
            year_select = ui.select(
                options=['Всі роки'] + year_options,
                value='Всі роки',
                label='Рік запису'
            ).classes('w-64').props('outlined dense')

            # Кнопка збереження "на гарячу" (прихована за замовчуванням)
            save_all_btn = ui.button('ЗБЕРЕГТИ ВИПРАВЛЕННЯ', icon='cloud_upload', color='orange', on_click=lambda: save_changes()) \
                .props('elevated size=md').classes('hidden')

        ui.separator().classes('mb-4')

        with ui.row().classes('w-full items-start'):
            with ui.column().classes('w-1/2 gap-2'):
                ui.checkbox('Критичні помилки (порожні ПІБ, №)') \
                    .bind_value(audit_filter, 'check_critical_empty').classes('text-gray-700')
                ui.checkbox('Дати з майбутнього') \
                    .bind_value(audit_filter, 'check_future_dates').classes('text-gray-700')
                ui.checkbox('Нелогічність у датах (СЗЧ > Повернення)') \
                    .bind_value(audit_filter, 'check_date_logic').classes('text-gray-700')

            with ui.column().classes('w-1/2 gap-2'):
                ui.checkbox('Невідповідність РНОКПП та Дати народження') \
                    .bind_value(audit_filter, 'check_rnokpp_dob').classes('text-gray-700')
                ui.checkbox('Помилки в військових званнях') \
                    .bind_value(audit_filter, 'check_title').classes('text-gray-700')
                ui.checkbox('Помилки в видах служби') \
                    .bind_value(audit_filter, 'check_service_type').classes('text-gray-700')

    with ui.row().classes('w-full justify-center mb-8'):
        scan_btn = ui.button('Запустити сканування', icon='troubleshoot').classes('bg-indigo-600 text-white px-8 py-3 text-lg rounded-lg')
        scan_btn.props('elevated')

    # --- ДІАЛОГ ВИПРАВЛЕННЯ ---
    edit_state = {'row': None}
    with ui.dialog() as edit_dialog, ui.card().classes('min-w-[800px] p-6 max-h-[120vh]'):
        ui.label('Виправити дані').classes('text-xl font-bold mb-2')
        edit_info_lbl = ui.label('').classes('text-sm text-gray-600 mb-4')

        target_col_select = ui.select(options=all_columns, label='Колонка для заміни').classes('w-full mb-2')

        # Додаємо підказку (hint), щоб користувач розумів, звідки взялося значення
        new_val_input = ui.input('Нове значення').classes('w-full mb-6 text-lg font-medium')

        # --- ДОДАЄМО БЛОК КОНТЕКСТУ ---
        ui.separator().classes('my-2')
        ui.label('Контекст з документа:').classes('text-sm font-bold text-gray-700 mb-2')

        # Використовуємо textarea, щоб довгий текст не "ламав" верстку
        bio_textarea = ui.textarea('Біографія (bio)').classes('w-full mb-2').props('readonly autogrow outlined')
        cond_textarea = ui.textarea('Умови СЗЧ (cond)').classes('w-full mb-6').props('readonly autogrow outlined')

        def apply_fix():
            row = edit_state['row']
            col_name = target_col_select.value
            new_val = new_val_input.value

            if not col_name or not new_val:
                ui.notify('Заповніть всі поля', type='warning')
                return

            if not row.get('id'):
                ui.notify('У цього запису відсутній ID (№). Виправте це вручну в Excel!', type='negative')
                return

            # Зберігаємо чернетку
            key = f"{row['mil_unit']}_{row['id']}_{col_name}"
            pending_updates[key] = {
                'id': row['id'],
                'mil_unit': row['mil_unit'],
                'col': col_name,
                'val': new_val
            }

            # Оновлюємо дані рядка
            row['is_fixed'] = True
            row['new_value'] = f"[{col_name}]: {new_val}"
            save_all_btn.classes(remove='hidden')

            # 💡 МАГІЯ РЕАКТИВНОСТІ: Форсуємо оновлення таблиці, створюючи новий список
            # table.rows = list(table.rows)

            table.update()
            edit_dialog.close()
            ui.notify('Додано в чергу на збереження', type='info')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=edit_dialog.close).props('flat text-gray-500')
            ui.button('Застосувати', on_click=apply_fix, color='green')

    def open_edit_dialog(row):
        edit_state['row'] = row
        edit_info_lbl.set_text(f"{row['name']} (Рядок: {row['row_idx']})")

        # 1. Авто-вибір колонки (якщо бекенд передав suggested_col)
        if row.get('suggested_col') and row['suggested_col'] in all_columns:
            target_col_select.value = row['suggested_col']
        else:
            guessed_col = row['column'].split(' / ')[0] if row['column'] else None
            target_col_select.value = guessed_col if guessed_col in all_columns else all_columns[0]

        # 2. Авто-заповнення очікуваного значення (якщо бекенд передав expected_val)
        if row.get('expected_val'):
            new_val_input.value = str(row['expected_val'])
            new_val_input.props('color="green"')  # Трохи підсвітимо інпут
        else:
            new_val_input.value = ''
            new_val_input.props('color="primary"')

        bio_textarea.value = row.get('bio') or 'Дані про біографію відсутні.'
        cond_textarea.value = row.get('cond') or 'Дані про умови відсутні.'

        edit_dialog.open()

    # --- ТАБЛИЦЯ ---
    table_container = ui.column().classes('w-full mx-auto items-center')
    with table_container:
        columns = [
            {'name': 'mil_unit', 'label': 'Підрозділ', 'field': 'mil_unit', 'align': 'center', 'sortable': True, 'classes': 'font-bold text-gray-700'},
            {'name': 'id', 'label': '№', 'field': 'id', 'align': 'center', 'sortable': True},
            {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left', 'sortable': True, 'classes': 'text-indigo-900 font-medium'},
            {'name': 'column', 'label': 'Проблемна колонка', 'field': 'column', 'align': 'left'},
            {'name': 'error_desc', 'label': 'Опис помилки', 'field': 'error_desc', 'align': 'left'},
            {'name': 'new_value', 'label': 'Нове значення', 'field': 'new_value', 'align': 'left'},
            {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
        ]

        table = ui.table(columns=columns, rows=[], row_key='row_idx').classes('w-full general-table hidden')

        # Кастомні слоти для гарного відображення виправлень
        table.add_slot('body', '''
            <q-tr :props="props">
                <q-td key="mil_unit" :props="props" class="font-bold text-gray-700">{{ props.row.mil_unit }}</q-td>
                <q-td key="id" :props="props">{{ props.row.id || 'N/A' }}</q-td>
                <q-td key="name" :props="props" class="font-bold text-blue-900">{{ props.row.name }}</q-td>
                <q-td key="column" :props="props">{{ props.row.column }}</q-td>
                <q-td key="error_desc" :props="props" :class="props.row.is_fixed ? 'text-grey text-strike' : 'text-red-700'">
                    {{ props.row.error_desc }}
                </q-td>
                <q-td key="new_value" :props="props" class="text-green-700 font-bold bg-green-50">
                    {{ props.row.new_value }}
                </q-td>
                <q-td key="actions" :props="props">
                    <q-btn v-if="!props.row.is_fixed" flat round icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row)">
                        <q-tooltip>Виправити помилку</q-tooltip>
                    </q-btn>
                    <q-icon v-else name="check_circle" color="green" size="md"></q-icon>
                </q-td>
            </q-tr>
        ''')
        table.on('edit', lambda e: open_edit_dialog(e.args))

        success_msg = ui.row().classes('w-full justify-center gap-2 items-center text-green-600 hidden mt-8')
        with success_msg:
            ui.icon('verified', size='2rem')
            ui.label('Помилок не знайдено! База в ідеальному стані.').classes('text-xl font-bold')

    async def save_changes():
        if not pending_updates: return
        save_all_btn.disable()

        persons_to_update = []
        # Групуємо зміни по ID та підрозділу, щоб створити один об'єкт Person на кожен рядок
        grouped = {}
        for key, data in pending_updates.items():
            g_key = (data['id'], data['mil_unit'])
            if g_key not in grouped:
                # Базовий словник для створення Person
                grouped[g_key] = {col.COLUMN_INCREMENTAL: data['id'], col.COLUMN_MIL_UNIT: data['mil_unit']}

            # Додаємо виправлену колонку у словник
            grouped[g_key][data['col']] = data['val']

        # Створюємо об'єкти Person через from_excel_dict
        for data_dict in grouped.values():
            persons_to_update.append(Person.from_excel_dict(data_dict))

        try:
            success = await auth_manager.execute(
                person_ctrl.save_persons,
                auth_manager.get_current_context(),
                persons_to_update,
                partial_update=True
            )
            if success:
                ui.notify(f'Успішно збережено в базу!', type='positive')
                pending_updates.clear()
                save_all_btn.classes('hidden')
                await run_audit()  # Перезапускаємо звіт
            else:
                ui.notify('Помилка при збереженні', type='negative')
        except Exception as e:
            ui.notify(f'Критична помилка: {e}', type='negative')
        finally:
            save_all_btn.enable()

    async def run_audit():
        checks = [
            audit_filter.check_rnokpp_dob, audit_filter.check_critical_empty,
            audit_filter.check_date_logic, audit_filter.check_future_dates,
            audit_filter.check_title, audit_filter.check_service_type
        ]
        if not any(checks):
            ui.notify('Виберіть хоча б один параметр для перевірки!', type='warning')
            return

        audit_filter.ins_year = None if year_select.value == 'Всі роки' else year_select.value

        scan_btn.disable()
        scan_btn.props('loading')
        status_lbl.set_text('Йде перевірка Excel файлу. Це може зайняти кілька секунд...')
        status_lbl.classes(replace='text-lg font-medium text-orange-500')
        table.classes('hidden')
        success_msg.classes('hidden')
        error_count_lbl.classes('hidden')
        pending_updates.clear()
        save_all_btn.classes('hidden')

        await asyncio.sleep(0.1)

        try:
            ctx = auth_manager.get_current_context()
            anomalies_dict = await run.io_bound(report_ctrl.find_excel_anomalies, ctx, audit_filter)

            flat_anomalies = []
            for unit_name, errors_list in anomalies_dict.items():
                for error in errors_list:
                    error['mil_unit'] = unit_name
                    error['is_fixed'] = False
                    error['new_value'] = ''
                    # Обов'язково переконайтеся, що backend повертає 'id' в словнику error!
                    flat_anomalies.append(error)

            if flat_anomalies:
                table.rows = flat_anomalies
                table.classes(remove='hidden')
                error_count_lbl.set_text(f'❌ Знайдено помилок: {len(flat_anomalies)}')
                error_count_lbl.classes(remove='hidden')
                status_lbl.set_text('Сканування завершено')
                status_lbl.classes(replace='text-lg font-medium text-gray-600')
                ui.notify(f'Виявлено {len(flat_anomalies)} логічних помилок!', type='warning')
            else:
                success_msg.classes(remove='hidden')
                status_lbl.set_text('Сканування завершено')
                status_lbl.classes(replace='text-lg font-medium text-gray-600')
                ui.notify('Перевірка пройдена успішно!', type='positive')

        except Exception as e:
            ui.notify(f'Помилка під час сканування: {e}', type='negative')
            status_lbl.set_text('Помилка сканування')
            status_lbl.classes(replace='text-lg font-medium text-red-600')
        finally:
            scan_btn.enable()
            scan_btn.props(remove='loading')

    scan_btn.on('click', run_audit)