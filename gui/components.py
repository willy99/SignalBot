from nicegui import ui, app


def menu():
    ui.add_head_html('<link rel="stylesheet" href="../static/style.css">')

    with ui.header().classes('bg-slate-800 items-center justify-between'):
        with ui.row().classes('items-center gap-2'):
            ui.button('А0224, 🏃‍♂️RUNNERS AND SOLDIERS 👨‍🚀', on_click=lambda: ui.navigate.to('/')) \
                .props('flat').classes('font-bold text-xl text-white normal-case')

            # 🌟 ІКОНКА INBOX
            with ui.button(icon='mail').props('flat round color="white"') \
                    .bind_visibility_from(app.inbox_state, 'count', backward=lambda x: x > 0) as inbox_btn:
                ui.badge().props('color="red" floating') \
                    .bind_text_from(app.inbox_state, 'count').classes('text-xs')
                with ui.menu().classes('w-80 max-h-96 overflow-y-auto') as inbox_menu:
                    pass

            def update_inbox_menu():
                inbox_menu.clear()
                with inbox_menu:
                    ui.label('Очікують в Inbox:').classes('font-bold text-gray-700 px-3 py-2 border-b w-full')

                    files = app.inbox_state.get('files', [])
                    if not files:
                        ui.label('Папка порожня').classes('text-gray-500 italic p-3')
                    else:
                        for f in files:
                            with ui.row().classes(
                                    'items-center gap-2 px-3 py-2 w-full hover:bg-gray-50 border-b border-gray-100 last:border-0'):
                                ui.icon('description', size='sm', color='gray-400')
                                ui.label(f).classes('text-sm text-gray-600 truncate').style('max-width: 240px;')
            inbox_btn.on('click', update_inbox_menu)

        with ui.row():
            ui.button('Головна', on_click=lambda: ui.navigate.to('/')).props('flat text-white icon="home"')
            # Зверніть увагу, маршрут змінено на /search
            ui.button('Пошук', on_click=lambda: ui.navigate.to('/search')).props('flat text-white')
            ui.button('ЄРДР', on_click=lambda: ui.navigate.to('/erdr')).props('flat text-white')

            with ui.button('Документація').props('flat text-white icon-right="expand_more"'):
                with ui.menu():
                    ui.menu_item('Довідки', on_click=lambda: ui.navigate.to('/notif_doc'))
                    ui.menu_item('Супроводи', on_click=lambda: ui.navigate.to('/support_doc'))

            with ui.button('Звіти').props('flat text-white icon-right="expand_more"'):
                with ui.menu():
                    ui.menu_item('Звіт по підрозділам', on_click=lambda: ui.navigate.to('/report'))
                    ui.menu_item('Логі системи', on_click=lambda: ui.navigate.to('/logs'))