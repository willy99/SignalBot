from nicegui import ui
from security_config import *

def render_users_page(auth_manager):
    ui.label('Керування користувачами').classes('w-full text-center text-3xl font-bold mb-8')

    # --- ДІАЛОГ ДОДАВАННЯ КОРИСТУВАЧА ---
    with ui.dialog() as add_dialog, ui.card().classes('w-96'):
        ui.label('Новий користувач').classes('text-xl font-bold mb-4')

        new_username = ui.input('Логін').classes('w-full')
        new_fullname = ui.input('ПІБ').classes('w-full')
        new_password = ui.input('Пароль').classes('w-full').props('type=password')
        new_role = ui.select(AVAILABLE_ROLES, label='Роль', value='Гість').classes('w-full mb-4')

        def save_new_user():
            if not new_username.value or not new_password.value:
                ui.notify('Логін та пароль обов\'язкові!', type='warning')
                return

            success, msg = auth_manager.create_user(
                new_username.value.strip(),
                new_password.value,
                new_role.value,
                new_fullname.value.strip() if new_fullname.value else ''
            )

            if success:
                ui.notify(msg, type='positive')
                add_dialog.close()
                refresh_table()
            else:
                ui.notify(msg, type='negative')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=add_dialog.close).props('flat')
            ui.button('Створити', on_click=save_new_user).classes('bg-blue-600 text-white')

    # --- ДІАЛОГ ЗМІНИ ПАРОЛЯ ---
    state = {'editing_user_id': None}

    with ui.dialog() as pass_dialog, ui.card().classes('w-96'):
        ui.label('Зміна пароля').classes('text-xl font-bold mb-4')
        edit_password = ui.input('Новий пароль').classes('w-full mb-4').props('type=password autofocus')

        def save_new_password():
            if not edit_password.value:
                ui.notify('Введіть новий пароль', type='warning')
                return
            auth_manager.update_password(state['editing_user_id'], edit_password.value)
            ui.notify('Пароль успішно змінено!', type='positive')
            pass_dialog.close()

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=pass_dialog.close).props('flat')
            ui.button('Зберегти', on_click=save_new_password).classes('bg-orange-500 text-white')

    # --- ГОЛОВНИЙ ІНТЕРФЕЙС СТОРІНКИ ---
    with ui.column().classes('w-full max-w-5xl mx-auto items-center'):

        with ui.row().classes('w-full justify-end mb-4'):
            ui.button('Додати користувача', on_click=lambda: (
                new_username.set_value(''), new_fullname.set_value(''), new_password.set_value(''), add_dialog.open()
            ), icon='person_add').classes('bg-green-600 text-white')

        table_container = ui.column().classes('w-full')

        def open_password_dialog(user_id):
            state['editing_user_id'] = user_id
            edit_password.value = ''
            pass_dialog.open()

        def toggle_user_status(user):
            # Забороняємо адміну вимикати самого себе, щоб не зламати систему
            if user['username'] == 'admin':
                ui.notify('Головного адміна не можна деактивувати!', type='warning')
                refresh_table()
                return

            auth_manager.update_user(user['id'], user['role'], user['full_name'], not user['is_active'])
            ui.notify(f"Статус {user['username']} змінено!", type='info')
            refresh_table()

        def update_user_role(user, new_role):
            if user['username'] == 'admin' and new_role != 'admin':
                ui.notify('Головний адмін завжди має бути admin!', type='warning')
                refresh_table()
                return

            auth_manager.update_user(user['id'], new_role, user['full_name'], user['is_active'])
            ui.notify(f"Роль {user['username']} змінено на {new_role}", type='positive')
            refresh_table()

        def refresh_table():
            table_container.clear()
            users = auth_manager.get_all_users()

            with table_container:
                columns = [
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                    {'name': 'username', 'label': 'Логін', 'field': 'username', 'align': 'left'},
                    {'name': 'full_name', 'label': 'ПІБ', 'field': 'full_name', 'align': 'left'},
                    {'name': 'role', 'label': 'Роль', 'field': 'role', 'align': 'center'},
                    {'name': 'status', 'label': 'Доступ', 'field': 'is_active', 'align': 'center'},
                    {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
                ]

                table = ui.table(columns=columns, rows=users, row_key='id').classes('w-full general-table')

                # Кастомний слот для колонки "Роль" (випадаючий список прямо в таблиці)
                table.add_slot('body-cell-role', f'''
                    <q-td :props="props">
                        <q-select 
                            v-model="props.row.role" 
                            :options="{AVAILABLE_ROLES}" 
                            dense options-dense borderless
                            @update:model-value="$parent.$emit('role_changed', props.row)"
                        />
                    </q-td>
                ''')

                # Кастомний слот для статусу (перемикач Активний/Вимкнений)
                table.add_slot('body-cell-status', '''
                    <q-td :props="props">
                        <q-toggle v-model="props.row.is_active" color="green" @update:model-value="$parent.$emit('toggle_status', props.row)" />
                    </q-td>
                ''')

                # Кастомний слот для дій (Кнопка зміни пароля)
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn size="sm" color="orange" icon="key" flat @click="$parent.$emit('change_pwd', props.row.id)">
                            Пароль
                        </q-btn>
                    </q-td>
                ''')

                # Обробники подій з таблиці
                table.on('role_changed', lambda e: update_user_role(e.args, e.args['role']))
                table.on('toggle_status', lambda e: toggle_user_status(e.args))
                table.on('change_pwd', lambda e: open_password_dialog(e.args))

        # Малюємо таблицю при першому завантаженні
        refresh_table()