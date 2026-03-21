from nicegui import ui, run
import re
from gui.controllers.config_controller import ConfigController
from gui.services.request_context import RequestContext


def render_settings_page(config_ctrl: ConfigController, ctx: RequestContext):
    with ui.row().classes('w-full justify-between items-center mb-6'):
        ui.label('⚙️ Налаштування системи').classes('text-3xl font-bold text-gray-800')

        save_btn = ui.button('ЗБЕРЕГТИ ЗМІНИ', icon='save', on_click=lambda: save_settings()) \
            .props('color="green" size="lg"').classes('shadow-md')

    try:
        configs = config_ctrl.get_all_configs(ctx)
    except Exception as e:
        ui.notify(f'Помилка завантаження налаштувань: {e}', type='negative')
        return

    # Групуємо по категоріях
    categories_raw = {}
    for conf in configs:
        if conf.category not in categories_raw:
            categories_raw[conf.category] = []
        categories_raw[conf.category].append(conf)

    # 💡 СОРТУВАННЯ ТАБІВ: Задаємо бажаний порядок
    desired_order = ['Основні', 'Шляхи', 'Час та Логіка', 'Технічні', 'Excel', 'UI']
    # Спочатку ті, що є у списку, потім всі інші
    sorted_cat_keys = sorted(categories_raw.keys(), key=lambda x: desired_order.index(x) if x in desired_order else 999)
    categories = {k: categories_raw[k] for k in sorted_cat_keys}

    state = {conf.key_name: conf.get_typed_value() for conf in configs}

    async def save_settings():
        save_btn.props('loading')
        try:
            for conf in configs:
                raw_val = state[conf.key_name]

                # 💡 ПРАВИЛЬНИЙ КАСТ ТИПІВ ПЕРЕД ЗБЕРЕЖЕННЯМ
                if conf.value_type == 'int':
                    try:
                        clean_val = int(float(raw_val))  # Рятує від 2000.0
                    except (ValueError, TypeError):
                        clean_val = 0
                elif conf.value_type == 'bool':
                    clean_val = 'True' if raw_val else 'False'
                elif conf.value_type == 'float':
                    try:
                        clean_val = float(raw_val)
                    except (ValueError, TypeError):
                        clean_val = 0.0
                else:
                    clean_val = str(raw_val).strip()

                await run.io_bound(config_ctrl.update_config_value, ctx, conf.key_name, str(clean_val))

            await run.io_bound(config_ctrl.apply_configs_to_runtime, ctx)
            ui.notify('✅ Налаштування успішно збережено та застосовано!', type='positive')
        except Exception as e:
            ui.notify(f'❌ Помилка збереження: {e}', type='negative')
        finally:
            save_btn.props(remove='loading')

    with ui.card().classes('w-full max-w-none mx-auto p-0 shadow-sm'):
        with ui.tabs().classes('w-full bg-blue-50 text-blue-900 font-bold border-b border-blue-100') as tabs:
            for cat in categories.keys():
                ui.tab(cat)

        first_category = list(categories.keys())[0] if categories else None

        with ui.tab_panels(tabs, value=first_category).classes('w-full p-4 bg-gray-50'):
            for cat, conf_list in categories.items():
                with ui.tab_panel(cat):

                    with ui.column().classes('w-full gap-2'):
                        for conf in conf_list:

                            # 💡 ПАРСИНГ ПРАВИЛ ВАЛІДАЦІЇ
                            v_min, v_max, v_regex = None, None, None
                            if conf.validation_rule:
                                rules = conf.validation_rule.split('|')
                                for rule in rules:
                                    if rule.startswith('min:'):
                                        v_min = rule.split(':')[1]
                                    elif rule.startswith('max:'):
                                        v_max = rule.split(':')[1]
                                    elif rule.startswith('regex:'):
                                        v_regex = rule.split(':', 1)[1]

                            with ui.row().classes(
                                    'w-full items-center py-3 px-4 bg-white rounded-md border border-gray-200 shadow-sm hover:bg-blue-50 transition-colors flex-nowrap'):

                                # 1. Назва
                                with ui.column().classes('w-1/4 min-w-[200px] shrink-0 gap-0'):
                                    ui.label(conf.key_name).classes('font-mono font-bold text-gray-800 text-sm')
                                    if conf.value_type == 'bool':
                                        ui.label('Перемикач').classes('text-[10px] text-gray-400 uppercase tracking-wider')
                                    elif conf.value_type in ['int', 'float']:
                                        ui.label('Число').classes('text-[10px] text-gray-400 uppercase tracking-wider')
                                    else:
                                        ui.label('Текст / Шлях').classes('text-[10px] text-gray-400 uppercase tracking-wider')

                                # 2. Опис
                                with ui.column().classes('w-1/2 flex-grow gap-0 pr-4'):
                                    ui.label(conf.description).classes('text-sm text-gray-700')
                                    if conf.validation_rule:
                                        ui.label(f'Правило: {conf.validation_rule}').classes('text-xs text-indigo-400 mt-1 italic')

                                # 3. Поле вводу + застосування правил
                                with ui.row().classes('w-1/4 min-w-[300px] shrink-0 justify-end items-center'):
                                    if conf.value_type == 'bool':
                                        ui.switch().bind_value(state, conf.key_name).props('color="green"')

                                    elif conf.value_type == 'int':
                                        el = ui.number(format='%.0f').bind_value(state, conf.key_name).classes('w-32').props('outlined dense')
                                        # Застосовуємо min/max до HTML input
                                        if v_min: el.props(f'min="{v_min}"')
                                        if v_max: el.props(f'max="{v_max}"')

                                    elif conf.value_type == 'float':
                                        el = ui.number(format='%.1f').bind_value(state, conf.key_name).classes('w-32').props('outlined dense step="0.1"')
                                        if v_min: el.props(f'min="{v_min}"')
                                        if v_max: el.props(f'max="{v_max}"')

                                    else:  # str
                                        # Якщо є regex, додаємо валідацію NiceGUI
                                        val_dict = {}
                                        if v_regex:
                                            # Зберігаємо патерн у замиканні лямбди
                                            val_dict['Невірний формат'] = lambda v, p=v_regex: bool(re.match(p, str(v).strip())) if v else True

                                        el = ui.input(validation=val_dict if val_dict else None).bind_value(state, conf.key_name).classes('w-full max-w-[450px]').props(
                                            'outlined dense')

                                        # Якщо це колір (є слово COLOR у ключі), додаємо маленький квадратик з цим кольором для зручності
                                        if 'COLOR' in conf.key_name and v_regex:
                                            with el.add_slot('prepend'):
                                                # Динамічно показуємо колір
                                                color_box = ui.html().bind_content_from(state, conf.key_name, backward=lambda
                                                    c: f'<div style="width: 16px; height: 16px; background-color: #{c}; border: 1px solid #ccc; border-radius: 3px;"></div>')