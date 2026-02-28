from nicegui import ui, run
import config
from gui.services.request_context import RequestContext
from service.storage.FileCacher import FileCacheManager
import re

def render_file_search_page(file_cache_manager: FileCacheManager, ctx: RequestContext):
    file_cache_manager.load_cache()

    with ui.column().classes('w-full items-center px-8 py-4'):
        ui.label('Миттєвий пошук файлів у базі').classes('text-h4 mb-4')

        with ui.row().classes('w-full items-center gap-4'):
            search_field = ui.input(
                label='Введіть прізвище або назву (напр: Максименко)') \
                .classes('flex-grow text-lg') \
                .props('autofocus clearable outlined')

            search_btn = ui.button('Знайти', icon='search').props('elevated').classes('h-14 bg-blue-600')

        results_container = ui.column().classes('w-full mt-6')

        # ---------------------------------------------------------
        # ВИПРАВЛЕНО: Функція копіювання тепер реконструює шлях
        # ---------------------------------------------------------
        async def copy_to_outbox(e):
            row_data = e.args
            filename = row_data['name']
            folder_path = row_data['path']

            # Реконструюємо повний шлях до файлу (оскільки ми видалили path_win з кешу)
            base_dir = config.DOCUMENT_STORAGE_PATH.rstrip('\\/')
            if folder_path == "(Коренева папка)":
                source_path = f"{base_dir}\\{filename}"
            else:
                source_path = f"{base_dir}\\{folder_path}\\{filename}"
                # Витягуємо тільки \\IP-адреса\назва_шари (напр. \\192.168.110.51\exchange)
            match = re.match(r'^\\\\[^\\]+\\[^\\]+', base_dir)
            share_root = match.group(0) if match else base_dir

            if folder_path == "(Коренева папка)":
                source_path = f"{base_dir}\\{filename}"
            else:
                # Клеїмо до share_root (\\...\exchange), бо folder_path вже містить "ДД\..."
                source_path = f"{share_root}\\{folder_path}\\{filename}"
                # -----------------------------------

            destination_path = config.OUTBOX_DIR_PATH + file_cache_manager.get_file_separator() + ctx.user_login + file_cache_manager.get_file_separator() + filename

            with ui.notification(message=f'Копіювання {filename}...', spinner=True, timeout=0) as n:
                try:
                    await run.io_bound(file_cache_manager.copy_to_local, source_path, destination_path)
                    n.message = 'Файл успішно скопійовано в Outbox!'
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

            data = file_cache_manager.search(query)

            results_container.clear()
            with results_container:
                if not data:
                    ui.notify('Нічого не знайдено', type='negative')
                    return

                ui.label(f'Знайдено файлів: {len(data)}').classes('font-bold text-gray-600 mb-2')

                display_data = data[:100]
                if len(data) > 100:
                    ui.notify('Показано перші 100 результатів. Уточніть запит.', type='info')

                # Підготовка даних для відображення масиву імен як рядка
                for row in display_data:
                    names_list = row.get('names', [])
                    row['names_display'] = ", ".join(names_list) if names_list else "—"

                # ДОДАНО НОВУ КОЛОНКУ ДЛЯ ІМЕН
                columns = [
                    {'name': 'name', 'label': 'Назва файлу', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'names', 'label': 'Знайдені особи', 'field': 'names_display', 'align': 'left',
                     'classes': 'whitespace-normal', 'style': 'max-width: 350px; word-break: break-word;'},
                    {'name': 'path', 'label': 'Шлях до папки', 'field': 'path', 'align': 'left'},
                    {'name': 'action', 'label': 'Дії', 'field': 'action', 'align': 'center'},
                ]

                table = ui.table(columns=columns, rows=display_data, row_key='name').classes('w-full general-table')

                table.add_slot('body-cell-action', '''
                    <q-td :props="props" class="gap-2">                        
                        <q-btn size="sm" color="green-7" icon="forward_to_inbox" label="Outbox"
                               @click="$parent.$emit('copyToOutbox', props.row)">
                            <q-tooltip>Копіювати файл в Outbox</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')

                table.on('copyToOutbox', copy_to_outbox)

        search_field.on('keydown.enter', do_search)
        search_btn.on('click', do_search)