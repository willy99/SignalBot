from nicegui import ui
from dics.security_config import *

def render_permissions_page(auth_manager):
    ui.label('Керування правами доступу').classes('w-full text-center text-3xl font-bold mb-8')

    # Стан для збереження вибраної ролі та її прав
    state = {
        'selected_role': None,
        'permissions': {}
    }

    # Ініціалізуємо порожній словник прав для всіх модулів
    for mod in AVAILABLE_MODULES.keys():
        state['permissions'][mod] = {PERM_READ: False, PERM_EDIT: False, PERM_DELETE: False}

    with ui.row().classes('w-full justify-center px-4'):
        with ui.card().classes('w-full max-w-6xl p-6 shadow-md'):

            # Вибір ролі
            with ui.row().classes('w-full items-center gap-4 mb-6'):
                ui.label('1. Оберіть роль для налаштування:').classes('text-lg font-medium text-gray-700')
                role_select = ui.select(AVAILABLE_ROLES, label='Роль', on_change=lambda e: load_role_permissions(e)).classes('w-64')

            # Контейнер для таблиці галочок (спочатку прихований/порожній)
            perms_container = ui.column().classes('w-full gap-2')

            def load_role_permissions(role):
                """Завантажує права з бази, коли адмін обирає роль зі списку"""
                # Приймаємо одразу рядок (роль), замість події 'e'
                role = role.value
                state['selected_role'] = role
                if not role:
                    perms_container.clear()
                    return

                # Отримуємо права з AuthManager

                current_perms = auth_manager.get_user_permissions(role)

                for mod in AVAILABLE_MODULES.keys():
                    mod_perms = current_perms.get(mod, {PERM_READ: False, PERM_EDIT: False, PERM_DELETE: False})
                    state['permissions'][mod][PERM_READ] = mod_perms.get(PERM_READ, False)
                    state['permissions'][mod][PERM_EDIT] = mod_perms.get(PERM_EDIT, False)
                    state['permissions'][mod][PERM_DELETE] = mod_perms.get(PERM_DELETE, False)

                render_checkboxes()

            def save_permissions():
                """Зберігає всі проставлені галочки в базу даних"""
                role = state['selected_role']
                if not role:
                    ui.notify('Оберіть роль!', type='warning')
                    return

                try:
                    for mod, perms in state['permissions'].items():
                        auth_manager.set_permissions(
                            role=role,
                            module_name=mod,
                            can_read=int(perms[PERM_READ]),
                            can_write=int(perms[PERM_EDIT]),
                            can_delete=int(perms[PERM_DELETE])
                        )
                    ui.notify(f'Права для ролі "{role}" успішно збережено!', type='positive', position='top')
                except Exception as e:
                    ui.notify(f'Помилка збереження: {e}', type='negative')

            def render_checkboxes():
                perms_container.clear()
                with perms_container:
                    ui.label('2. Налаштуйте доступ до модулів:').classes('text-lg font-medium text-gray-700 mb-2 mt-4')

                    # Шапка таблиці
                    with ui.row().classes(
                            'w-full font-bold border-b-2 border-gray-200 pb-2 items-center bg-gray-50 px-2 rounded-t flex-nowrap'):
                        ui.label('Модуль').classes('w-2/5 whitespace-nowrap')
                        ui.label('Читання (Read)').classes('w-1/5 text-center text-blue-600 whitespace-nowrap')
                        ui.label('Запис/Редагування').classes('w-1/5 text-center text-green-600 whitespace-nowrap')
                        ui.label('Видалення').classes('w-1/5 text-center text-red-600 whitespace-nowrap')

                    # Рядки для кожного модуля
                    for mod_id, mod_name in AVAILABLE_MODULES.items():
                        with ui.row().classes(
                                'w-full items-center border-b border-gray-100 py-3 px-2 hover:bg-blue-50 transition-colors flex-nowrap'):
                            ui.label(mod_name).classes('w-2/5 text-gray-800 font-medium')

                            # ЗБЕРІГАЄМО ПОСИЛАННЯ НА КОЖЕН ЧЕКБОКС
                            with ui.row().classes('w-1/5 justify-center'):
                                cb_read = ui.checkbox('').bind_value(state['permissions'][mod_id], PERM_READ).props('color="blue"')

                            with ui.row().classes('w-1/5 justify-center'):
                                cb_write = ui.checkbox('').bind_value(state['permissions'][mod_id], PERM_EDIT).props('color="green"')

                            with ui.row().classes('w-1/5 justify-center'):
                                cb_delete = ui.checkbox('').bind_value(state['permissions'][mod_id], PERM_DELETE).props('color="red"')

                            # === ЛОГІКА "ЗАХИСТУ ВІД ДУРАКА" ===
                            def enforce_logic(val, action, r=cb_read, w=cb_write, d=cb_delete):
                                # val - це булеве значення (True/False), яке прийшло з галочки
                                if action == PERM_READ and not val:
                                    w.set_value(False)
                                    d.set_value(False)
                                elif action in [PERM_EDIT, PERM_DELETE] and val:
                                    r.set_value(True)

                            # e.args містить нове значення (True або False)
                            cb_read.on('update:model-value', lambda e, r=cb_read, w=cb_write, d=cb_delete: enforce_logic(e.args, PERM_READ, r, w, d))
                            cb_write.on('update:model-value', lambda e, r=cb_read, w=cb_write, d=cb_delete: enforce_logic(e.args, PERM_EDIT, r, w, d))
                            cb_delete.on('update:model-value', lambda e, r=cb_read, w=cb_write, d=cb_delete: enforce_logic(e.args, PERM_DELETE, r, w, d))

                    # Кнопка збереження
                    with ui.row().classes('w-full justify-end mt-6'):
                        ui.button('💾 ЗБЕРЕГТИ ПРАВА', on_click=save_permissions).classes(
                            'bg-green-600 text-white px-8 py-2 shadow-lg')