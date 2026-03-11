from nicegui import ui, run, events
from gui.services.request_context import RequestContext
import config
from service.processing.parsers.ParserFactory import ParserFactory
import asyncio


def render_inbox_page(inbox_ctrl, task_ctrl, auth_manager, ctx: RequestContext):
    can_assign = auth_manager.has_access('task', 'delete')
    users_list = task_ctrl.get_available_users()
    user_options = {u['username']: u.get('full_name') or u['username'] for u in users_list if 'username' in u}

    state = {
        'personal_files': [],
        'root_files': [],
        'outbox_files': [],
        'selected_file': None,
        'selected_type': None,
        'file_content': '',
        'is_loading_content': False,
        'action_queue': [],
        'is_processing_queue': False
    }

    with ui.row().classes('w-full justify-center mb-4 transition-all') as queue_banner:
        queue_badge = ui.badge('Черга порожня', color='gray').classes('text-sm px-4 py-1')

    async def process_action_queue():
        q_len = len(state['action_queue'])

        if q_len > 0:
            queue_badge.set_text(f'В черзі на обробку: {q_len}')
            queue_badge.props('color="amber"')
        else:
            queue_badge.set_text('Черга порожня')
            queue_badge.props('color="gray"')

        if state['is_processing_queue'] or q_len == 0:
            return

        state['is_processing_queue'] = True

        try:
            while state['action_queue']:
                action = state['action_queue'][0]
                fname = action['filename']
                folder = action['folder']
                atype = action['type']

                try:
                    if atype == 'excel':
                        ui.notify(f'⏳ Ексель: обробка {fname}...', type='info')
                        success = await run.io_bound(inbox_ctrl.process_file_to_excel, ctx, fname)
                        if success:
                            ui.notify(f'✅ {fname} занесено в Ексель!', type='positive')
                            await run.io_bound(inbox_ctrl.delete_file, ctx, None, folder, fname)
                        else:
                            ui.notify(f'❌ Помилка розпізнавання {fname}', type='negative')

                    elif atype == 'archive':
                        ui.notify(f'⏳ Архів: збереження {fname}...', type='info')
                        success = await run.io_bound(inbox_ctrl.archive_file, ctx, fname)
                        if success:
                            ui.notify(f'✅ {fname} архівовано!', type='positive')
                            await run.io_bound(inbox_ctrl.delete_file, ctx, None, folder, fname)
                        else:
                            ui.notify(f'❌ Помилка архівації {fname}', type='negative')

                    elif atype == 'delete':
                        u_login = ctx.user_login if action.get('is_personal') else None
                        await run.io_bound(inbox_ctrl.delete_file, ctx, u_login, folder, fname)
                        ui.notify(f'🗑️ {fname} успішно видалено', type='positive')

                    elif atype == 'assign':
                        target = action['target']
                        is_pers = action.get('is_personal', False)
                        await run.io_bound(inbox_ctrl.assign_file, ctx, fname, is_pers, target)
                        ui.notify(f'👤 {fname} передано користувачу {target}', type='positive')

                except Exception as ex:
                    ui.notify(f'❌ Сталася помилка під час обробки {fname}: {ex}', type='negative')

                state['action_queue'].pop(0)
                await load_data()

        finally:
            state['is_processing_queue'] = False

    ui.timer(1.0, process_action_queue)

    def add_to_queue(action_type: str, folder: str, filename: str, **kwargs):
        state['action_queue'].append({
            'type': action_type,
            'filename': filename,
            'folder': folder,
            **kwargs
        })
        ui.notify(f'Додано в чергу: {filename}', type='info')
        refresh_left_panel()
        refresh_right_panel()

    def is_queued(filename: str) -> bool:
        return any(a['filename'] == filename for a in state['action_queue'])

    with ui.row().classes('w-full h-[calc(100vh-140px)] flex-nowrap px-4 gap-4'):
        left_panel = ui.column().classes(
            'w-1/3 max-w-[350px] h-full overflow-y-auto shrink-0 border border-gray-200 rounded-lg bg-gray-50 p-2 gap-4 shadow-inner'
        )
        right_panel = ui.column().classes(
            'flex-grow h-full border border-gray-200 rounded-lg p-0 bg-white shadow-sm flex flex-col overflow-hidden'
        )

    async def handle_upload(e: events.UploadEventArguments):
        try:
            filename = e.file.name
            file_data = await e.file.read()
            await run.io_bound(inbox_ctrl.upload_root_file, ctx, filename, file_data)
            ui.notify(f'Файл "{filename}" завантажено!', type='positive')
            e.sender.reset()
            await load_data()
        except Exception as ex:
            ui.notify(f'Помилка завантаження: {ex}', type='negative')

    async def load_data():
        try:
            data = await run.io_bound(inbox_ctrl.get_user_inbox_messages, ctx)
            state['personal_files'] = data.get('personal_files', [])
            state['root_files'] = data.get('root_files', [])
            state['outbox_files'] = data.get('outbox_files', [])

            if state['selected_file']:
                if state['selected_type'] == 'inbox_personal' and state['selected_file'] not in state['personal_files']:
                    clear_selection()
                elif state['selected_type'] == 'inbox_shared' and state['selected_file'] not in state['root_files']:
                    clear_selection()
                elif state['selected_type'] == 'outbox_personal' and state['selected_file'] not in state['outbox_files']:
                    clear_selection()

            refresh_left_panel()
            refresh_right_panel()
        except Exception as e:
            ui.notify(f'Помилка завантаження файлів: {e}', type='negative')

    def clear_selection():
        state['selected_file'] = None
        state['selected_type'] = None
        state['file_content'] = ''

    async def select_file(filename: str, f_type: str):
        state['selected_file'] = filename
        state['selected_type'] = f_type
        state['file_content'] = ''
        state['is_loading_content'] = True

        refresh_left_panel()
        refresh_right_panel()

        await load_file_content(filename, f_type)

        state['is_loading_content'] = False
        refresh_right_panel()

    async def load_file_content(filename: str, f_type: str):
        try:
            if f_type == 'inbox_personal':
                file_path = f"{config.INBOX_LOCAL_DIR_PATH}/{ctx.user_login}/{filename}"
            elif f_type == 'outbox_personal':
                file_path = f"{config.OUTBOX_LOCAL_DIR_PATH}/{ctx.user_login}/{filename}"
            else:
                file_path = f"{config.INBOX_LOCAL_DIR_PATH}/{filename}"

            def extract():
                engine = ParserFactory.get_parser(file_path, inbox_ctrl.log_manager)
                return engine.get_full_text()

            text = await run.io_bound(extract)
            state['file_content'] = text
        except Exception as e:
            state['file_content'] = f"❌ Неможливо відобразити вміст файлу.\nПомилка: {e}"

    def refresh_left_panel():
        left_panel.clear()
        with left_panel:
            with ui.card().classes('w-full p-2 shadow-sm border border-blue-200 bg-blue-50/50 mb-2'):
                ui.label('Завантажити у спільну папку').classes('font-bold text-blue-800 text-sm mb-1')
                ui.upload(multiple=True, auto_upload=True, on_upload=handle_upload).classes('w-full').props('color="blue" accept="*" flat')

            with ui.expansion(f'🔴 Вхідні ({len(state["personal_files"])})', value=True) \
                    .props('header-class="font-bold text-red-800 bg-red-50 rounded" dense').classes('w-full'):
                with ui.column().classes('w-full gap-2 mt-2'):
                    if not state['personal_files']:
                        ui.label('Немає файлів').classes('text-xs text-gray-400 italic pl-1')
                    else:
                        for f in state['personal_files']:
                            is_sel = (state['selected_file'] == f and state['selected_type'] == 'inbox_personal')
                            in_queue = is_queued(f)

                            bg_color = 'bg-amber-50 border-amber-300' if in_queue else ('bg-red-100 border-red-300' if is_sel else 'bg-white hover:bg-gray-100 border-gray-200')
                            icon_name = 'hourglass_empty' if in_queue else 'description'
                            icon_color = 'amber-500' if in_queue else ('red-500' if is_sel else 'gray-400')

                            with ui.row().classes(f'w-full p-2 border rounded cursor-pointer items-center gap-2 flex-nowrap transition-colors {bg_color}') \
                                    .on('click', lambda fname=f: select_file(fname, 'inbox_personal')):
                                ui.icon(icon_name, color=icon_color)
                                ui.label(f).classes('text-sm truncate flex-grow font-medium' if is_sel or in_queue else 'text-sm truncate flex-grow text-gray-700')

            with ui.expansion(f'⚪ Спільні файли ({len(state["root_files"])})', value=True) \
                    .props('header-class="font-bold text-gray-700 bg-gray-100 rounded" dense').classes('w-full'):
                with ui.column().classes('w-full gap-2 mt-2'):
                    if not state['root_files']:
                        ui.label('Немає файлів').classes('text-xs text-gray-400 italic pl-1')
                    else:
                        for f in state['root_files']:
                            is_sel = (state['selected_file'] == f and state['selected_type'] == 'inbox_shared')
                            in_queue = is_queued(f)

                            bg_color = 'bg-amber-50 border-amber-300' if in_queue else ('bg-blue-100 border-blue-300' if is_sel else 'bg-white hover:bg-gray-100 border-gray-200')
                            icon_name = 'hourglass_empty' if in_queue else 'description'
                            icon_color = 'amber-500' if in_queue else ('blue-600' if is_sel else 'gray-400')

                            with ui.row().classes(f'w-full p-2 border rounded cursor-pointer items-center gap-2 flex-nowrap transition-colors {bg_color}') \
                                    .on('click', lambda fname=f: select_file(fname, 'inbox_shared')):
                                ui.icon(icon_name, color=icon_color)
                                ui.label(f).classes('text-sm truncate flex-grow font-medium' if is_sel or in_queue else 'text-sm truncate flex-grow text-gray-700')

            with ui.expansion(f'🟢 Вихідні (Outbox) ({len(state["outbox_files"])})', value=True) \
                    .props('header-class="font-bold text-green-800 bg-green-50 rounded" dense').classes('w-full'):
                with ui.column().classes('w-full gap-2 mt-2'):
                    if not state['outbox_files']:
                        ui.label('Немає файлів').classes('text-xs text-gray-400 italic pl-1')
                    else:
                        for f in state['outbox_files']:
                            is_sel = (state['selected_file'] == f and state['selected_type'] == 'outbox_personal')
                            in_queue = is_queued(f)

                            bg_color = 'bg-amber-50 border-amber-300' if in_queue else ('bg-green-100 border-green-300' if is_sel else 'bg-white hover:bg-gray-100 border-gray-200')
                            icon_name = 'hourglass_empty' if in_queue else 'outbox'
                            icon_color = 'amber-500' if in_queue else ('green-600' if is_sel else 'gray-400')

                            with ui.row().classes(f'w-full p-2 border rounded cursor-pointer items-center gap-2 flex-nowrap transition-colors {bg_color}') \
                                    .on('click', lambda fname=f: select_file(fname, 'outbox_personal')):
                                ui.icon(icon_name, color=icon_color)
                                ui.label(f).classes('text-sm truncate flex-grow font-medium' if is_sel or in_queue else 'text-sm truncate flex-grow text-gray-700')

    def refresh_right_panel():
        right_panel.clear()
        with right_panel:
            if not state['selected_file']:
                with ui.column().classes('w-full h-full items-center justify-center bg-gray-50'):
                    ui.icon('find_in_page', size='100px', color='gray-300')
                    ui.label('Оберіть документ ліворуч для перегляду та обробки').classes('text-gray-500 text-lg mt-4')
                return

            f_name = state['selected_file']
            f_type = state['selected_type']
            in_queue = is_queued(f_name)

            icon_color = 'red-500' if f_type == 'inbox_personal' else ('green-600' if f_type == 'outbox_personal' else 'blue-600')

            with ui.row().classes('w-full bg-gray-100 border-b border-gray-200 p-3 items-center justify-between shrink-0'):
                with ui.row().classes('items-center gap-3 overflow-hidden flex-grow'):
                    ui.icon('hourglass_empty' if in_queue else 'description', size='md', color='amber-500' if in_queue else icon_color)
                    ui.label(f_name).classes('text-lg font-bold truncate text-gray-800').tooltip(f_name)

                if in_queue:
                    with ui.row().classes('items-center gap-2 px-4 py-2 bg-amber-100 rounded border border-amber-300 shrink-0'):
                        ui.spinner('dots', size='sm', color='amber-700')
                        ui.label('Очікує в черзі...').classes('text-amber-800 font-bold text-sm')
                else:
                    with ui.row().classes('items-center gap-2 shrink-0 flex-nowrap'):
                        if f_type == 'inbox_personal':
                            ui.button('Завантажити', icon='download', on_click=lambda: download_file(f_name)) \
                                .props('color="green" size="sm" stack').classes('w-24 h-14')
                            ui.button('Задача', icon='add_task', on_click=lambda: ui.notify('TODO: Задача', type='info')) \
                                .props('color="primary" size="sm" stack').classes('w-24 h-14')

                            if can_assign:
                                sel_assign = ui.select(user_options, label='Кому').props('dense outlined hide-bottom-space').classes('w-32 h-14')
                                ui.button('Віддати', icon='switch_account',
                                          on_click=lambda: add_to_queue('assign', config.INBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=True)) \
                                    .props('color="secondary" size="sm" stack').classes('w-24 h-14')

                            ui.button('Видалити', icon='delete', on_click=lambda: confirm_and_queue_delete(config.INBOX_DIR_PATH, f_name, True)) \
                                .props('color="red" size="sm" stack').classes('w-20 h-14')

                        elif f_type == 'inbox_shared':
                            ui.button('Архів', icon='archive', on_click=lambda: add_to_queue('archive', config.INBOX_DIR_PATH, f_name)) \
                                .props('color="blue" size="sm" stack').classes('w-24 h-14')
                            ui.button('Ексель', icon='table_chart', on_click=lambda: add_to_queue('excel', config.INBOX_DIR_PATH, f_name)) \
                                .props('color="green" size="sm" stack').classes('w-24 h-14')

                            if can_assign:
                                sel_assign = ui.select(user_options, label='Оберіть юзера').props('dense outlined hide-bottom-space').classes('w-40 h-14')
                                ui.button('Призначити', icon='person_add',
                                          on_click=lambda: add_to_queue('assign', config.INBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=False)) \
                                    .props('color="secondary" size="sm" stack').classes('w-28 h-14')

                            ui.button('Видалити', icon='delete', on_click=lambda: confirm_and_queue_delete(config.INBOX_DIR_PATH, f_name, False)) \
                                .props('color="red" size="sm" stack').classes('w-20 h-14')

                        elif f_type == 'outbox_personal':
                            if can_assign:
                                sel_assign = ui.select(user_options, label='Кому').props('dense outlined hide-bottom-space').classes('w-32 h-14')
                                ui.button('Призначити', icon='switch_account',
                                          on_click=lambda: add_to_queue('assign', config.OUTBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=True)) \
                                    .props('color="secondary" size="sm" stack').classes('w-28 h-14')

                            ui.button('Видалити', icon='delete', on_click=lambda: confirm_and_queue_delete(config.OUTBOX_DIR_PATH, f_name, True)) \
                                .props('color="red" size="sm" stack').classes('w-20 h-14')

            with ui.column().classes('w-full flex-1 p-0 m-0 bg-white relative overflow-hidden'):
                if state['is_loading_content']:
                    with ui.column().classes('absolute inset-0 items-center justify-center bg-white/80 z-10'):
                        ui.spinner('dots', size='xl', color='primary')
                        ui.label('Читання документу...').classes('text-gray-500 mt-2')

                with ui.scroll_area().classes('w-full h-full p-4'):
                    ui.label().bind_text(state, 'file_content').classes(
                        'whitespace-pre-wrap text-gray-800 font-mono text-sm'
                    )

    async def download_file(filename: str):
        try:
            file_buffer = await run.io_bound(inbox_ctrl.download_personal_file, ctx, filename)
            if file_buffer: ui.download(file_buffer.getvalue(), filename)
        except Exception:
            pass

    async def confirm_and_queue_delete(folder: str, filename: str, is_personal: bool):
        dialog = ui.dialog()
        with dialog, ui.card().classes('p-4 min-w-[300px]'):
            ui.label(f'Видалити "{filename}"?').classes('font-bold')
            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ui.button('Ні', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                ui.button('Так', on_click=lambda: dialog.submit(True)).props('color="red"')

        if await dialog:
            add_to_queue('delete', folder, filename, is_personal=is_personal)

    ui.timer(0.1, load_data, once=True)