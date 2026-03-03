from nicegui import ui, app
from gui.services.request_context import RequestContext
from domain.task import *
from gui.controllers.task_controller import TaskController
from datetime import timedelta
from service.constants import TASK_STATUS_COMPLETED, TASK_STATUS_NEW, TASK_STATUS_IN_PROGRESS
from dics.deserter_xls_dic import TASK_TYPES

# Словник іконок для різних типів задач
def get_type_icon(task_type: str) -> str:
    icons = TASK_TYPES
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
    # Отримуємо список юзерів і робимо зручний словник {id: "Ім'я"}
    users_list = controller.get_available_users()
    users_map = {}

    assignee_options = {
        'unassigned': 'Непризначені',
        'all': 'Всі задачі',
        ctx.user_id: 'Мої задачі',
    }

    for u in users_list:
        name = u.get('full_name') or u.get('username') or f"User {u['id']}"
        users_map[u['id']] = name
        if u['id'] != ctx.user_id:
            assignee_options[u['id']] = name

    # Типи задач
    type_options = {'all': 'Всі типи'}
    for t in TASK_TYPES.keys():
        type_options[t] = t

    # Тематичний період
    period_options = {
        'all': 'Будь-який термін',
        'overdue': '🔥 Прострочені',
        'today': '⚡ На сьогодні / Актуальні',
        'future': '📅 Майбутні / Безстрокові'
    }

    # Роки (від поточного -2 до +1)
    current_year = datetime.now().year
    year_options = {str(y): str(y) for y in range(current_year - 2, current_year + 2)}

    default_state = {
        'search_query': '',
        'assignee_id': ctx.user_id,
        'task_type_filter': 'all',
        'period_filter': 'all',
        'created_year': None,
        'created_from': None,
        'created_to': None,
    }

    state = app.storage.user.get('task_board_filters', default_state)

    # Захист: якщо збереженого юзера раптом видалили з бази
    if state.get('assignee_id') not in assignee_options:
        state['assignee_id'] = ctx.user_id

    # === СТВОРЮЄМО ОНОВЛЮВАНУ ДОШКУ (Але поки не малюємо) ===
    @ui.refreshable
    def task_board():
        # Тепер ми передаємо весь словник state прямо в контролер
        tasks = controller.get_all_tasks(ctx, search_filter=state)
        # ДОДАТКОВИЙ PYTHON-ФІЛЬТР ДЛЯ КИРИЛИЦІ
        if state.get('search_query', ''):
            search_query = state.get('search_query', '').strip().lower()
            if search_query:
                tasks = [
                    t for t in tasks
                    if (t.task_subject and search_query in t.task_subject.lower()) or
                       (t.task_details and search_query in t.task_details.lower())
                ]

        # Розподіляємо по списках
        new_tasks = [t for t in tasks if t.task_status == TASK_STATUS_NEW]
        in_progress_tasks = [t for t in tasks if t.task_status == TASK_STATUS_IN_PROGRESS]
        completed_tasks = [t for t in tasks if t.task_status == TASK_STATUS_COMPLETED]

        with ui.row().classes(
                'w-full items-start justify-between gap-0 flex-nowrap bg-white border-y border-gray-200 shadow-sm'):
            # СТОВПЧИК 1: NEW
            with ui.column().classes('flex-1 p-4 min-h-[70vh] border-r border-gray-200'):
                ui.label(f'НОВІ ({len(new_tasks)})').classes(
                    'font-bold text-gray-500 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in new_tasks:
                    render_task_card(t, controller, ctx, task_board.refresh, users_map)

            # СТОВПЧИК 2: IN PROGRESS
            with ui.column().classes('flex-1 p-4 min-h-[70vh] border-r border-gray-200'):
                ui.label(f'В РОБОТІ ({len(in_progress_tasks)})').classes(
                    'font-bold text-blue-500 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in in_progress_tasks:
                    render_task_card(t, controller, ctx, task_board.refresh, users_map)

            # СТОВПЧИК 3: COMPLETED
            with ui.column().classes('flex-1 p-4 min-h-[70vh]'):
                ui.label(f'ЗАВЕРШЕНІ ({len(completed_tasks)})').classes(
                    'font-bold text-green-600 text-sm mb-4 text-center w-full uppercase tracking-wider')
                for t in completed_tasks:
                    render_task_card(t, controller, ctx, task_board.refresh, users_map)

    # === ОБРОБНИКИ ПОДІЙ ===
    def on_filter_change(e=None):
        app.storage.user['task_board_filters'] = state
        task_board.refresh()  # Перемальовуємо дошку одним викликом

    def reset_filters():
        # Скидаємо все на дефолт
        state.update({k: v for k, v in default_state.items()})
        on_filter_change()

    # === МАЛЮЄМО UI ===
    with ui.row().classes('w-full justify-between items-center mb-4 px-4'):
        # 1. Заголовок (зліва)
        ui.label('Дошка задач').classes('text-3xl font-bold')

        # 2. Блок з фільтром та кнопкою (справа)
        with ui.row().classes('items-center gap-4 flex-grow justify-end'):
            ui.input('Пошук (тема, опис)', on_change=on_filter_change) \
                .bind_value(state, 'search_query') \
                .props('clearable outlined dense debounce=500') \
                .classes('w-64')
            # Важливо: використовуємо bind_value(state, 'assignee_id') замість value=
            filter_select = ui.select(
                assignee_options,
                label='Фільтр за виконавцем',
                on_change=on_filter_change
            ).bind_value(state, 'assignee_id').classes('w-64')

            filter_select.add_slot('option', f'''
                    <q-item v-bind="props.itemProps" 
                            :class="props.opt.value == {ctx.user_id} ? 'bg-orange-50 text-orange-900 font-bold border-l-4 border-orange-200' : ''">
                        <q-item-section>
                            <q-item-label v-html="props.opt.label"></q-item-label>
                        </q-item-section>
                    </q-item>
                ''')

            ui.button('Створити нову', icon='add', on_click=lambda: ui.navigate.to('/tasks/edit/new')).props(
                'color="primary"')

    # --- РОЗШИРЕНІ ФІЛЬТРИ (Сховані в гармошку) ---
    with ui.expansion('Розширені фільтри (Дати, Типи, Періоди)', icon='filter_alt') \
            .classes('w-full mt-2 bg-gray-50 rounded-md border border-gray-200'):
        with ui.row().classes('w-full items-center gap-4 p-4'):
            ui.select(type_options, label='Тип задачі', on_change=on_filter_change) \
                .bind_value(state, 'task_type_filter').props('outlined dense').classes('w-48')

            ui.select(period_options, label='Тематичний період', on_change=on_filter_change) \
                .bind_value(state, 'period_filter').props('outlined dense').classes('w-64')

            ui.separator().props('vertical').classes('mx-2')

            ui.select(year_options, label='Рік створ.', clearable=True, on_change=on_filter_change) \
                .bind_value(state, 'created_year').props('outlined dense').classes('w-32')

            ui.input('Створено з', on_change=on_filter_change) \
                .bind_value(state, 'created_from').props('type=date clearable outlined dense').classes('w-40')

            ui.input('Створено до', on_change=on_filter_change) \
                .bind_value(state, 'created_to').props('type=date clearable outlined dense').classes('w-40')

            # Кнопка скидання фільтрів (притиснута до правого краю)
            ui.button('Скинути', icon='restart_alt', on_click=reset_filters) \
                .props('flat color="red"').classes('ml-auto')

    # === РЕНДЕРИМО ДОШКУ ===
    task_board()  # Викликаємо функцію, щоб вона намалювала дошку на екрані


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