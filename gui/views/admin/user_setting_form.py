from nicegui import ui, app

from dics.deserter_xls_dic import VALID_PATTERN_PHONE, VALID_PATTERN_EMAIL
from domain.user import User
from gui.services.auth_manager import AuthManager
from gui.controllers.user_controller import UserController
import regex as re


def render_profile_settings(user_ctrl: UserController, auth_manager: AuthManager):
    ctx = auth_manager.get_current_context()

    user_data:User = user_ctrl.get_user_profile(ctx)

    state = {
        'full_name': user_data.full_name,
        'use_2fa': bool(user_data.use_2fa),
        'has_verified_contact': bool(user_data.email or user_data.phone),
        'loading': False
    }

    async def save_profile():
        state['loading'] = True
        try:
            success = await auth_manager.execute(
                user_ctrl.update_profile,
                ctx,
                full_name=state['full_name'],
                use_2fa=state['use_2fa']
            )
            if success:
                ui.notify('Профіль оновлено!', type='positive')
                # Оновлюємо дані в сесії, щоб у меню відразу змінилося ім'я
                app.storage.user['user_info']['full_name'] = state['full_name']
        except Exception as e:
            ui.notify(f'Помилка: {e}', type='negative')
        finally:
            state['loading'] = False

    with ui.column().classes('w-full items-center p-8'):
        with ui.card().classes('w-full max-w-lg p-6 shadow-lg rounded-xl'):
            ui.label('Налаштування профілю').classes('text-2xl font-bold mb-6')

            # --- Поле ПІБ ---
            ui.input('Ваше повне ім\'я (ПІБ)').bind_value(state, 'full_name') \
                .classes('w-full mb-4').props('outlined icon="person"')

            # --- Секція 2FA ---
            with ui.row().classes('w-full items-center p-4 bg-slate-50 rounded-lg mb-6 border'):
                with ui.column().classes('flex-grow'):
                    ui.label('Двофакторна автентифікація (2FA)').classes('font-bold')
                    if not state['has_verified_contact']:
                        ui.label('Спочатку підтвердіть Signal або Email у розділі безпеки') \
                            .classes('text-xs text-red-500')
                    else:
                        ui.label('Використовувати код при кожному вході') \
                            .classes('text-xs text-slate-500')

                # Сам перемикач
                tgl = ui.switch().bind_value(state, 'use_2fa')
                tgl.bind_enabled_from(state, 'has_verified_contact')

            # --- Інфо про пароль ---
            with ui.row().classes('w-full p-3 bg-amber-50 rounded border border-amber-200 mb-6'):
                ui.icon('info', color='amber-700')
                ui.label('Зміна пароля здійснюється тільки адміністратором системи.').classes('text-xs text-amber-900')

            # --- Кнопка збереження ---
            ui.button('ЗБЕРЕГТИ ЗМІНИ', on_click=save_profile) \
                .props(f'color="primary" :loading="{state["loading"]}"') \
                .classes('w-full h-12 text-lg')

def render_user_settings_2fa(user_ctrl: UserController, auth_manager: AuthManager):
    # Отримуємо поточні дані користувача з контексту
    ctx = auth_manager.get_current_context()
    user_data: User = user_ctrl.get_user_profile(ctx)

    # Локальний стан форми для реактивності
    state = {
        'current_phone': user_data.phone,
        'current_email': user_data.email,
        'contact_value': '',
        'contact_type': 'Signal',
        'verification_code': '',
        'is_waiting_code': False,
        'timer': 0,
        'loading': False,
        'is_success': False,
        'show_edit_form': not (user_data.phone or user_data.email)  # Ховаємо форму, якщо дані вже є
    }
    state.update({
        'is_success': False
    })

    def start_timer():
        state['timer'] = 60

        def tick():
            if state['timer'] > 0:
                state['timer'] -= 1
                ui.timer(1.0, tick, once=True)

        tick()

    async def handle_send_code():
        if not state['contact_value'].strip():
            ui.notify('Введіть дані для зв\'язку', type='warning')
            return

        state['loading'] = True
        try:
            # Викликаємо контролер через наш безпечний execute
            success = await auth_manager.execute(
                user_ctrl.request_verification,
                ctx,
                contact_info=state['contact_value'].strip(),
                contact_type=state['contact_type']
            )

            if success:
                state['is_waiting_code'] = True
                start_timer()
                ui.notify(f'Код відправлено на {state["contact_type"]}', type='positive')
        except Exception as e:
            ui.notify(f'Помилка: {e}', type='negative')
        finally:
            state['loading'] = False

    async def handle_verify_success():
        # Додаткова логіка після успішного підтвердження
        state['is_success'] = True
        state['is_waiting_code'] = False
        # Оновлюємо локальний "поточний" стан, щоб UI перерисувався
        if state['contact_type'] == 'Signal':
            state['current_phone'] = state['contact_value']
        else:
            state['current_email'] = state['contact_value']

    async def handle_verify():
        if not state['verification_code'].strip():
            ui.notify('Введіть код підтвердження', type='warning')
            return

        state['loading'] = True
        try:
            success = await auth_manager.execute(
                user_ctrl.confirm_verification,
                ctx,
                entered_code=state['verification_code'].strip()
            )

            if success:
                # ПЕРЕМИКАЄМО НА ЕКРАН УСПІХУ
                state['is_success'] = True
                state['is_waiting_code'] = False
        except Exception as e:
            ui.notify(f'Невірний код: {e}', type='negative')
        finally:
            state['loading'] = False

    def validate_contact(value: str) -> bool:
        if not value:
            return False
        if state['contact_type'] == 'Signal':
            return bool(re.match(VALID_PATTERN_PHONE, value))
        else:
            return bool(re.match(VALID_PATTERN_EMAIL, value))

    def handle_contact_blur():
        val = state['contact_value'].strip()
        if state['contact_type'] == 'Signal' and val.isdigit() and len(val) == 10:
            # Якщо ввів 0961234567 -> перетворюємо на +380961234567
            state['contact_value'] = '+38' + val

    contact_input = None

    def update_label(new_type):
        if contact_input:
            contact_input.error = None  # Скидаємо помилку при зміні типу
            contact_input.props(f'label="Ваш {new_type}"')
            contact_input.props(f'placeholder="{" +380961234567" if new_type == "Signal" else "example@mail.com"}"')
            contact_input.update()  # Примусово оновлюємо елемент

    # --- ДИЗАЙН СТОРІНКИ ---
    with ui.column().classes('w-full items-center p-8'):
        with ui.card().classes('w-full max-w-lg p-6 shadow-lg rounded-xl'):
            with ui.column().classes('w-full').bind_visibility_from(state, 'is_success', backward=lambda x: not x):
                ui.label('Безпека та 2FA').classes('text-2xl font-bold mb-4 text-slate-800')

                # ==========================================
                # НОВИЙ БЛОК: ПОТОЧНИЙ СТАН (показуємо, якщо дані є)
                # ==========================================
                with ui.column().classes('w-full p-4 mb-4 bg-green-50 rounded-lg border border-green-200') \
                        .bind_visibility_from(state, 'show_edit_form', backward=lambda x: not x):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('verified', color='positive', size='sm')
                        ui.label('Ваш підтверджений контакт:').classes('text-sm text-green-800 font-bold')

                    # Виводимо телефон
                    with ui.row().classes('items-center gap-2 ml-7').bind_visibility_from(state, 'current_phone'):
                        ui.icon('phone_android', size='16px', color='grey-6')
                        ui.label().bind_text_from(state, 'current_phone')

                    # Виводимо пошту
                    with ui.row().classes('items-center gap-2 ml-7').bind_visibility_from(state, 'current_email'):
                        ui.icon('alternate_email', size='16px', color='grey-6')
                        ui.label().bind_text_from(state, 'current_email')

                    ui.button('Змінити дані', on_click=lambda: state.update({'show_edit_form': True})) \
                        .props('flat dense color="primary" icon="edit"').classes('mt-2 text-xs')

                with ui.column().classes('w-full').bind_visibility_from(state, 'show_edit_form'):
                    ui.markdown('Оберіть спосіб отримання кодів для **двохфакторної авторизації**.').classes('mb-4 text-slate-600')

                    # Вибір типу зв'язку
                    with ui.row().classes('w-full gap-4 mb-4'):
                        ui.select(
                            options=['Signal', 'Email'],
                            label='Канал зв\'язку',
                            on_change=lambda e: update_label(e.value)
                        ).bind_value(state, 'contact_type').classes('flex-grow').props('outlined dense')


                    # Введення контакту
                    with ui.row().classes('w-full items-center gap-2 mb-4'):
                        contact_input = ui.input(
                            label='Ваш Signal',
                            validation={'Невірний формат': lambda v: validate_contact(v)}
                        ).bind_value(state, 'contact_value').classes('flex-grow').props('outlined dense')

                        contact_input.on('blur', handle_contact_blur)
                        contact_input.bind_enabled_from(state, 'is_waiting_code', backward=lambda x: not x)

                        send_btn = ui.button(on_click=handle_send_code).props('flat round icon="send" color="primary"')
                        send_btn.bind_visibility_from(state, 'is_waiting_code', backward=lambda x: not x)
                        send_btn.bind_enabled_from(state, 'loading', backward=lambda x: not x)

                # Блок підтвердження (з'являється після відправки)
                with ui.column().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-200').bind_visibility_from(state, 'is_waiting_code'):
                    ui.label('Підтвердження').classes('font-bold text-blue-800 mb-2')

                    with ui.row().classes('w-full items-center gap-4'):
                        code_input = ui.input('Код із повідомлення').bind_value(state, 'verification_code').classes('w-40').props('outlined dense mask="######" shadow-2')

                        verify_btn = ui.button('ПІДТВЕРДИТИ', on_click=handle_verify).props('color="positive" text-color="white"').classes('flex-grow h-10')
                        verify_btn.bind_enabled_from(state, 'loading', backward=lambda x: not x)

                    with ui.row().classes('w-full justify-between items-center mt-2'):
                        ui.label().bind_text_from(state, 'timer', backward=lambda x: f"Повторна відправка через {x}с" if x > 0 else "")

                        ui.button('Скасувати', on_click=lambda: state.update({'is_waiting_code': False})).props('flat color="grey" dense').classes('text-xs')

                # Інформаційна плашка
                with ui.row().classes('mt-6 p-3 bg-amber-50 rounded border border-amber-200 w-full'):
                    ui.icon('security', color='amber-800').classes('mr-2')
                    ui.label('Після підтвердження ви зможете увімкнути вхід за кодом у налаштуваннях профілю.').classes('text-xs text-amber-900')

            # --- ЕКРАН 2: ПІДТВЕРДЖЕНО (показуємо тільки при успіху) ---
            with ui.column().classes('w-full items-center py-6 text-center').bind_visibility_from(state, 'is_success'):
                ui.icon('check_circle', color='positive', size='64px').classes('mb-4')
                ui.label('Контакт підтверджено!').classes('text-2xl font-bold text-slate-800')
                ui.label('Тепер ви можете використовувати цей канал для входу в систему.').classes('text-slate-600 mb-8')

                with ui.row().classes('w-full justify-center'):
                    ui.button('НА ГОЛОВНУ', on_click=lambda: ui.navigate.to('/home')) \
                        .props('elevated color="primary" icon="home"') \
                        .classes('px-8 py-2')