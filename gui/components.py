from nicegui import ui


def menu():
    ui.add_head_html('<link rel="stylesheet" href="../static/style.css">')

    with ui.header().classes('bg-slate-800 items-center justify-between'):
        # Робимо логотип клікабельним, щоб він повертав на Головну (Дашборд)
        ui.button('А0224, 🏃‍♂️RUNNERS AND SOLDIERS 👨‍🚀', on_click=lambda: ui.navigate.to('/')) \
            .props('flat').classes('font-bold text-xl text-white normal-case')

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