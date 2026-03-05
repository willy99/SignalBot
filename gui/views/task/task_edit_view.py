from nicegui import ui
from datetime import datetime
from gui.services.request_context import RequestContext
from domain.task import Task
from gui.controllers.task_controller import TaskController
from service.constants import TASK_STATUS_NEW, TASK_STATUS_COMPLETED
from dics.deserter_xls_dic import TASK_TYPES

def render_task_edit_page(controller: TaskController, ctx: RequestContext, task_id: int = None):
    is_new = task_id is None
    page_title = 'Створення нової задачі' if is_new else f'Редагування задачі №{task_id}'

    ui.label(page_title).classes('w-full text-center text-3xl font-bold mb-6')

    # Стейт форми
    state = {
        'id': task_id,
        'task_subject': '',
        'task_details': '',
        'task_type': 'Документація',
        'assignee': ctx.user_id,
        'task_deadline': '',
        'task_status': TASK_STATUS_NEW  # За замовчуванням
    }

    users_list = controller.get_available_users()
    users_options = {}
    for u in users_list:
        if not u.get('is_active'):
            continue
        user_id = u['id']
        display_name = u.get('full_name') or u.get('username') or f"Користувач {user_id}"
        if user_id == ctx.user_id:
            users_options[user_id] = f"{display_name} (Ви)"
        else:
            users_options[user_id] = display_name
    type_options = list(TASK_TYPES.keys())

    # --- ЗАВАНТАЖЕННЯ ДАНИХ (Якщо це редагування) ---
    if not is_new:
        existing_task = controller.get_task_by_id(ctx, task_id)
        if existing_task:
            state['task_subject'] = existing_task.task_subject
            state['task_details'] = existing_task.task_details or ''
            state['task_type'] = existing_task.task_type or 'Інше'
            state['assignee'] = existing_task.assignee
            state['task_status'] = existing_task.task_status
            if existing_task.task_deadline:
                # Конвертуємо datetime в рядок для UI
                state['task_deadline'] = existing_task.task_deadline.strftime('%d.%m.%Y %H:%M')
        else:
            ui.notify('Задачу не знайдено!', type='negative')
            ui.navigate.to('/tasks')
            return

    # --- МАЛЮЄМО ФОРМУ ---
    with ui.card().classes('w-full max-w-4xl mx-auto p-6 shadow-md'):

        # 1. Рядок: Статус, Виконавець, Тип
        with ui.row().classes('w-full items-center gap-4 mb-4'):

            # Статус (просто кольоровий бейдж, змінюється на дошці)
            badge_color = 'green' if state['task_status'] == TASK_STATUS_COMPLETED else 'blue'
            with ui.row().classes('items-center gap-2'):
                ui.label('Статус:').classes('text-gray-500 font-medium')
                ui.badge(state['task_status'], color=badge_color).classes('text-sm px-2 py-1')

            # Випадаючі списки
            ui.select(users_options, label='Виконавець (Кому)').bind_value(state, 'assignee').classes('flex-1')
            ui.select(type_options, label='Тип задачі').bind_value(state, 'task_type').classes('w-1/4')

        # 2. Тема задачі
        ui.input('Короткий заголовок (Тема)').bind_value(state, 'task_subject').classes(
            'w-full mb-4 text-lg font-medium').props('autofocus outlined')

        # 3. Детальний опис
        ui.textarea('Детальний опис задачі').bind_value(state, 'task_details').classes('w-full mb-4').props(
            'outlined rows=6')

        # 4. Дедлайн (Використовуємо поле з іконкою календаря/годинника)
        with ui.input('Дедлайн (ДД.ММ.РРРР ГГ:ХХ)').bind_value(state, 'task_deadline').classes('w-1/3 mb-6').props(
                'outlined clearable') as deadline_input:
            with deadline_input.add_slot('append'):
                ui.icon('event').classes('cursor-pointer')
                with ui.menu().classes('p-2'):
                    ui.date().bind_value(state, 'task_deadline').props('mask="DD.MM.YYYY HH:mm"')
                    ui.time().bind_value(state, 'task_deadline').props('mask="DD.MM.YYYY HH:mm" format24h')

        ui.separator().classes('mb-4')

        # --- ОБРОБНИК ЗБЕРЕЖЕННЯ ---
        def on_save():
            if not state['task_subject'].strip():
                ui.notify('Введіть тему задачі!', type='warning')
                return

            # Парсимо дедлайн назад у datetime, якщо він є
            parsed_deadline = None
            if state['task_deadline']:
                try:
                    parsed_deadline = datetime.strptime(state['task_deadline'], '%d.%m.%Y %H:%M')
                except ValueError:
                    ui.notify('Невірний формат дати. Використовуйте ДД.ММ.РРРР ГГ:ХХ', type='negative')
                    return

            # Створюємо об'єкт Pydantic
            # Примітка: Task імпортуємо з вашого сервісу
            task_model = Task(
                id=state['id'],
                created_by=ctx.user_id,  # Якщо це редагування, сервіс проігнорує це поле і залишить старого автора
                assignee=state['assignee'],
                task_status=state['task_status'],
                task_type=state['task_type'],
                task_subject=state['task_subject'].strip(),
                task_details=state['task_details'].strip(),
                task_deadline=parsed_deadline
            )

            try:
                # Зберігаємо через контролер
                saved_id = controller.save_task(ctx, task_model)
                ui.notify(f'Задачу №{saved_id} успішно збережено!', type='positive')
                ui.navigate.to('/tasks')  # Повертаємось на дошку
            except Exception as e:
                ui.notify(f'Помилка збереження: {e}', type='negative')

        # 5. Кнопки управління
        with ui.row().classes('w-full justify-between items-center'):
            ui.button('Скасувати', icon='close', on_click=lambda: ui.navigate.to('/tasks')).props('flat color="gray"')
            ui.button('Зберегти задачу', icon='save', on_click=on_save).props('color="primary" size="lg"').classes(
                'px-8')