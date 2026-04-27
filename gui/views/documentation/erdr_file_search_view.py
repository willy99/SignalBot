from nicegui import ui
import config
from gui.services.auth_manager import AuthManager
from service.storage.ErdrCacher import ErdrCacheManager
import regex as re

def render_erdr_search_page(erdr_cache_manager: ErdrCacheManager, auth_manager: AuthManager):
    # Завантажуємо кеш при відкритті сторінки
    erdr_cache_manager.load_cache()

    with ui.column().classes('w-full items-center px-8 py-4'):
        # Змінено заголовок для ідентифікації сторінки
        ui.label('Миттєвий пошук витягів ЄРДР у базі').classes('text-h4 mb-4 text-indigo-800')
        with ui.row().classes('w-full justify-center gap-8 mb-6 py-3 bg-indigo-50 rounded-xl border border-indigo-100 shadow-sm'):
            ui.label(f'📁 Файлів у базі: {getattr(erdr_cache_manager, "total_count", 0)}').classes('text-indigo-900 font-bold')
            ui.label(f'👥 Осіб знайдено: {getattr(erdr_cache_manager, "total_persons", 0)}').classes('text-indigo-900 font-bold')
            ui.label(f'Оновлено: {getattr(erdr_cache_manager, "last_indexed_date", "Ніколи")}') \
                .classes(f'font-bold {getattr(erdr_cache_manager, "status_color", "text-gray-600")}')

        with ui.row().classes('w-full items-center gap-4'):
            search_field = ui.input(
                label='Введіть прізвище (напр: максименко, або макс*дмитро)') \
                .classes('flex-grow text-lg') \
                .props('autofocus clearable outlined')

            # Змінено колір кнопки для візуального розмежування модулів
            search_btn = ui.button('Знайти', icon='search').props('elevated').classes('h-14 bg-indigo-600')

        results_container = ui.column().classes('w-full mt-6')

        def get_full_source_path(row_data):
            filename = row_data['name']
            folder_path = row_data['path']
            # ВАЖЛИВО: Використовуємо шлях до папки з ЄРДР
            base_dir = config.ERDR_DOCUMENT_STORAGE_PATH.rstrip('\\/')

            match = re.match(r'^\\\\[^\\]+\\[^\\]+', base_dir)
            share_root = match.group(0) if match else base_dir

            if folder_path == "(Коренева папка)":
                return f"{base_dir}\\{filename}"
            else:
                return f"{share_root}\\{folder_path}\\{filename}"

        async def copy_to_outbox(e):
            row_data = e.args
            source_path = get_full_source_path(row_data)
            filename = row_data['name']

            # Використовуємо сепаратор напряму від клієнта
            separator = erdr_cache_manager.client.get_separator()
            destination_path = config.OUTBOX_DIR_PATH + separator + auth_manager.get_current_context().user_login + separator + filename

            with ui.notification(message=f'Копіювання {filename}...', spinner=True, timeout=0) as n:
                try:
                    await auth_manager.execute(erdr_cache_manager.copy_to_local, auth_manager.get_current_context(), source_path, destination_path)
                    n.message = 'Витяг успішно скопійовано в Outbox!'
                    n.type = 'positive'
                    n.icon = 'check_circle'
                    n.spinner = False
                    n.timeout = 3
                except Exception as ex:
                    n.message = f'Помилка копіювання: {ex}'
                    n.type = 'negative'
                    n.icon = 'error'
                    n.spinner = False
                    n.timeout = 5

        async def download_file(e):
            row_data = e.args
            filename = row_data['name']
            source_path = get_full_source_path(row_data)

            with ui.notification(message=f'Підготовка до завантаження {filename}...', spinner=True, timeout=0) as n:
                try:
                    # Читаємо файл у буфер через клієнт
                    file_buffer = await auth_manager.execute(erdr_cache_manager.client.get_file_buffer, auth_manager.get_current_context(), source_path)

                    # Відправляємо файл клієнту
                    ui.download(file_buffer.read(), filename)

                    n.message = 'Завантаження розпочато!'
                    n.type = 'positive'
                    n.spinner = False
                    n.timeout = 2
                except Exception as ex:
                    n.message = f'Помилка завантаження: {ex}'
                    n.type = 'negative'
                    n.spinner = False
                    n.timeout = 5

        # ---------------------------------------------------------
        # ЛОГІКА ПОШУКУ ТА ВІДМАЛЬОВКИ ТАБЛИЦІ
        # ---------------------------------------------------------
        def do_search(e=None):
            query = search_field.value
            if not query or len(query.replace('*', '')) < 2:
                ui.notify('Введіть мінімум 2 символи для пошуку', type='warning')
                return

            results_container.clear()
            with results_container:
                ui.spinner(size='lg')

            data = erdr_cache_manager.search(query)

            results_container.clear()
            with results_container:
                if not data:
                    ui.notify('Витягів не знайдено', type='negative')
                    return

                ui.label(f'Знайдено документів: {len(data)}').classes('font-bold text-gray-600 mb-2')

                display_data = data[:100]
                if len(data) > 100:
                    ui.notify('Показано перші 100 результатів. Уточніть запит.', type='info')

                # Підготовка даних для відображення
                for row in display_data:
                    names_list = row.get('names', [])
                    row['names_display'] = ", ".join(names_list) if names_list else "—"

                # Колонки адаптовані під ЄРДР
                columns = [
                    {'name': 'name', 'label': 'Назва витягу / Файлу', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'names', 'label': 'Знайдені особи', 'field': 'names_display', 'align': 'left',
                     'classes': 'whitespace-normal text-indigo-900 font-medium', 'style': 'max-width: 350px; word-break: break-word;'},
                    {'name': 'path', 'label': 'Шлях (Рік / Місяць)', 'field': 'path', 'align': 'left'},
                    {'name': 'action', 'label': 'Дії', 'field': 'action', 'align': 'center'},
                ]

                table = ui.table(columns=columns, rows=display_data, row_key='name').classes('w-full general-table')

                table.add_slot('body-cell-action', '''
                                <q-td :props="props" class="q-gutter-xs">                        
                                    <q-btn size="sm" color="indigo-5" icon="file_download"
                                           @click="$parent.$emit('downloadFile', props.row)">
                                        <q-tooltip>Завантажити на комп'ютер</q-tooltip>
                                    </q-btn>
                                    <q-btn size="sm" color="green-7" icon="forward_to_inbox"
                                           @click="$parent.$emit('copyToOutbox', props.row)">
                                        <q-tooltip>Копіювати в Outbox</q-tooltip>
                                    </q-btn>
                                </q-td>
                            ''')

                table.on('copyToOutbox', copy_to_outbox)
                table.on('downloadFile', download_file)

        search_field.on('keydown.enter', do_search)
        search_btn.on('click', do_search)