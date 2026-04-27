import asyncio
from nicegui import ui, run

from gui.controllers.report_controller import ReportController
from gui.services.auth_manager import AuthManager
from gui.controllers.person_controller import PersonController  # Додали імпорт
from domain.audit_filter import AuditSearchFilter
from dics.deserter_xls_dic import COLUMN_INSERT_DATE  # Додали імпорт


def render_audit_page(report_ctrl: ReportController, person_ctrl: PersonController, auth_manager: AuthManager):
    ui.label('Аудит бази даних ЄРДР').classes('w-full text-center text-3xl font-bold mb-8 text-indigo-900')

    # Створюємо екземпляр фільтра
    audit_filter = AuditSearchFilter()

    # Отримуємо опції для років та сортуємо їх
    year_options = person_ctrl.get_column_options().get(COLUMN_INSERT_DATE, [])
    year_options = sorted([str(y) for y in year_options], reverse=True)

    # Контейнер для статистики
    stats_container = ui.row().classes('w-full justify-center gap-8 mb-6 py-4 bg-gray-50 rounded-xl border border-gray-200 shadow-sm')

    with stats_container:
        status_lbl = ui.label('Готовий до перевірки').classes('text-lg font-medium text-gray-600')
        error_count_lbl = ui.label('').classes('text-lg font-bold text-red-600 hidden')

    # БЛОК ФІЛЬТРІВ
    with ui.card().classes('w-full max-w-4xl mx-auto mb-8 bg-white border border-gray-100 shadow-md'):
        ui.label('Параметри перевірки').classes('text-xl font-bold mb-4 text-gray-800')

        # --- ДОДАНО ВИБІР РОКУ ---
        with ui.row().classes('w-full mb-4 items-center'):
            year_select = ui.select(
                options=['Всі роки'] + year_options,
                value='Всі роки',
                label='Рік запису'
            ).classes('w-64').props('outlined dense')

        ui.separator().classes('mb-4')

        with ui.row().classes('w-full items-start'):
            # Ліва колонка чекбоксів
            with ui.column().classes('w-1/2 gap-2'):
                ui.checkbox('Критичні помилки (порожні ПІБ, №)') \
                    .bind_value(audit_filter, 'check_critical_empty').classes('text-gray-700')

                ui.checkbox('Дати з майбутнього') \
                    .bind_value(audit_filter, 'check_future_dates').classes('text-gray-700')

                ui.checkbox('Нелогічність у датах (СЗЧ > Повернення)') \
                    .bind_value(audit_filter, 'check_date_logic').classes('text-gray-700')


            # Права колонка чекбоксів
            with ui.column().classes('w-1/2 gap-2'):

                ui.checkbox('Невідповідність РНОКПП та Дати народження') \
                    .bind_value(audit_filter, 'check_rnokpp_dob').classes('text-gray-700')

                ui.checkbox('Аномалії військового звання') \
                    .bind_value(audit_filter, 'check_title').classes('text-gray-700')

                ui.checkbox('Аномалії виду служби') \
                    .bind_value(audit_filter, 'check_service_type').classes('text-gray-700')

    # Кнопка запуску
    with ui.row().classes('w-full justify-center mb-8'):
        scan_btn = ui.button('Запустити сканування', icon='troubleshoot').classes('bg-indigo-600 text-white px-8 py-3 text-lg rounded-lg')
        scan_btn.props('elevated')

    # Таблиця результатів
    table_container = ui.column().classes('w-full mx-auto items-center')

    with table_container:
        columns = [
            {'name': 'mil_unit', 'label': 'Підрозділ', 'field': 'mil_unit', 'align': 'center', 'sortable': True, 'classes': 'font-bold text-gray-700'},
            {'name': 'row_idx', 'label': 'Рядок', 'field': 'row_idx', 'align': 'left', 'sortable': True, 'style': 'width: 80px; font-weight: bold;'},
            {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left', 'sortable': True, 'classes': 'text-indigo-900 font-medium'},
            {'name': 'column', 'label': 'Проблемна колонка', 'field': 'column', 'align': 'left', 'sortable': True},
            {'name': 'error_desc', 'label': 'Опис помилки', 'field': 'error_desc', 'align': 'left', 'classes': 'text-red-700'},
        ]

        table = ui.table(columns=columns, rows=[], row_key='row_idx').classes('w-full general-table hidden')

        success_msg = ui.row().classes('w-full justify-center gap-2 items-center text-green-600 hidden mt-8')
        with success_msg:
            ui.icon('verified', size='2rem')
            ui.label('Помилок не знайдено! База в ідеальному стані.').classes('text-xl font-bold')

    async def run_audit():
        # Перевірка, чи вибраний хоча б один фільтр (рік не рахується як перевірка)
        checks = [
            audit_filter.check_rnokpp_dob, audit_filter.check_critical_empty,
            audit_filter.check_date_logic, audit_filter.check_future_dates,
            audit_filter.check_title, audit_filter.check_service_type
        ]
        if not any(checks):
            ui.notify('Виберіть хоча б один параметр для перевірки!', type='warning')
            return

        # --- ЗАПИСУЄМО ВИБРАНИЙ РІК У ФІЛЬТР ---
        audit_filter.ins_year = None if year_select.value == 'Всі роки' else year_select.value

        scan_btn.disable()
        scan_btn.props('loading')
        status_lbl.set_text('Йде перевірка Excel файлу. Це може зайняти кілька секунд...')
        status_lbl.classes(replace='text-lg font-medium text-orange-500')
        table.classes('hidden')
        success_msg.classes('hidden')
        error_count_lbl.classes('hidden')

        await asyncio.sleep(0.1)

        try:
            ctx = auth_manager.get_current_context()
            anomalies_dict = await run.io_bound(report_ctrl.find_excel_anomalies, ctx, audit_filter)

            flat_anomalies = []
            for unit_name, errors_list in anomalies_dict.items():
                for error in errors_list:
                    error['mil_unit'] = unit_name
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