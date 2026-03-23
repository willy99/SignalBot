import re
from nicegui import ui, run
from dics.deserter_xls_dic import PATTERN_NAME_WITH_CASE
from domain.person_filter import PersonSearchFilter

# Переконайтеся, що імпортували ваші класи та константи:
# from gui.services.request_context import RequestContext
# from domain.filters import PersonSearchFilter

def render_bulk_search_page(person_ctrl, ctx):
    ui.label('Масовий пошук осіб').classes('w-full text-center text-3xl font-bold mb-6')

    with ui.card().classes('w-full max-w-4xl mx-auto p-6 shadow-md'):
        ui.label('Вставте текст зі списком ПІБ:').classes('text-lg font-medium text-gray-700 mb-2')

        # Поле для вводу масиву тексту
        text_input = ui.textarea(
            placeholder='Наприклад:\nСКЛІФАСОВСЬКИЙ Андрій Вадимович\nСамаруха Володимир Володимирович...') \
            .classes('w-full mb-4').props('outlined rows=10')

        search_btn = ui.button('Почати пошук', icon='search').props('color="primary" size="lg"').classes('w-full mb-4')

    # Контейнер для виводу результатів
    results_container = ui.column().classes('w-full max-w-4xl mx-auto mt-6 gap-2')

    async def perform_bulk_search():
        raw_text = text_input.value or ""

        if not raw_text.strip():
            ui.notify("Введіть текст для пошуку!", type='warning')
            return

        extracted_names = []

        # 1. Читаємо текст по-рядково
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue  # Пропускаємо порожні рядки

            # Шукаємо збіги в конкретному рядку
            matches = re.finditer(PATTERN_NAME_WITH_CASE, line)

            for m in matches:
                name = m.group(0).strip()
                # СИЛОВЕ ОЧИЩЕННЯ: прибираємо коми, крапки з комою та пробіли з кінця
                name = name.rstrip(' ,;')

                if name:
                    extracted_names.append(name)

        # Прибираємо дублікати, але зберігаємо оригінальний порядок
        seen = set()
        unique_names = [x for x in extracted_names if not (x in seen or seen.add(x))]

        if not unique_names:
            ui.notify("Не знайдено жодного ПІБ за вашим патерном!", type='negative')
            return

            # Блокуємо кнопку
        search_btn.disable()
        search_btn.set_text(f'Аналізуємо {len(unique_names)} осіб...')
        search_btn.props('icon="hourglass_empty"')

        results_container.clear()

        try:
            # 1. Виконуємо МАСОВИЙ пошук ОДНИМ запитом
            # Припускаю, що person_ctrl має метод-обгортку batch_search_names, який смикає ExcelProcessor
            search_results = await run.io_bound(person_ctrl.batch_search_names, ctx, unique_names)

            with results_container:
                # Рахуємо статистику
                found_count = sum(1 for r in search_results if r['found'])
                not_found_count = len(search_results) - found_count

                with ui.row().classes('w-full justify-between items-end mb-4'):
                    ui.label(f'Всього розпізнано: {len(unique_names)}').classes('font-bold text-gray-600 text-xl')
                    ui.label(f'✅ В базі: {found_count} | ❌ Відсутні: {not_found_count}').classes('text-sm font-medium')

                # 2. Малюємо вже відсортовані результати
                for item in search_results:
                    bg_color = 'bg-white' if item['found'] else 'bg-red-50'

                    with ui.row().classes(
                            f'w-full items-center justify-between p-3 border rounded-lg {bg_color} shadow-sm'):
                        ui.label(item['name']).classes('text-md font-medium')

                        if item['found']:
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Є в базі').classes('text-xs text-green-600')
                                ui.icon('check_circle', color='green', size='sm')
                        else:
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Відсутній').classes('text-xs text-red-500 font-bold')
                                ui.icon('cancel', color='red', size='sm')

        except Exception as e:
            ui.notify(f"Помилка масового пошуку: {e}", type="negative")

        finally:
            search_btn.enable()
            search_btn.set_text('Почати пошук')
            search_btn.props('icon="search"')
            ui.notify('Аналіз завершено!', type='positive')

    # Прив'язуємо клік
    search_btn.on('click', perform_bulk_search)