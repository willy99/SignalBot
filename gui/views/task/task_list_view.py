from nicegui import ui
from gui.services.request_context import RequestContext
from domain.task import *
from gui.controllers.task_controller import TaskController
from datetime import timedelta
from service.constants import TASK_STATUS_COMPLETED, TASK_STATUS_NEW, TASK_STATUS_IN_PROGRESS
# Словник іконок для різних типів задач
def get_type_icon(task_type: str) -> str:
    icons = {
        'Документація': 'description',  # Класичний аркуш тексту
        'Запити': 'manage_search',  # Або залишіть 'search' чи 'contact_mail'
        'Фікс Даних': 'bug_report',  # Важливо: саме bug_report!
        'Програмірувай': 'code'  # Або 'terminal' / 'developer_mode'
    }
    return icons.get(task_type, 'task')


def get_card_colors(task, current_user_id: int) -> str:
    """Визначає колір картки за логікою власності, статусу та дедлайну"""
    # Якщо задача призначена НЕ мені — вона завжди сіра
    if task.assignee != current_user_id:
        return 'bg-gray-50 border-gray-400 text-gray-500'

    if task.task_status == TASK_STATUS_COMPLETED:
        return 'bg-green-50 border-green-500 text-green-900'

    # Якщо дедлайн є і він у минулому
    if task.task_deadline and task.task_deadline < datetime.now():
        return 'bg-red-50 border-red-500 text-red-900'

    # Всі інші (мої, в роботі або нові, не прострочені)
    return 'bg-blue-50 border-blue-500 text-blue-900'


async def delete_task_with_confirm(task_id: int, controller: TaskController, ctx: RequestContext, refresh_callback):
    """Викликає вікно підтвердження і видаляє задачу, якщо користувач згоден"""
    dialog = ui.dialog()
    with dialog, ui.card().classes('p-6 min-w-[300px]'):
        ui.label('Видалення задачі').classes('text-xl font-bold text-red-600 mb-2')
        ui.label('Ви дійсно хочете назавжди видалити цю задачу?').classes('text-gray-600 mb-6')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
            ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

    # Чекаємо, поки користувач натисне одну з кнопок
    result = await dialog

    if result:  # Якщо натиснув "Видалити" (повернулося True)
        try:
            controller.delete_task(ctx, task_id)
            ui.notify('Задачу успішно видалено', type='warning', icon='delete')
            refresh_callback()  # Перемальовуємо дошку
        except Exception as e:
            ui.notify(f'Помилка видалення: {e}', type='negative')

def render_task_list_page(controller: TaskController, ctx: RequestContext):
    ui.label('Дошка задач').classes('w-full text-center text-3xl font-bold mb-4')

    # Отримуємо список юзерів і робимо зручний словник {id: "Ім'я"}
    users_list = controller.get_available_users()
    users_map = {}
    filter_options = {'all': 'Всі задачі', ctx.user_id: 'Мої задачі'}

    for u in users_list:
        name = u.get('full_name') or u.get('username') or f"User {u['id']}"
        users_map[u['id']] = name
        if u['id'] != ctx.user_id:
            filter_options[u['id']] = name

    # Стейт для фільтра (за замовчуванням - мої задачі)
    state = {'assignee_filter': ctx.user_id}

    # Верхня панель: Фільтр + Кнопка створення
    def on_filter_change(e):
        state['assignee_filter'] = e.value
        refresh_board()

    with ui.row().classes('w-full justify-between items-center mb-4 px-4'):
        ui.select(
            filter_options,
            label='Фільтр за виконавцем',
            value=state['assignee_filter'],
            on_change=on_filter_change
        ).classes('w-64')
        ui.button('Створити нову', icon='add', on_click=lambda: ui.navigate.to('/tasks/edit/new')).props(
            'color="primary"')

    # Головний контейнер дошки (w-full - на всю ширину, bg-white)
    board_container = ui.row().classes(
        'w-full items-start justify-between gap-0 flex-nowrap bg-white border-y border-gray-200 shadow-sm')

    def refresh_board():
        board_container.clear()
        assignee_id_filter = None
        if state['assignee_filter'] != 'all':
            # tasks = [t for t in all_tasks if t.assignee == state['assignee_filter']]
            assignee_id_filter = state['assignee_filter']
        #else:
            #tasks = all_tasks

        tasks = controller.get_all_tasks(ctx, assignee_id_filter)

        # Розподіляємо по списках
        new_tasks = [t for t in tasks if t.task_status == TASK_STATUS_NEW]
        in_progress_tasks = [t for t in tasks if t.task_status == TASK_STATUS_IN_PROGRESS]
        completed_tasks = [t for t in tasks if t.task_status == TASK_STATUS_COMPLETED]

        with board_container:
            # СТОВПЧИК 1: NEW (додали border-r для тонкої роздільної лінії)
            with ui.column().classes('flex-1 p-4 min-h-[70vh] border-r border-gray-200'):
                ui.label(f'НОВІ ({len(new_tasks)})').classes(
                    'font-bold text-gray-500 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in new_tasks:
                    render_task_card(t, controller, ctx, refresh_board, users_map)

            # СТОВПЧИК 2: IN PROGRESS (border-r)
            with ui.column().classes('flex-1 p-4 min-h-[70vh] border-r border-gray-200'):
                ui.label(f'В РОБОТІ ({len(in_progress_tasks)})').classes(
                    'font-bold text-blue-500 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in in_progress_tasks:
                    render_task_card(t, controller, ctx, refresh_board, users_map)

            # СТОВПЧИК 3: COMPLETED (без правого бордера)
            with ui.column().classes('flex-1 p-4 min-h-[70vh]'):
                ui.label(f'ЗАВЕРШЕНІ ({len(completed_tasks)})').classes(
                    'font-bold text-green-600 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in completed_tasks:
                    render_task_card(t, controller, ctx, refresh_board, users_map)

    # Перше малювання дошки
    refresh_board()


def render_task_card(task, controller: TaskController, ctx: RequestContext, refresh_callback, users_map: dict):
    """Малює компактну картку задачі"""
    color_classes = get_card_colors(task, ctx.user_id)

    # Компактна картка: менші відступи (p-2), щільніший геп (gap-1)
    with ui.card().classes(f'w-full mb-2 p-2 border-l-4 {color_classes} shadow-sm hover:shadow transition-all'):

        # РЯДОК 1: Іконка типу, Заголовок, Кнопки
        with ui.row().classes('w-full items-center no-wrap gap-2'):
            ui.icon(get_type_icon(task.task_type), size='sm').classes('text-gray-500').tooltip(
                task.task_type or 'Тип не вказано')

            # Subject займає весь вільний простір, обрізається, якщо задовгий
            ui.label(task.task_subject) \
                .classes(
                'font-semibold text-sm flex-grow truncate cursor-pointer hover:text-blue-600 transition-colors') \
                .tooltip(task.task_subject) \
                .on('click', lambda e: ui.navigate.to(f'/tasks/edit/{task.id}'))

            # Кнопка редагування
            ui.button(icon='edit', on_click=lambda: ui.navigate.to(f'/tasks/edit/{task.id}')).props(
                'flat dense size=sm color="grey-7"').classes('px-1 min-w-[24px]')

            # Показуємо тільки якщо задача належить поточному юзеру І статус NEW або COMPLETED
            if task.assignee == ctx.user_id and task.task_status in [TASK_STATUS_NEW, TASK_STATUS_COMPLETED]:
                ui.button(
                    icon='delete',
                    on_click=lambda: delete_task_with_confirm(task.id, controller, ctx, refresh_callback)
                ).props('flat dense size=sm color="red-4"').classes('px-1 min-w-[24px]').tooltip('Видалити задачу')

            # Кнопка "Наступний статус"
            if task.task_status == TASK_STATUS_NEW:
                ui.button(icon='arrow_forward',
                          on_click=lambda: change_and_refresh(task.id, TASK_STATUS_IN_PROGRESS, controller, ctx,
                                                              refresh_callback)).props(
                    'flat dense size=sm color="primary"').classes('px-1 min-w-[24px]').tooltip('В роботу')
            elif task.task_status == TASK_STATUS_IN_PROGRESS:
                # Кнопка 1: Повернути в "Нові" (Відкласти)
                ui.button(icon='arrow_back',
                          on_click=lambda:
                          change_and_refresh(task.id, TASK_STATUS_NEW, controller, ctx, refresh_callback)
                          ).props('flat dense size=sm color="orange"').classes('px-1 min-w-[24px]').tooltip(
                    'Відкласти в ящик')

                # Кнопка 2: Завершити
                ui.button(icon='done',
                          on_click=lambda:
                          change_and_refresh(task.id, TASK_STATUS_COMPLETED, controller, ctx, refresh_callback)
                          ).props('flat dense size=sm color="green"').classes('px-1 min-w-[24px]').tooltip(
                    'Завершити')

            elif task.task_status == TASK_STATUS_COMPLETED:
                ui.button(icon='settings_backup_restore',
                          on_click=lambda:
                          change_and_refresh(task.id, TASK_STATUS_IN_PROGRESS, controller, ctx, refresh_callback)
                          ).props('flat dense size=sm color="orange"').classes('px-1 min-w-[24px]').tooltip(
                    'Повернути в роботу')

        deadline_str = task.task_deadline.strftime("%d.%m.%Y %H:%M") if task.task_deadline else "Без дедлайну"
        assignee_name = users_map.get(task.assignee, 'Не призначено')

        # --- ЛОГІКА КОЛЬОРІВ ДЕДЛАЙНУ ---
        deadline_classes = 'text-gray-500'  # Дефолтний стиль (просто сірий текст, без фону)

        if task.task_deadline and task.task_status != TASK_STATUS_COMPLETED:
            now = datetime.now()
            # 1. Прострочено (менше за поточний час)
            if task.task_deadline < now:
                deadline_classes = 'bg-red-500 text-white px-1.5 py-0.5 rounded-md font-medium'
            # 2. Сьогодні або Завтра (але ще не прострочено, бо пройшло першу перевірку)
            elif task.task_deadline.date() <= (now + timedelta(days=1)).date():
                deadline_classes = 'bg-orange-200 text-black px-1.5 py-0.5 rounded-md font-medium'

        # --- ВІДМАЛЬОВКА ---
        with ui.row().classes('w-full justify-between items-center text-xs mt-1'):

            # Застосовуємо вираховані класи до блоку з іконкою та датою
            with ui.row().classes(f'items-center gap-1 {deadline_classes}'):
                ui.icon('schedule', size='xs')
                ui.label(deadline_str)

            with ui.row().classes('items-center gap-1 text-gray-500'):
                ui.icon('person', size='xs')
                ui.label(assignee_name).classes('truncate max-w-[120px]').tooltip(assignee_name)


def change_and_refresh(task_id: int, new_status: str, controller: TaskController, ctx: RequestContext,
                       refresh_callback):
    """Оновлює статус у базі і миттєво перемальовує дошку"""
    controller.update_task_status(ctx, task_id, new_status)
    ui.notify('Статус оновлено!', type='positive', position='top-right')
    refresh_callback()