from nicegui import ui, run
from gui.services.request_context import RequestContext

# --- КОНСТАНТИ ДЕФОЛТНИХ ЗНАЧЕНЬ СТОРІНОК ---
# Константи залишаються без змін...
DEF_NOTIF, DEF_ASSIGN, DEF_RESULT = 1, 3, 3
DEF_ACT, DEF_EXPL, DEF_CHAR = 4, 4, 2
DEF_MED, DEF_CARD, DEF_SET_DOCS, DEF_MOVE, DEF_OTHER = 1, 2, 2, 1, 0


def render_document_page(controller, ctx: RequestContext, draft_id: int = None):
    ui.label('Масове створення супровідних листів').classes('w-full text-center text-3xl font-bold mb-8')

    state = {
        'edit_idx': None,
        'buffer': [],
        'current_search_results': {},
        'current_support_doc_id': draft_id
    }

    with ui.grid(columns=12).classes('w-full gap-6 items-start'):

        with ui.card().classes('col-span-12 md:col-span-8 w-full'):
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                city = ui.radio(['Миколаїв', 'Дніпро', 'Донецьк'], value='Миколаїв').props('inline')
                supp_number_input = ui.input('Загальний номер супроводу').classes('w-1/3')

            ui.label('Пошук військовослужбовця').classes('text-lg font-bold text-gray-700')

            with ui.row().classes('w-full gap-2 items-center'):
                search_input = ui.input('Введіть прізвище...').classes('flex-grow').props('clearable autofocus')
                search_btn = ui.button('Шукати', icon='search').props('elevated color="primary"')

            person_select = ui.select(
                options={},
                label='Оберіть особу зі знайдених'
            ).classes('w-full mt-2')
            person_select.visible = False

            async def perform_search(e=None):
                query = search_input.value
                if not query or len(query) < 2:
                    ui.notify('Введіть мінімум 2 літери для пошуку', type='warning')
                    return

                search_btn.disable()
                try:
                    results = await run.io_bound(controller.search_persons, ctx, query)

                    state['current_search_results'].clear()
                    options = {}

                    for person in results:
                        id_num = f"{person.rnokpp}_{person.name}_{person.desertion_date}"
                        state['current_search_results'][id_num] = {
                            'name': person.name,
                            'rnokpp': person.rnokpp,
                            'id_number': id_num  # Зберігаємо ключ
                        }
                        options[id_num] = f"{person.name} (РНОКПП: {person.rnokpp} СЗЧ: {person.desertion_date})"

                    person_select.options = options
                    person_select.visible = True

                    if options:
                        person_select.value = list(options.keys())[0]  # Автовибір першого
                        ui.notify(f'Знайдено збігів: {len(options)}', type='info')
                    else:
                        ui.notify('За цим запитом нікого не знайдено', type='warning')
                        person_select.visible = False

                except Exception as ex:
                    ui.notify(f'Помилка пошуку: {ex}', type='negative')
                finally:
                    search_btn.enable()

            search_input.on('keydown.enter', perform_search)
            search_btn.on('click', perform_search)

            with ui.row().classes('w-full gap-4 mt-6'):
                total_input = ui.number('Загалом сторінок', value=0, format='%.0f').classes('w-1/3')

            def icon_number(label, icon_name, value):
                num_input = ui.number(label, value=value, format='%.0f')
                with num_input.add_slot('prepend'):
                    ui.icon(icon_name).classes('text-gray-500 text-2xl')
                return num_input

            ui.label('Деталізація сторінок:').classes('mt-4 text-gray-500')
            with ui.grid(columns=3).classes('w-full gap-2'):
                notif = icon_number('Повідомлення', 'campaign', DEF_NOTIF)
                assign = icon_number('Наказ про призначення', 'assignment_ind', DEF_ASSIGN)
                result = icon_number('Наказ про результати', 'fact_check', DEF_RESULT)

                act = icon_number('Акти', 'gavel', DEF_ACT)
                expl = icon_number('Пояснення', 'speaker_notes', DEF_EXPL)
                ui.label('')

                char = icon_number('Службова характеристика', 'military_tech', DEF_CHAR)
                med = icon_number('Медична характеристика', 'medical_services', DEF_MED)
                card = icon_number('Службова картка', 'badge', DEF_CARD)

                set_docs = icon_number('Витяг про переміщення', 'transfer_within_a_station', DEF_SET_DOCS)
                move = icon_number('Витяг про СЗЧ', 'directions_run', DEF_MOVE)
                other = icon_number('Інша документація', 'folder_copy', DEF_OTHER)

            def update_btn_state():
                if state['edit_idx'] is not None:
                    add_btn.text = 'Зберегти зміни'
                    add_btn.props('color="orange"')
                    add_btn.icon = 'save'
                    cancel_btn.set_visibility(True)
                else:
                    add_btn.text = 'Додати до пакету'
                    add_btn.props('color="blue"')
                    add_btn.icon = 'add'
                    cancel_btn.set_visibility(False)

            def clear_inputs():
                state['edit_idx'] = None
                search_input.value = ''
                person_select.value = None
                person_select.visible = False
                total_input.value = 0

                notif.value = DEF_NOTIF
                assign.value = DEF_ASSIGN
                result.value = DEF_RESULT
                act.value = DEF_ACT
                expl.value = DEF_EXPL
                char.value = DEF_CHAR
                med.value = DEF_MED
                card.value = DEF_CARD
                set_docs.value = DEF_SET_DOCS
                move.value = DEF_MOVE
                other.value = DEF_OTHER

                update_btn_state()

            def on_add_click():
                selected_id = person_select.value
                if not selected_id:
                    ui.notify('Будь ласка, знайдіть та оберіть військовослужбовця!', type='negative')
                    return

                buffer_data = state['buffer']
                edit_idx = state['edit_idx']

                existing_ids = [doc['id_number'] for i, doc in enumerate(buffer_data) if i != edit_idx]
                if selected_id in existing_ids:
                    ui.notify(f'Ця особа вже є у списку пакету!', type='warning')
                    return

                selected_person = state['current_search_results'].get(selected_id, {})
                name_val = selected_person.get('name', 'Невідоме ПІБ')

                total_val = int(total_input.value or 0)
                fields = [notif, assign, result, act, expl, char, med, card, set_docs, move, other]
                calculated_sum = sum([int(f.value or 0) for f in fields])

                if calculated_sum != total_val:
                    ui.notify(f'Помилка! Загальна ({total_val}) != Сумі ({calculated_sum})', type='negative')
                    return

                raw_data = {
                    'id_number': selected_id,  # Наш комбінований ключ
                    'name': name_val,
                    'total': total_val,
                    'notif': int(notif.value or DEF_NOTIF),
                    'assign': int(assign.value or DEF_ASSIGN),
                    'result': int(result.value or DEF_RESULT),
                    'act': int(act.value or DEF_ACT),
                    'expl': int(expl.value or DEF_EXPL),
                    'char': int(char.value or DEF_CHAR),
                    'med': int(med.value or DEF_MED),
                    'card': int(card.value or DEF_CARD),
                    'set_docs': int(set_docs.value or DEF_SET_DOCS),
                    'move': int(move.value or DEF_MOVE),
                    'other': int(other.value or DEF_OTHER),
                }

                if edit_idx is not None:
                    buffer_data[edit_idx] = raw_data
                    ui.notify(f"Дані оновлено!", type='positive')
                else:
                    buffer_data.append(raw_data)
                    ui.notify(f"Додано до драфту!", type='positive')

                refresh_buffer_ui()
                clear_inputs()

            with ui.row().classes('w-full mt-4 gap-2'):
                add_btn = ui.button('Додати до пакету', on_click=on_add_click, icon='add').classes(
                    'flex-grow bg-blue-500 text-white')
                cancel_btn = ui.button('Скасувати', on_click=clear_inputs, icon='close').props('flat').classes(
                    'text-gray-500 bg-gray-200')
                cancel_btn.set_visibility(False)

        # ==========================================
        # ПРАВА ЧАСТИНА: БУФЕР (DRAFT)
        # ==========================================
        with ui.column().classes('col-span-12 md:col-span-4 w-full'):
            ui.label('Поточний пакет (Чернетка):').classes('text-xl font-bold')
            buffer_container = ui.column().classes('w-full gap-2 p-4 border rounded bg-gray-50 min-h-[200px]')

            def on_remove_click(idx):
                if 0 <= idx < len(state['buffer']):
                    state['buffer'].pop(idx)
                if state['edit_idx'] == idx:
                    clear_inputs()
                elif state['edit_idx'] is not None and state['edit_idx'] > idx:
                    state['edit_idx'] -= 1
                refresh_buffer_ui()

            def on_edit_click(idx):
                state['edit_idx'] = idx
                doc = state['buffer'][idx]

                id_num = doc['id_number']
                search_input.value = doc['name']

                state['current_search_results'][id_num] = {'name': doc['name'], 'id_number': id_num}
                person_select.options = {id_num: f"{doc['name']} (РНОКПП: {id_num})"}
                person_select.value = id_num
                person_select.visible = True

                total_input.value = doc['total']
                notif.value = doc['notif']
                assign.value = doc['assign']
                result.value = doc['result']
                act.value = doc['act']
                expl.value = doc['expl']
                char.value = doc['char']
                med.value = doc['med']
                card.value = doc['card']
                set_docs.value = doc['set_docs']
                move.value = doc['move']
                other.value = doc['other']

                update_btn_state()
                ui.notify(f"Редагування...", type='info')

            def refresh_buffer_ui():
                buffer_container.clear()
                buffer_data = state['buffer']

                with buffer_container:
                    if not buffer_data:
                        ui.label('Список порожній.').classes('text-gray-400 italic')
                    else:
                        for i, doc in enumerate(buffer_data):
                            with ui.row().classes(
                                    'w-full justify-between items-center bg-white p-2 border rounded shadow-sm'):
                                ui.label(f"{i + 1}. {doc['name']} ({doc['total']} стор.)").classes(
                                    'font-medium text-sm truncate w-2/3')
                                with ui.row().classes('gap-1'):
                                    ui.button(icon='edit', color='blue',
                                              on_click=lambda idx=i: on_edit_click(idx)).props('flat dense size=sm')
                                    ui.button(icon='delete', color='red',
                                              on_click=lambda idx=i: on_remove_click(idx)).props('flat dense size=sm')

                generate_docs_btn.set_visibility(len(buffer_data) > 0)
                save_draft_btn.set_visibility(len(buffer_data) > 0)

            async def on_generate_docs_click():
                try:
                    file_bytes, file_name = controller.generate_support_document(
                        ctx, city.value, supp_number_input.value, state['buffer']
                    )
                    ui.download(file_bytes, file_name)
                    ui.notify('Пакет успішно згенеровано!', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка генерації: {e}', type='negative')

            async def on_save_draft_click():
                if not state['buffer']:
                    ui.notify('Неможливо зберегти: пакет порожній!', type='warning')
                    return

                save_draft_btn.disable()
                try:
                    # Отримуємо логін/ПІБ поточного користувача з контексту

                    # Викликаємо наш новий сервіс (який ви передасте ззовні, або ініціалізуєте)
                    draft_id = await run.io_bound(
                        controller.save_support_doc,
                        ctx,
                        city.value,
                        supp_number_input.value,
                        state['buffer'],
                        state.get('current_support_doc_id')  # Якщо ми редагуємо стару чернетку, передаємо її ID
                    )

                    # Зберігаємо ID поточної чернетки, щоб наступне збереження оновило її, а не створило нову
                    state['current_support_doc_id'] = draft_id

                    ui.notify(f'Чернетку №{draft_id} збережено!', type='positive', icon='cloud_done')
                except Exception as e:
                    ui.notify(f'Помилка БД: {e}', type='negative')
                finally:
                    save_draft_btn.enable()

            generate_docs_btn = ui.button('ЗГЕНЕРУВАТИ WORD', on_click=on_generate_docs_click,
                                          icon='description').classes('w-full mt-4 h-12').props('color="green"')
            save_draft_btn = ui.button('ЗБЕРЕГТИ ЯК ЧЕРНЕТКУ', on_click=on_save_draft_click,
                                       icon='save_as').classes('w-full mt-2 h-10').props('outline color="primary"')

            refresh_buffer_ui()