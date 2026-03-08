from nicegui import ui, run, events
from gui.services.request_context import RequestContext
import asyncio


def render_inbox_page(inbox_ctrl, task_ctrl, auth_manager, ctx: RequestContext):
    ui.label('📥 Вхідні файли (Inbox)').classes('text-3xl font-bold mb-6 text-center w-full')

    can_assign = auth_manager.has_access('task', 'delete')

    users_list = task_ctrl.get_available_users()
    user_options = {u['username']: u.get('full_name') or u['username'] for u in users_list if 'username' in u}

    # ==========================================
    # ОБРОБНИК ЗАВАНТАЖЕННЯ (Upload)
    # ==========================================
    async def handle_upload(e: events.UploadEventArguments):
        try:
            filename = e.file.name
            file_data = await e.file.read()
            await run.io_bound(inbox_ctrl.upload_root_file, ctx, filename, file_data)
            ui.notify(f'Файл "{filename}" успішно завантажено!', type='positive', icon='cloud_done')
            e.sender.reset()
            await load_data()
        except Exception as ex:
            ui.notify(f'Помилка завантаження: {ex}', type='negative')

    # СТАТИЧНИЙ БЛОК UPLOAD
    with ui.card().classes('w-full max-w-5xl mx-auto p-0 shadow-sm border border-blue-200 mb-6'):
        with ui.row().classes('w-full bg-blue-50 p-4 border-b border-blue-200 items-center gap-2'):
            ui.icon('cloud_upload', size='md', color='blue-600')
            ui.label('Завантажити нові файли у спільну папку').classes('font-bold text-blue-800 text-lg')
        with ui.row().classes('w-full p-4'):
            ui.upload(multiple=True, auto_upload=True, on_upload=handle_upload,
                      label='Перетягніть файли сюди або натисніть "+" (Browse)').classes('w-full').props(
                'color="blue" accept="*"')

    # ДИНАМІЧНИЙ КОНТЕЙНЕР ДЛЯ ФАЙЛІВ
    files_container = ui.column().classes('w-full max-w-5xl mx-auto gap-6')

    async def load_data():
        files_container.clear()
        with files_container:
            ui.spinner('dots', size='lg', color='primary').classes('mx-auto mt-4')

        try:
            data = await run.io_bound(inbox_ctrl.get_user_inbox_messages, ctx)
            personal_files = data.get('personal_files', [])
            root_files = data.get('root_files', [])

            # --- Стейт для масових дій ---
            selection_p = set()  # Виділені персональні файли
            selection_r = set()  # Виділені спільні файли
            checkboxes_p = {}  # UI-елементи чекбоксів (персональні)
            checkboxes_r = {}  # UI-елементи чекбоксів (спільні)

            files_container.clear()
            with files_container:
                # ==========================================
                # 1. ПЕРСОНАЛЬНІ ФАЙЛИ (Мої)
                # ==========================================
                with ui.card().classes('w-full p-0 shadow-sm border border-red-100'):
                    with ui.row().classes(
                            'w-full bg-red-50 p-4 border-b border-red-100 items-center justify-between min-h-[72px]'):

                        # Ліва частина хедера: Головний чекбокс + Заголовок
                        with ui.row().classes('items-center gap-2'):
                            def toggle_all_p(e):
                                for cb in checkboxes_p.values(): cb.value = e.value

                            ui.checkbox(on_change=toggle_all_p).props('color="red"')
                            ui.label(f'🔴 Вам призначено ({len(personal_files)})').classes(
                                'font-bold text-red-800 text-lg')

                        # Права частина хедера: БЛОК МАСОВИХ ДІЙ (прихований)
                        bulk_actions_p = ui.row().classes('items-center gap-2 transition-all')
                        bulk_actions_p.set_visibility(False)
                        with bulk_actions_p:
                            ui.label('Вибрано:').classes('text-sm text-gray-600')
                            ui.button(icon='download', on_click=lambda: download_selected(selection_p)).props(
                                'color="green" outline size="sm"').tooltip('Завантажити вибрані')
                            if can_assign:
                                bulk_assign_select_p = ui.select(user_options, label='Перепризначити вибрані').props(
                                    'dense outlined').classes('w-48')
                                ui.button(icon='switch_account',
                                          on_click=lambda: assign_selected(selection_p, bulk_assign_select_p.value,
                                                                           True)).props(
                                    'color="secondary" outline size="sm"').tooltip('Віддати вибрані')
                            ui.button(icon='delete', on_click=lambda: delete_selected_p(selection_p)).props(
                                'color="red" flat size="sm"').classes('px-2').tooltip('Видалити вибрані')

                        # Функція оновлення видимості блоку масових дій
                        def update_bulk_p_visibility(filename, is_checked):
                            if is_checked:
                                selection_p.add(filename)
                            else:
                                selection_p.discard(filename)
                            bulk_actions_p.set_visibility(len(selection_p) > 0)

                    if not personal_files:
                        ui.label('У вас немає нових файлів.').classes('text-gray-500 italic p-6 text-center w-full')
                    else:
                        for f in personal_files:
                            with ui.row().classes(
                                    'w-full p-4 border-b border-gray-100 items-center justify-between hover:bg-gray-50 flex-nowrap'):
                                with ui.row().classes('items-center gap-3 flex-grow overflow-hidden'):
                                    # Чекбокс конкретного файлу
                                    cb = ui.checkbox(
                                        on_change=lambda e, fname=f: update_bulk_p_visibility(fname, e.value)).props(
                                        'color="red"')
                                    checkboxes_p[f] = cb

                                    ui.icon('description', size='md', color='red-400')
                                    ui.label(f).classes('text-gray-800 font-medium truncate').tooltip(f)

                                # Індивідуальні дії (залишаємо для зручності)
                                with ui.row().classes('items-center gap-2 flex-nowrap'):
                                    ui.button(icon='download',
                                              on_click=lambda file_name=f: download_file(file_name)).props(
                                        'color="green" outline size="sm"').classes('whitespace-nowrap').tooltip(
                                        'Завантажити собі')
                                    ui.button(icon='add_task',
                                              on_click=lambda file_name=f: create_task_from_file(file_name)).props(
                                        'color="primary" outline size="sm"').classes('whitespace-nowrap').tooltip(
                                        'Додати задачу')
                                    if can_assign:
                                        assignee_select_p = ui.select(user_options, label='Перепризначити').props(
                                            'dense outlined').classes('w-48')
                                        ui.button(icon='switch_account',
                                                  on_click=lambda file_name=f, sel=assignee_select_p: assign_file(
                                                      file_name, sel.value, True)).props(
                                            'color="secondary" outline size="sm"').classes('whitespace-nowrap').tooltip(
                                            'Спихнути комусь')
                                    ui.button(icon='delete',
                                              on_click=lambda file_name=f: delete_file_with_confirm(file_name)).props(
                                        'color="red" flat size="sm"').classes('px-2').tooltip('Видалити файл')

                # ==========================================
                # 2. СПІЛЬНІ ФАЙЛИ (Непризначені)
                # ==========================================
                with ui.card().classes('w-full p-0 shadow-sm border border-gray-200 mt-4'):
                    with ui.row().classes(
                            'w-full bg-gray-100 p-4 border-b border-gray-200 items-center justify-between min-h-[72px]'):

                        with ui.row().classes('items-center gap-2'):
                            def toggle_all_r(e):
                                for cb in checkboxes_r.values(): cb.value = e.value

                            ui.checkbox(on_change=toggle_all_r)
                            ui.label(f'⚪ Спільні файли ({len(root_files)})').classes('font-bold text-gray-700 text-lg')

                        # БЛОК МАСОВИХ ДІЙ (тільки якщо є права)
                        bulk_actions_r = ui.row().classes('items-center gap-2 transition-all')
                        bulk_actions_r.set_visibility(False)
                        if can_assign:
                            with bulk_actions_r:
                                ui.label('Вибрано:').classes('text-sm text-gray-600')
                                bulk_assign_select_r = ui.select(user_options, label='Призначити вибрані').props(
                                    'dense outlined').classes('w-48')
                                ui.button('Призначити', icon='person_add',
                                          on_click=lambda: assign_selected(selection_r, bulk_assign_select_r.value,
                                                                           False)).props('color="secondary" size="sm"')

                        def update_bulk_r_visibility(filename, is_checked):
                            if is_checked:
                                selection_r.add(filename)
                            else:
                                selection_r.discard(filename)
                            bulk_actions_r.set_visibility(len(selection_r) > 0)

                    if not root_files:
                        ui.label('Спільна папка порожня.').classes('text-gray-500 italic p-6 text-center w-full')
                    else:
                        for f in root_files:
                            with ui.row().classes(
                                    'w-full p-4 border-b border-gray-100 items-center justify-between hover:bg-gray-50 flex-nowrap'):
                                with ui.row().classes('items-center gap-3 flex-grow overflow-hidden'):
                                    cb = ui.checkbox(
                                        on_change=lambda e, fname=f: update_bulk_r_visibility(fname, e.value))
                                    checkboxes_r[f] = cb

                                    ui.icon('description', size='md', color='gray-400')
                                    ui.label(f).classes('text-gray-700 font-medium truncate').tooltip(f)

                                if can_assign:
                                    with ui.row().classes('items-center gap-2 flex-nowrap'):
                                        assignee_select = ui.select(user_options, label='Оберіть юзера').props(
                                            'dense outlined').classes('w-56')
                                        ui.button('Призначити', icon='person_add',
                                                  on_click=lambda file_name=f, sel=assignee_select: assign_file(
                                                      file_name, sel.value, False)).props(
                                            'color="secondary" size="sm"').classes('whitespace-nowrap')

        except Exception as e:
            files_container.clear()
            with files_container:
                ui.notify(f'Помилка завантаження Inbox: {e}', type='negative')

    # ==========================================
    # ФУНКЦІЇ ДЛЯ МАСОВИХ ДІЙ
    # ==========================================
    async def assign_selected(selected_set: set, target_username: str, is_personal: bool):
        if not target_username:
            ui.notify('Спочатку оберіть користувача зі списку!', type='warning')
            return
        if not selected_set: return

        try:
            for fname in list(selected_set):
                await run.io_bound(inbox_ctrl.assign_file, ctx, fname, is_personal, target_username)
            ui.notify(f'{len(selected_set)} файлів переміщено до {target_username}', type='positive')
            await load_data()
        except Exception as e:
            ui.notify(f'Помилка масового призначення: {e}', type='negative')

    async def delete_selected_p(selected_set: set):
        if not selected_set: return
        dialog = ui.dialog()
        with dialog, ui.card().classes('p-6 min-w-[300px]'):
            ui.label('Підтвердження масового видалення').classes('text-xl font-bold text-red-600 mb-2')
            ui.label(f'Ви дійсно хочете назавжди видалити {len(selected_set)} файлів?').classes('text-gray-700 mb-6')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Скасувати', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                ui.button('Видалити', on_click=lambda: dialog.submit(True)).props('color="red"')

        if await dialog:
            try:
                for fname in list(selected_set):
                    await run.io_bound(inbox_ctrl.delete_personal_file, ctx, fname)
                ui.notify(f'{len(selected_set)} файлів успішно видалено', type='positive')
                await load_data()
            except Exception as e:
                ui.notify(f'Помилка масового видалення: {e}', type='negative')

    async def download_selected(selected_set: set):
        # Щоб браузер не заблокував множинні popup-вікна, завантажуємо з невеличкою паузою
        for fname in list(selected_set):
            try:
                file_buffer = await run.io_bound(inbox_ctrl.download_personal_file, ctx, fname)
                if file_buffer:
                    ui.download(file_buffer.getvalue(), fname)
                    await asyncio.sleep(0.5)  # Пауза для браузера
            except Exception as e:
                ui.notify(f'Помилка завантаження {fname}: {e}', type='negative')
        ui.notify('Масове завантаження розпочато!', type='positive')

    # ==========================================
    # ФУНКЦІЇ ДЛЯ ОДИНИЧНИХ ДІЙ (Ваші без змін)
    # ==========================================
    async def download_file(filename: str):
        try:
            file_buffer = await run.io_bound(inbox_ctrl.download_personal_file, ctx, filename)
            if file_buffer:
                ui.download(file_buffer.getvalue(), filename)
            else:
                ui.notify('Файл не знайдено', type='warning')
        except Exception as e:
            pass

    def create_task_from_file(filename: str):
        ui.notify(f'TODO: Відкрити створення задачі для: {filename}', type='info')

    async def assign_file(filename: str, target_username: str, is_personal: bool):
        if not target_username:
            ui.notify('Спочатку оберіть юзера!', type='warning')
            return
        try:
            await run.io_bound(inbox_ctrl.assign_file, ctx, filename, is_personal, target_username)
            await load_data()
        except Exception as e:
            pass

    async def delete_file_with_confirm(filename: str):
        dialog = ui.dialog()
        with dialog, ui.card().classes('p-4 min-w-[300px]'):
            ui.label(f'Видалити "{filename}"?').classes('font-bold')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Ні', on_click=lambda: dialog.submit(False)).props('flat color="gray"')
                ui.button('Так', on_click=lambda: dialog.submit(True)).props('color="red"')

        if await dialog:
            await run.io_bound(inbox_ctrl.delete_personal_file, ctx, filename)
            await load_data()

    ui.timer(0.1, load_data, once=True)