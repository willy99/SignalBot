from nicegui import ui, run, events

from dics.security_config import PERM_DELETE, MODULE_TASK, MODULE_PERSON, PERM_EDIT
from gui.controllers.inbox_controller import InboxController
from gui.controllers.task_controller import TaskController
from gui.services.auth_manager import AuthManager
import config
import os
import regex as re
from gui.tools.ui_components import confirm_delete_dialog
from service.processing.parsers.ParserFactory import ParserFactory
from domain.person import Person
from gui.controllers.person_controller import PersonController
from gui.views.person.person_view import edit_person

# Дозволені розширення файлів для завантаження
_ALLOWED_EXTENSIONS = {'.doc', '.docx', '.pdf', '.txt', '.jpg', '.jpeg', '.png', '.xlsx', '.xls'}


def _safe_filename(name: str) -> str:
    """Захист від Path Traversal"""
    name = os.path.basename(name)
    name = re.sub(r'[^\w.\- ]', '_', name, flags=re.UNICODE).strip()
    if not name: raise ValueError("Ім'я файлу не може бути порожнім")
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Тип файлу '{ext}' не дозволений.")
    return name


def render_inbox_page(inbox_ctrl: InboxController, task_ctrl: TaskController, person_ctrl: PersonController, auth_manager: AuthManager):
    can_assign = auth_manager.has_access(MODULE_TASK, PERM_DELETE)
    can_edit = auth_manager.has_access(MODULE_PERSON, PERM_EDIT)
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
        'is_processing_queue': False,
        # Стейт для гармошки на мобільному
        'mobile_folders_open': True,
        'mobile_content_open': False
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

        if state['is_processing_queue'] or q_len == 0: return

        state['is_processing_queue'] = True
        try:
            while state['action_queue']:
                action = state['action_queue'][0]
                fname = action['filename']
                folder = action['folder']
                atype = action['type']

                try:
                    if atype == 'archive':
                        ui.notify(f'⏳ Архів: збереження {fname}...', type='info')
                        u_login = auth_manager.get_current_context().user_login if action.get('is_personal') else None
                        success = await auth_manager.execute(inbox_ctrl.archive_file, auth_manager.get_current_context(), u_login, fname)
                        if success:
                            ui.notify(f'✅ {fname} архівовано!', type='positive')
                            await auth_manager.execute(inbox_ctrl.delete_file, auth_manager.get_current_context(), u_login, folder, fname)
                        else:
                            ui.notify(f'❌ Помилка архівації {fname}', type='negative')

                    elif atype == 'delete':
                        u_login = auth_manager.get_current_context().user_login if action.get('is_personal') else None
                        await auth_manager.execute(inbox_ctrl.delete_file, auth_manager.get_current_context(), u_login, folder, fname)
                        ui.notify(f'🗑️ {fname} успішно видалено', type='positive')

                    elif atype == 'assign':
                        target = action['target']
                        is_pers = action.get('is_personal', False)
                        f_folder = action.get('folder')
                        await auth_manager.execute(
                            inbox_ctrl.assign_file, auth_manager.get_current_context(),
                            fname, is_pers, target, f_folder
                        )
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
            'type': action_type, 'filename': filename, 'folder': folder, **kwargs
        })
        ui.notify(f'Додано в чергу: {filename}', type='info')
        render_left_panel.refresh()
        render_right_panel.refresh()

    def is_queued(filename: str) -> bool:
        return any(a['filename'] == filename for a in state['action_queue'])

    async def handle_upload(e: events.UploadEventArguments):
        try:
            filename = _safe_filename(e.file.name)
            file_data = await e.file.read()
            await auth_manager.execute(inbox_ctrl.upload_root_file, auth_manager.get_current_context(), filename, file_data)
            ui.notify(f'Файл "{filename}" завантажено!', type='positive')
            e.sender.reset()
            await load_data()
        except ValueError as ex:
            ui.notify(f'Файл відхилено: {ex}', type='warning')
        except Exception as ex:
            ui.notify(f'Помилка завантаження: {ex}', type='negative')

    async def load_data():
        try:
            data = await auth_manager.execute(inbox_ctrl.get_user_inbox_messages, auth_manager.get_current_context())
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

            render_left_panel.refresh()
            render_right_panel.refresh()
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

        # Магія для мобільного: автоматично закриваємо папки і відкриваємо контент
        state['mobile_folders_open'] = False
        state['mobile_content_open'] = True

        render_left_panel.refresh()
        render_right_panel.refresh()

        await load_file_content(filename, f_type)

        state['is_loading_content'] = False
        render_right_panel.refresh()

    async def load_file_content(filename: str, f_type: str):
        try:
            safe_name = os.path.basename(filename)
            if f_type == 'inbox_personal':
                file_path = os.path.join(config.INBOX_LOCAL_DIR_PATH, auth_manager.get_current_context().user_login, safe_name)
            elif f_type == 'outbox_personal':
                file_path = os.path.join(config.OUTBOX_LOCAL_DIR_PATH, auth_manager.get_current_context().user_login, safe_name)
            else:
                file_path = os.path.join(config.INBOX_LOCAL_DIR_PATH, safe_name)

            def extract(ctx):
                engine = ParserFactory.get_parser(file_path, inbox_ctrl.log_manager)
                return engine.get_full_text()

            text = await auth_manager.execute(extract, auth_manager.get_current_context())
            state['file_content'] = text
        except Exception as e:
            state['file_content'] = f"❌ Неможливо відобразити вміст файлу.\nПомилка: {e}"

    async def on_process_excel_click(filename: str, folder: str):
        ui.notify('⏳ Розпізнаю документ...', type='info')
        try:
            parsed_data_list, messages = await auth_manager.execute(inbox_ctrl.parse_file_for_review, auth_manager.get_current_context(), folder, filename)
            if messages:
                for msg in messages: ui.notify(msg, type='warning')
            if not parsed_data_list:
                ui.notify('❌ Не вдалося знайти дані людей у документі', type='warning')
                clear_selection()
                await load_data()
                return

            for raw_dict in parsed_data_list:
                new_person = Person.from_excel_dict(raw_dict)
                new_person.id = None
                dialog = edit_person(person=new_person, person_ctrl=person_ctrl, auth_manager=auth_manager, on_close=None)
                await dialog
            ui.notify('✅ Всіх знайдених осіб оброблено!', type='positive')
            clear_selection()
            await load_data()

        except Exception as e:
            ui.notify(f'Помилка обробки: {e}', type='negative')

    async def download_file(filename: str, f_type: str):
        try:
            if f_type == 'inbox_personal':
                file_buffer = await auth_manager.execute(inbox_ctrl.download_file, auth_manager.get_current_context(), filename, config.INBOX_DIR_PATH, True)
            elif f_type == 'outbox_personal':
                file_buffer = await auth_manager.execute(inbox_ctrl.download_file, auth_manager.get_current_context(), filename, config.OUTBOX_DIR_PATH, True)
            else:
                file_buffer = await auth_manager.execute(inbox_ctrl.download_file, auth_manager.get_current_context(), filename, config.INBOX_DIR_PATH, False)
            if file_buffer:
                ui.download(file_buffer.getvalue(), filename)
                ui.notify(f'Завантаження {filename} почалося.', type='positive')
            else:
                ui.notify('Не вдалося завантажити файл.', type='negative')
        except Exception as e:
            ui.notify(f'Помилка завантаження: {e}', type='negative')

    async def confirm_and_queue_delete(folder: str, filename: str, is_personal: bool):
        result = await confirm_delete_dialog(f'Видалити "{filename}"?')
        if result: add_to_queue('delete', folder, filename, is_personal=is_personal)

    # ==========================================
    # UI КОМПОНЕНТИ (Функції)
    # ==========================================

    @ui.refreshable
    def render_left_panel():
        with ui.column().classes('w-full h-full p-2 gap-4'):
            with ui.card().classes('w-full p-2 shadow-sm border border-blue-200 bg-blue-50/50 mb-2'):
                ui.label('Завантажити у спільну папку').classes('font-bold text-blue-800 text-sm mb-1')
                ui.upload(multiple=True, auto_upload=True, on_upload=handle_upload).classes('w-full') \
                    .props('color="blue" accept=".doc,.docx,.pdf,.txt,.jpg,.jpeg,.png,.xlsx,.xls" flat')

            with ui.expansion(f'🔴 Вхідні (Inbox) ({len(state["personal_files"])})', value=True) \
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

    @ui.refreshable
    def render_right_panel():
        with ui.column().classes('w-full h-full flex flex-col p-0 overflow-hidden'):
            if not state['selected_file']:
                with ui.column().classes('w-full h-full items-center justify-center bg-gray-50 flex-grow'):
                    ui.icon('find_in_page', size='100px', color='gray-300')
                    ui.label('Оберіть документ для перегляду').classes('text-gray-500 text-lg mt-4 text-center px-4')
                return

            f_name = state['selected_file']
            f_type = state['selected_type']
            in_queue = is_queued(f_name)
            icon_color = 'red-500' if f_type == 'inbox_personal' else ('green-600' if f_type == 'outbox_personal' else 'blue-600')

            # 🪄 МАГІЯ: Помічник для адаптивних кнопок
            def resp_btn(text, icon_name, color, on_click_fn):
                # 💻 Для ПК: Текст + Іконка (stack)
                ui.button(text, icon=icon_name, on_click=on_click_fn) \
                    .props(f'color="{color}" size="sm" stack').classes('gt-sm w-20 xl:w-24 h-14')
                # 📱 Для мобільного: Тільки іконка
                ui.button(icon=icon_name, on_click=on_click_fn) \
                    .props(f'color="{color}" size="md" padding="sm"').classes('lt-md').tooltip(text)

            # Хедер файла з кнопками
            with ui.row().classes('w-full bg-gray-100 border-b border-gray-200 p-2 sm:p-3 items-center justify-between shrink-0 flex-wrap gap-2'):
                with ui.row().classes('items-center gap-2 overflow-hidden flex-grow min-w-[150px]'):
                    ui.icon('hourglass_empty' if in_queue else 'description', size='md', color='amber-500' if in_queue else icon_color)
                    ui.label(f_name).classes('text-base sm:text-lg font-bold truncate text-gray-800').tooltip(f_name)

                if in_queue:
                    with ui.row().classes('items-center gap-2 px-4 py-2 bg-amber-100 rounded border border-amber-300 shrink-0'):
                        ui.spinner('dots', size='sm', color='amber-700')
                        ui.label('Очікує в черзі...').classes('text-amber-800 font-bold text-sm')
                else:
                    # Контейнер для кнопок
                    with ui.row().classes('items-center gap-1 sm:gap-2 shrink-0 flex-wrap justify-end'):

                        if f_type == 'inbox_personal':
                            resp_btn('Завант.', 'download', 'blue', lambda: download_file(f_name, f_type))

                            if can_assign:
                                sel_assign = ui.select(user_options, label='Кому').props('dense outlined hide-bottom-space').classes('w-24 sm:w-32')
                                resp_btn('Призначити', 'switch_account', 'blue',
                                         lambda: add_to_queue('assign', config.INBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=True))

                            if can_edit:
                                resp_btn('Архів', 'archive', 'blue', lambda: add_to_queue('archive', config.INBOX_DIR_PATH, f_name))
                                resp_btn('В базу', 'person_add', 'green', lambda: on_process_excel_click(f_name, auth_manager.get_current_context().user_login))

                            resp_btn('Видалити', 'delete', 'red', lambda: confirm_and_queue_delete(config.INBOX_DIR_PATH, f_name, True))

                        elif f_type == 'inbox_shared':
                            resp_btn('Завант.', 'download', 'blue', lambda: download_file(f_name, f_type))
                            resp_btn('Архів', 'archive', 'blue', lambda: add_to_queue('archive', config.INBOX_DIR_PATH, f_name))
                            resp_btn('В базу', 'person_add', 'green', lambda: on_process_excel_click(f_name, None))

                            if can_assign:
                                sel_assign = ui.select(user_options, label='Оберіть юзера').props('dense outlined hide-bottom-space').classes('w-24 sm:w-32')
                                resp_btn('Призначити', 'switch_account', 'blue',
                                         lambda: add_to_queue('assign', config.INBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=False))

                            resp_btn('Видалити', 'delete', 'red', lambda: confirm_and_queue_delete(config.INBOX_DIR_PATH, f_name, False))

                        elif f_type == 'outbox_personal':
                            resp_btn('Завант.', 'download', 'blue', lambda: download_file(f_name, f_type))

                            if can_assign:
                                sel_assign = ui.select(user_options, label='Кому').props('dense outlined hide-bottom-space').classes('w-24 sm:w-32')
                                resp_btn('Призначити', 'switch_account', 'blue',
                                         lambda: add_to_queue('assign', config.OUTBOX_DIR_PATH, f_name, target=sel_assign.value, is_personal=True))

                            resp_btn('Видалити', 'delete', 'red', lambda: confirm_and_queue_delete(config.OUTBOX_DIR_PATH, f_name, True))

            # Блок контенту
            with ui.column().classes('w-full flex-grow p-0 m-0 bg-white relative overflow-hidden'):
                if state['is_loading_content']:
                    with ui.column().classes('absolute inset-0 items-center justify-center bg-white/80 z-10'):
                        ui.spinner('dots', size='xl', color='primary')
                        ui.label('Читання документу...').classes('text-gray-500 mt-2')

                with ui.scroll_area().classes('w-full h-full p-4'):
                    ui.label().bind_text(state, 'file_content').classes('whitespace-pre-wrap text-gray-800 font-mono text-sm')

    # ==========================================
    # ВІДОБРАЖЕННЯ СТОРІНКИ
    # ==========================================

    # 💻 ДЕСКТОПНА ВЕРСІЯ (Дві колонки поруч, gt-sm)
    with ui.row().classes('gt-sm w-full h-[calc(100vh-140px)] flex-nowrap px-4 gap-4'):
        with ui.column().classes('w-1/3 max-w-[350px] h-full overflow-y-auto shrink-0 border border-gray-200 rounded-lg bg-gray-50 p-0 shadow-inner'):
            render_left_panel()
        with ui.column().classes('flex-grow h-full border border-gray-200 rounded-lg p-0 bg-white shadow-sm flex flex-col overflow-hidden'):
            render_right_panel()

    # 📱 МОБІЛЬНА ВЕРСІЯ (Гармошка, lt-md)
    with ui.column().classes('lt-md w-full gap-3 px-2 pb-8 h-[calc(100vh-100px)] overflow-y-auto'):

        with ui.expansion('📁 Папки та Файли', group='mobile_inbox') \
                .bind_value(state, 'mobile_folders_open') \
                .classes('w-full bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden') \
                .props('header-class="bg-blue-50 text-blue-900 font-bold"'):
            with ui.column().classes('p-0 w-full bg-gray-50/50'):
                render_left_panel()

        with ui.expansion('📄 Вміст та Дії', group='mobile_inbox') \
                .bind_value(state, 'mobile_content_open') \
                .classes('w-full bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden') \
                .props('header-class="bg-green-50 text-green-900 font-bold"'):
            # Задаємо фіксовану висоту для контенту на мобільному, щоб scroll_area працювала
            with ui.column().classes('p-0 w-full h-[65vh] flex flex-col'):
                render_right_panel()

    # Початкове завантаження
    ui.timer(0.1, load_data, once=True)