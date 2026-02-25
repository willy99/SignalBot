from nicegui import ui, run
import config

def render_file_search_page(file_cache_manager):
    # Замість p-4 (відступи) можна зробити px-8 для країв
    file_cache_manager.load_cache()
    with ui.column().classes('w-full items-center px-8 py-4'):
        ui.label('Миттєвий пошук файлів у базі').classes('text-h4 mb-4')

        with ui.row().classes('w-full items-center gap-4'):
            search_field = ui.input(
                label='Введіть назву (можна використовувати * для пропуску слів, напр: максименко*дшб)') \
                .classes('flex-grow text-lg') \
                .props('autofocus clearable outlined')

            search_btn = ui.button('Знайти', icon='search').props('elevated').classes('h-14 bg-blue-600')

        results_container = ui.column().classes('w-full mt-6')

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

                # Налаштування колонок. Можна додати align: 'left' до всіх
                columns = [
                    {'name': 'name', 'label': 'Назва файлу', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'path', 'label': 'Шлях до папки', 'field': 'path', 'align': 'left'},
                    {'name': 'action', 'label': 'Дії', 'field': 'action', 'align': 'center'},
                ]

                # Таблиця розтягується завдяки w-full
                table = ui.table(columns=columns, rows=display_data, row_key='full_path').classes('w-full')

                table.add_slot('body-cell-action', '''
                    <q-td :props="props" class="gap-2">
                        <q-btn size="sm" color="blue-8" icon="content_copy" label="Win"
                               @click="$parent.$emit('copyPath', {path: props.row.path_win, os: 'Windows'})">
                            <q-tooltip>Копіювати шлях для Windows</q-tooltip>
                        </q-btn>

                        <q-btn size="sm" color="grey-8" icon="content_copy" label="Mac" style="margin-left: 8px;" class="gap-2"
                               @click="$parent.$emit('copyPath', {path: props.row.path_mac, os: 'Mac'})">
                            <q-tooltip>Копіювати шлях для Mac (Cmd+K)</q-tooltip>
                        </q-btn>
                        
                        <q-btn size="sm" color="green-7" icon="forward_to_inbox" label="Outbox"
                               @click="$parent.$emit('copyToOutbox', props.row)">
                            <q-tooltip>Копіювати файл в Outbox</q-tooltip>
                        </q-btn>
                          
                    </q-td>
                ''')
                # Підписуємось на події

                def copy_to_clipboard(e):
                    path_to_copy = e.args['path']
                    os_name = e.args['os']
                    ui.clipboard.write(path_to_copy)
                    ui.notify(
                        f'Шлях для {os_name} скопійовано!\nВставте його у Провідник/Finder',
                        type='positive',
                        icon='check_circle',
                        multi_line=True
                    )

                table.on('copyToOutbox', copy_to_outbox)
                table.on('copyPath', copy_to_clipboard)

        search_field.on('keydown.enter', do_search)
        search_btn.on('click', do_search)

    async def copy_to_outbox(e):
        row_data = e.args
        source_path = row_data['path_win']
        filename = row_data['name']
        destination_path = config.OUTBOX_DIR_PATH + file_cache_manager.get_file_separator() + filename

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