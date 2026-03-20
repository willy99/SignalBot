from nicegui import ui, run
from gui.controllers.config_controller import ConfigController
from gui.services.request_context import RequestContext


def render_settings_page(config_ctrl: ConfigController, ctx: RequestContext):
    with ui.row().classes('w-full justify-between items-center mb-6'):
        ui.label('⚙️ Налаштування системи').classes('text-3xl font-bold text-gray-800')

        save_btn = ui.button('ЗБЕРЕГТИ ЗМІНИ', icon='save', on_click=lambda: save_settings()) \
            .props('color="green" size="lg"').classes('shadow-md')

    # Отримуємо всі налаштування з БД
    try:
        configs = config_ctrl.get_all_configs(ctx)
    except Exception as e:
        ui.notify(f'Помилка завантаження налаштувань: {e}', type='negative')
        return

    # Групуємо по категоріях
    categories = {}
    for conf in configs:
        if conf.category not in categories:
            categories[conf.category] = []
        categories[conf.category].append(conf)

    # Стан для прив'язки UI
    state = {conf.key_name: conf.get_typed_value() for conf in configs}

    async def save_settings():
        save_btn.props('loading')
        try:
            for conf in configs:
                new_val = state[conf.key_name]
                await run.io_bound(config_ctrl.update_config_value, ctx, conf.key_name, str(new_val))

            await run.io_bound(config_ctrl.apply_configs_to_runtime, ctx)
            ui.notify('✅ Налаштування успішно збережено та застосовано!', type='positive')
        except Exception as e:
            ui.notify(f'❌ Помилка збереження: {e}', type='negative')
        finally:
            save_btn.props(remove='loading')

    # Малюємо UI
    with ui.card().classes('w-full max-w-none mx-auto p-0 shadow-sm'):
        with ui.tabs().classes('w-full bg-blue-50 text-blue-900 font-bold border-b border-blue-100') as tabs:
            for cat in categories.keys():
                ui.tab(cat)

        first_category = list(categories.keys())[0] if categories else None

        with ui.tab_panels(tabs, value=first_category).classes('w-full p-4 bg-gray-50'):
            for cat, conf_list in categories.items():
                with ui.tab_panel(cat):

                    # Замість сітки використовуємо колонку (список)
                    with ui.column().classes('w-full gap-2'):

                        for conf in conf_list:
                            # Один параметр = один довгий рядок
                            with ui.row().classes(
                                    'w-full items-center py-3 px-4 bg-white rounded-md border border-gray-200 shadow-sm hover:bg-blue-50 transition-colors flex-nowrap'):

                                # 1. КОЛОНКА: Назва параметру (Ключ)
                                with ui.column().classes('w-1/4 min-w-[200px] shrink-0 gap-0'):
                                    ui.label(conf.key_name).classes('font-mono font-bold text-gray-800 text-sm')
                                    # Маленька підказка щодо типу даних
                                    if conf.value_type == 'bool':
                                        ui.label('Перемикач').classes('text-[10px] text-gray-400 uppercase tracking-wider')
                                    elif conf.value_type in ['int', 'float']:
                                        ui.label('Число').classes('text-[10px] text-gray-400 uppercase tracking-wider')
                                    else:
                                        ui.label('Текст / Шлях').classes('text-[10px] text-gray-400 uppercase tracking-wider')

                                # 2. КОЛОНКА: Опис (Займає половину ширини екрану)
                                with ui.column().classes('w-1/2 flex-grow gap-0 pr-4'):
                                    ui.label(conf.description).classes('text-sm text-gray-700')

                                    if conf.validation_rule:
                                        ui.label(f'Правило: {conf.validation_rule}').classes('text-xs text-indigo-400 mt-1 italic')

                                # 3. КОЛОНКА: Поле вводу
                                with ui.row().classes('w-1/4 min-w-[300px] shrink-0 justify-end items-center'):
                                    if conf.value_type == 'bool':
                                        ui.switch().bind_value(state, conf.key_name).props('color="green"')

                                    elif conf.value_type == 'int':
                                        ui.number(format='%.0f').bind_value(state, conf.key_name) \
                                            .classes('w-32').props('outlined dense')

                                    elif conf.value_type == 'float':
                                        ui.number(format='%.1f').bind_value(state, conf.key_name) \
                                            .classes('w-32').props('outlined dense step="0.1"')

                                    else:  # str
                                        # Текстове поле робимо дуже широким, щоб було зручно редагувати шляхи
                                        ui.input().bind_value(state, conf.key_name) \
                                            .classes('w-full max-w-[450px]').props('outlined dense')