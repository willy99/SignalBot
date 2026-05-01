from nicegui import ui
from datetime import datetime
from gui.services.auth_manager import AuthManager
from domain.task import Task, Subtask
from gui.controllers.task_controller import TaskController
from gui.tools.ui_components import confirm_delete_dialog
from service.constants import TASK_STATUS_NEW, TASK_STATUS_COMPLETED, TASK_STATUS_IN_PROGRESS, TASK_STATUS_CANCELED
from dics.deserter_xls_dic import TASK_TYPES


def render_task_edit_page(controller: TaskController, auth_manager: AuthManager, task_id: int = None):
    is_new = task_id is None
    page_title = 'Створення нової задачі' if is_new else f'Редагування задачі №{task_id}'

    # Стейт форми (додано 'new_subtask_text' для синхронізації інпутів на моб/ПК)
    state = {
        'id': task_id,
        'task_subject': '',
        'task_details': '',
        'task_type': 'Документація',
        'assignee': auth_manager.get_current_context().user_id,
        'task_deadline': '',
        'task_status': TASK_STATUS_NEW,
        'subtasks': [],
        'new_subtask_text': ''
    }

    users_list = controller.get_available_users()
    users_options = {}
    for u in users_list:
        if not u.get('is_active'):
            continue
        user_id = u['id']
        display_name = u.get('full_name') or u.get('username') or f"Користувач {user_id}"
        if user_id == auth_manager.get_current_context().user_id:
            users_options[user_id] = f"{display_name} (Ви)"
        else:
            users_options[user_id] = display_name
    type_options = list(TASK_TYPES.keys())

    # --- ЗАВАНТАЖЕННЯ ДАНИХ ---
    if not is_new:
        existing_task = controller.get_task_by_id(auth_manager.get_current_context(), task_id)
        if existing_task:
            state['task_subject'] = existing_task.task_subject
            state['task_details'] = existing_task.task_details or ''
            state['task_type'] = existing_task.task_type or 'Інше'
            state['assignee'] = existing_task.assignee
            state['task_status'] = existing_task.task_status
            if existing_task.subtasks:
                state['subtasks'] = [{'title': st.title, 'is_done': st.is_done} for st in existing_task.subtasks]

            if existing_task.task_deadline:
                state['task_deadline'] = existing_task.task_deadline.strftime('%d.%m.%Y %H:%M')
        else:
            ui.notify('Задачу не знайдено!', type='negative')
            ui.navigate.to('/tasks')
            return

    # --- ОБРОБНИКИ ДІЙ ---
    def on_save():
        if not state['task_subject'].strip():
            ui.notify('Введіть тему задачі!', type='warning')
            return

        parsed_deadline = None
        if state['task_deadline']:
            try:
                parsed_deadline = datetime.strptime(state['task_deadline'], '%d.%m.%Y %H:%M')
            except ValueError:
                ui.notify('Невірний формат дати. Використовуйте ДД.ММ.РРРР ГГ:ХХ', type='negative')
                return

        parsed_subtasks = [Subtask(title=st['title'], is_done=st['is_done']) for st in state.get('subtasks', [])]

        task_model = Task(
            id=state['id'],
            created_by=auth_manager.get_current_context().user_id,
            assignee=state['assignee'],
            task_status=state['task_status'],
            task_type=state['task_type'],
            task_subject=state['task_subject'].strip(),
            task_details=state['task_details'].strip(),
            task_deadline=parsed_deadline,
            subtasks=parsed_subtasks
        )

        try:
            saved_id = controller.save_task(auth_manager.get_current_context(), task_model)
            ui.notify(f'Задачу №{saved_id} успішно збережено!', type='positive')
            ui.navigate.to('/tasks')
        except Exception as e:
            ui.notify(f'Помилка збереження: {e}', type='negative')

    async def on_delete():
        result = await confirm_delete_dialog(f'Видалити задачу №{task_id}?')
        if result:
            try:
                controller.delete_task(auth_manager.get_current_context(), task_id)
                ui.notify('Задачу видалено', type='positive')
                ui.navigate.to('/tasks')
            except Exception as e:
                ui.notify(f'Помилка видалення: {e}', type='negative')

    def change_status(new_status: str):
        state['task_status'] = new_status
        on_save()
        header_buttons.refresh()
        status_badge.refresh()
        ui.notify(f'Статус змінено на: {new_status}')

    # --- ПІДЗАДАЧІ ---
    @ui.refreshable
    def render_subtasks():
        subtasks = state.get('subtasks', [])
        if subtasks:
            completed = sum(1 for st in subtasks if st.get('is_done'))
            total = len(subtasks)
            progress = completed / total if total > 0 else 0
            ui.linear_progress(progress, show_value=False).props('color="green"').classes('mb-2')
            ui.label(f'Виконано: {completed} з {total}').classes('text-xs text-gray-500 mb-2')

        with ui.column().classes('w-full gap-1'):
            for idx, st in enumerate(subtasks):
                with ui.row().classes('w-full items-center justify-between group hover:bg-gray-50 p-1 rounded transition-colors flex-nowrap'):
                    with ui.row().classes('items-center gap-2 flex-grow overflow-hidden'):
                        ui.checkbox().bind_value(st, 'is_done').on('change', render_subtasks.refresh)
                        text_classes = 'text-gray-400 text-sm truncate line-through' if st.get('is_done') else 'text-gray-800 text-sm truncate'
                        ui.label(st['title']).classes(text_classes)
                    ui.button(icon='close', on_click=lambda i=idx: remove_subtask(i)).props('flat dense size="sm" color="red"').classes('opacity-50 hover:opacity-100')

    def add_subtask(e=None):
        val = state.get('new_subtask_text', '')
        if val and val.strip():
            state['subtasks'].append({'title': val.strip(), 'is_done': False})
            state['new_subtask_text'] = ''  # Очищаємо поле
            render_subtasks.refresh()

    def remove_subtask(index):
        state['subtasks'].pop(index)
        render_subtasks.refresh()

    # ==========================================
    # UI КОМПОНЕНТИ (Функції)
    # ==========================================

    @ui.refreshable
    def header_buttons():
        with ui.row().classes('items-center gap-2 flex-wrap'):
            if not is_new:
                ui.button('ВИДАЛИТИ', icon='delete', on_click=on_delete).props('color="red"').classes('h-10 flex-grow sm:flex-grow-0')

            ui.button('СКАСУВАТИ', icon='close', on_click=lambda: ui.navigate.to('/tasks')).props('color="gray" text-color="black"').classes('h-10 flex-grow sm:flex-grow-0')

            if state['task_status'] == TASK_STATUS_NEW:
                ui.button('РОЗПОЧАТИ', icon='play_arrow', on_click=lambda: change_status(TASK_STATUS_IN_PROGRESS)) \
                    .props('color="orange"').classes('h-10 flex-grow sm:flex-grow-0')
            elif state['task_status'] == TASK_STATUS_IN_PROGRESS:
                ui.button('ЗАВЕРШИТИ', icon='check_circle', on_click=lambda: change_status(TASK_STATUS_COMPLETED)) \
                    .props('color="green"').classes('h-10 flex-grow sm:flex-grow-0')

            ui.button('ЗБЕРЕГТИ', icon='save', on_click=on_save).props('color="primary"').classes('h-10 px-8 shadow-md flex-grow sm:flex-grow-0')

    @ui.refreshable
    def status_badge():
        colors = {
            TASK_STATUS_NEW: 'blue',
            TASK_STATUS_IN_PROGRESS: 'orange',
            TASK_STATUS_COMPLETED: 'green',
            TASK_STATUS_CANCELED: 'red'
        }
        color = colors.get(state['task_status'], 'gray')
        with ui.row().classes('items-center justify-between w-full border-b border-gray-100 pb-3 mb-2'):
            ui.label('Статус:').classes('text-gray-600 font-bold')
            ui.badge(state['task_status'], color=color).classes('text-sm px-2 py-1')

    def render_main_content():
        """Ліва колонка (Основна інформація)"""
        ui.input('Короткий заголовок (Тема)').bind_value(state, 'task_subject').classes(
            'w-full mb-4 text-lg font-bold').props('autofocus outlined')

        ui.label('Детальний опис задачі').classes('text-sm text-gray-500 font-medium mb-1')
        ui.editor(placeholder='Опишіть задачу, додайте деталі...').bind_value(state, 'task_details').classes(
            'w-full mb-6 border border-gray-300 rounded'
        )

        ui.label('Чек-ліст (Підзадачі)').classes('text-sm text-gray-500 font-medium mb-1')
        with ui.card().classes('w-full p-4 mb-2 shadow-none border border-gray-200 bg-gray-50/50'):
            render_subtasks()
            with ui.row().classes('w-full items-center gap-2 mt-2 flex-nowrap'):
                ui.icon('add_task', color='gray-400')
                new_subtask_input = ui.input(placeholder='Додати нову підзадачу...').bind_value(state, 'new_subtask_text').classes('flex-grow').props('dense borderless')
                new_subtask_input.on('keydown.enter', add_subtask)
                ui.button('Додати', on_click=add_subtask).props('flat color="primary" size="sm"')

    def render_side_panel():
        """Права колонка (Параметри)"""
        status_badge()
        ui.select(users_options, label='Виконавець (Кому)').bind_value(state, 'assignee').classes('w-full')
        ui.select(type_options, label='Тип задачі').bind_value(state, 'task_type').classes('w-full')

        with ui.input('Дедлайн').bind_value(state, 'task_deadline').classes('w-full').props('outlined clearable') as deadline_input:
            with deadline_input.add_slot('append'):
                ui.icon('event').classes('cursor-pointer')
                with ui.menu().classes('p-2'):
                    ui.date().bind_value(state, 'task_deadline').props('mask="DD.MM.YYYY HH:mm"')
                    ui.time().bind_value(state, 'task_deadline').props('mask="DD.MM.YYYY HH:mm" format24h')

    # ==========================================
    # ВІДОБРАЖЕННЯ СТОРІНКИ
    # ==========================================

    # Заголовок і кнопки
    with ui.row().classes('w-full max-w-6xl mx-auto items-center justify-between mb-6 flex-wrap gap-4 px-2 sm:px-0'):
        ui.label(page_title).classes('text-2xl sm:text-3xl font-bold truncate w-full sm:w-auto text-center sm:text-left')
        header_buttons()

    # 💻 ДЕСКТОПНА ВЕРСІЯ (Дві колонки: 8 та 4)
    # Використовуємо gt-sm (Greater Than Small - видимо на комп'ютерах)
    with ui.grid(columns=12).classes('gt-sm w-full max-w-6xl mx-auto gap-6 items-start'):
        with ui.column().classes('col-span-8 w-full gap-4'):
            with ui.card().classes('w-full p-6 shadow-md'):
                render_main_content()

        with ui.column().classes('col-span-4 w-full gap-4'):
            with ui.card().classes('w-full p-6 shadow-md gap-4'):
                render_side_panel()

    # 📱 МОБІЛЬНА ВЕРСІЯ (Гармошка)
    # Використовуємо lt-md (Less Than Medium - видимо на телефонах і планшетах)
    with ui.column().classes('lt-md w-full gap-3 px-2 pb-8'):
        with ui.expansion('Основна інформація', icon='edit_document', group='mobile_task', value=True) \
                .classes('w-full bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden') \
                .props('header-class="bg-blue-50 text-blue-900 font-bold"'):
            with ui.column().classes('p-4 w-full'):
                render_main_content()

        with ui.expansion('Параметри та Дедлайн', icon='settings', group='mobile_task') \
                .classes('w-full bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden') \
                .props('header-class="bg-orange-50 text-orange-900 font-bold"'):
            with ui.column().classes('p-4 w-full'):
                render_side_panel()