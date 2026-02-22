from nicegui import ui
from gui.components import menu

def render_document_page(controller):
    menu()
    ui.label('Масове створення супровідних листів').classes('w-full text-center text-3xl font-bold mb-8')

    with ui.grid(columns=12).classes('w-full gap-6 items-start'):

        # ЛІВА ЧАСТИНА: ФОРМА
        with ui.card().classes('col-span-12 md:col-span-8 w-full'):
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                city = ui.radio(['Миколаїв', 'Дніпро', 'Донецьк'], value='Миколаїв').props('inline')
                supp_number_input = ui.input('Загальний номер супроводу').classes('w-1/3')

            ui.label('Дані військовослужбовця').classes('text-lg font-bold text-gray-700')
            name_input = ui.input('ПІБ повністю').classes('w-full')

            with ui.row().classes('w-full gap-4'):
                total_input = ui.number('Загалом сторінок', value=0, format='%.0f').classes('w-1/3')

            def icon_number(label, icon_name, value):
                """Створює числове поле з іконкою зліва"""
                num_input = ui.number(label, value=value, format='%.0f')
                # Додаємо іконку у слот 'prepend' (зліва всередині поля)
                with num_input.add_slot('prepend'):
                    ui.icon(icon_name).classes('text-gray-500 text-2xl')  # text-2xl задає гарний розмір
                return num_input

            ui.label('Деталізація сторінок:').classes('mt-4 text-gray-500')
            with ui.grid(columns=3).classes('w-full gap-2'):
                # Рядок 1
                notif = icon_number('Повідомлення', 'campaign', 1)  # Гучномовець (оповіщення)
                assign = icon_number('Наказ про призначення', 'assignment_ind', 3)  # Документ з людиною
                result = icon_number('Наказ про результати', 'fact_check', 3)  # Документ з галочкою (результат)

                # Рядок 2
                act = icon_number('Акти', 'gavel', 4)  # Молоток (акт/юридична дія)
                expl = icon_number('Пояснення', 'speaker_notes', 4)  # Нотатки (пояснення зі слів)
                ui.label('')

                # Рядок 3
                char = icon_number('Службова характеристика', 'military_tech', 2)  # Військова нагорода/оцінка
                med = icon_number('Медична характеристика', 'medical_services', 1)  # Валізка з хрестом
                card = icon_number('Службова картка', 'badge', 2)  # Бейдж/посвідчення

                # Рядок 4
                set_docs = icon_number('Витяг про переміщення', 'transfer_within_a_station', 2)  # Стрілки переміщення
                move = icon_number('Витяг про СЗЧ', 'directions_run', 1)  # Бігун
                other = icon_number('Інша документація', 'folder_copy', 0)  # Папка з копіями

            def clear_inputs():
                name_input.value = ''
                for field in [total_input, notif, assign, result, act, expl, char, med, card, set_docs, move, other]:
                    field.value = 0

            def on_add_click():
                if not name_input.value:
                    ui.notify('Введіть ПІБ!', type='negative')
                    return

                total_val = int(total_input.value or 0)
                fields = [notif, assign, result, act, expl, char, med, card, set_docs, move, other]
                calculated_sum = sum([int(f.value or 0) for f in fields])
                # 3. Порівнюємо тепер цілі числа (наприклад, 20 != 20)
                if calculated_sum != total_val:
                    ui.notify(f'Помилка! Загальна ({total_val}) != Сумі ({calculated_sum})', type='negative')
                    return

                raw_data = {
                    'name': name_input.value,
                    'total': int(total_input.value or 0),
                    'notif': int(notif.value or 0),
                    'assign': int(assign.value or 0),
                    'result': int(result.value or 0),
                    'act': int(act.value or 0),
                    'expl': int(expl.value or 0),
                    'char': int(char.value or 0),
                    'med': int(med.value or 0),
                    'card': int(card.value or 0),
                    'set_docs': int(set_docs.value or 0),
                    'move': int(move.value or 0),
                    'other': int(other.value or 0),
                }

                controller.add_to_buffer(raw_data)
                refresh_buffer_ui()
                clear_inputs()
                ui.notify(f"{raw_data['name']} додано!", type='positive')

            ui.button('Додати до списку', on_click=on_add_click, icon='add').classes('w-full mt-4 bg-blue-500 text-white')

        # ПРАВА ЧАСТИНА: БУФЕР
        with ui.column().classes('col-span-12 md:col-span-4 w-full'):
            ui.label('Додані до пакету:').classes('text-xl font-bold')
            buffer_container = ui.column().classes('w-full gap-2 p-4 border rounded bg-gray-50 min-h-[200px]')

            def on_remove_click(idx):
                controller.remove_from_buffer(idx)
                refresh_buffer_ui()

            def refresh_buffer_ui():
                buffer_container.clear()
                buffer_data = controller.get_buffer()

                with buffer_container:
                    if not buffer_data:
                        ui.label('Список порожній.').classes('text-gray-400 italic')
                    else:
                        for i, doc in enumerate(buffer_data):
                            with ui.row().classes(
                                    'w-full justify-between items-center bg-white p-2 border rounded shadow-sm'):
                                ui.label(f"{i + 1}. {doc['name']} ({doc['total']} стор.)").classes('font-medium')
                                ui.button(icon='delete', color='red',
                                          on_click=lambda idx=i: on_remove_click(idx)).props('flat dense')

                generate_btn.set_visibility(len(buffer_data) > 0)

            async def on_generate_click():
                try:
                    # магія
                    file_bytes, file_name = controller.generate_support_document(city.value, supp_number_input.value)
                    ui.download(file_bytes, file_name)
                    ui.notify('Пакет успішно згенеровано!', type='positive', color='green')
                except ValueError as ve:
                    ui.notify(str(ve), type='warning')
                except Exception as e:
                    ui.notify(f'Помилка генерації: {e}', type='negative')

            generate_btn = ui.button('ЗГЕНЕРУВАТИ ПАКЕТ', on_click=on_generate_click, icon='download').classes(
                'w-full mt-4 h-12').props('color="green"')

            refresh_buffer_ui()