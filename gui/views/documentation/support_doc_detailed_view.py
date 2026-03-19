from nicegui import ui, run

from dics.deserter_xls_dic import VALID_PATTERN_DOC_NUM
from domain.person_filter import PersonSearchFilter
from gui.services.request_context import RequestContext
from utils.utils import to_genitive_case, to_genitive_title
from gui.tools.validation import is_valid_doc_number
from config import OUTBOX_DIR_PATH
from gui.tools.ui_components import fix_date, date_input, mark_dirty, mark_clean
from service.storage.FileCacher import FileCacheManager
import io
from gui.controllers.person_controller import PersonController
from gui.controllers.support_controller import SupportController
from service.constants import DOC_STATUS_COMPLETED, DOC_STATUS_DRAFT, DOC_PACKAGE_DETAILED
import re

DEF_NOTIF, DEF_ASSIGN, DEF_RESULT = 1, 3, 3
DEF_ACT, DEF_EXPL, DEF_CHAR = 4, 4, 2
DEF_MED, DEF_CARD, DEF_SET_DOCS, DEF_MOVE, DEF_OTHER = 1, 2, 2, 1, 0


def render_document_page(controller: SupportController, person_controller: PersonController,
                         file_cache_manager: FileCacheManager, ctx: RequestContext, draft_id: int = None):
    state = {
        'status': DOC_STATUS_DRAFT,
        'support_date': '',
        'support_number': '',
        'edit_idx': None,
        'buffer': [],
        'current_search_results': {},
        'current_support_doc_id': draft_id,
        'next_seq_num': 1
    }

    async def on_save_draft_click():
        if not state['buffer']:
            ui.notify('Неможливо зберегти: пакет порожній!', type='warning')
            return

        save_draft_btn.disable()
        try:
            draft_new_id = await run.io_bound(
                controller.save_support_doc,
                ctx,
                city.value,
                state.get('support_number', ''),
                state.get('support_date', ''),
                state['buffer'],
                state.get('current_support_doc_id'),
                package_type=DOC_PACKAGE_DETAILED
            )
            state['current_support_doc_id'] = draft_new_id
            ui.notify(f'Чернетку №{draft_new_id} збережено!', type='positive', icon='cloud_done')
            mark_clean()
        except Exception as e:
            ui.notify(f'Помилка БД: {e}', type='negative')
        finally:
            save_draft_btn.enable()

    async def on_generate_docs_click():
        try:
            supp_num = state.get('support_number', '').strip()
            supp_date = state.get('support_date', '')

            if not supp_num or not supp_date:
                ui.notify('Непогано б заповнити дату та номер супроводу!', type='warning')
                return

            if not is_valid_doc_number(supp_num):
                ui.notify('❌ Увага! Невірний формат номера супроводу. Має бути 642/ХХХХ', type='negative')
                return

            await on_save_draft_click()

            generate_docs_btn.props('loading')
            ui.notify('⏳ Генеруємо документи...', type='info')

            file_bytes, file_name = await run.io_bound(
                controller.generate_support_document,
                ctx, city.value, supp_num, supp_date, state['buffer']
            )
            ui.download(file_bytes, file_name)
            ui.notify('Пакет успішно згенеровано!', type='positive')
        except Exception as e:
            ui.notify(f'Помилка генерації: {e}', type='negative')
        finally:
            generate_docs_btn.props(remove='loading')

    async def on_generate_logs_click():
        try:
            supp_num = state.get('support_number', '').strip()
            supp_date = state.get('support_date', '')

            generate_logs_btn.props('loading')
            log_text = await run.io_bound(
                controller.generate_logs,
                ctx, city.value, supp_num, supp_date, state['buffer']
            )
            file_name = f"Пакет_Супроводів_{supp_num}_{supp_date}.txt"
            destination_path = f'{OUTBOX_DIR_PATH}{file_cache_manager.get_file_separator()}{ctx.user_login}{file_cache_manager.get_file_separator()}{file_name.replace("/", "_")}'
            log_buffer = io.BytesIO(log_text.encode('utf-8'))

            client = file_cache_manager.client
            with client:
                await run.io_bound(client.save_file_from_buffer, destination_path, log_buffer)

            ui.notify('Документ для СЕДО збережено в ' + str(destination_path), type="positive")
        except Exception as e:
            ui.notify(f'Помилка генерації СЕДО: {e}', type='negative')
        finally:
            generate_logs_btn.props(remove='loading')

    async def on_send_dbr_click():
        supp_num = state.get('support_number', '').strip()
        supp_date = state.get('support_date', '')

        if not supp_num or not supp_date:
            ui.notify('Непогано б заповнити дату та номер супроводу!', type='warning')
            return

        if not is_valid_doc_number(supp_num):
            ui.notify('❌ Увага! Невірний формат номера супроводу. Має бути 642/ХХХХ', type='negative')
            return

        await on_save_draft_click()

        current_id = state.get('current_support_doc_id')
        if not current_id:
            ui.notify('Спочатку збережіть чернетку!', type='warning')
            return

        complete_btn.disable()
        complete_btn.props('loading')
        ui.notify('⏳ Оновлюємо дані в Excel, зачекайте...', type='info')

        try:
            complete = await run.io_bound(
                controller.mark_as_completed,
                ctx,
                person_controller,
                current_id
            )

            if complete:
                state['status'] = DOC_STATUS_COMPLETED
                refresh_status_ui()
                ui.notify('✅ Документи відправлені, дати та номери проставлені в базі!', type='positive')
            else:
                ui.notify('⚠️ Документи не відправлені, сталася помилка логіки!', type='negative')

        except Exception as e:
            ui.notify(f'❌ Помилка під час відправки: {e}', type='negative')
        finally:
            complete_btn.props(remove='loading')
            if state.get('status') != DOC_STATUS_COMPLETED:
                complete_btn.enable()

    with ui.row().classes('w-full px-4 items-center justify-between mb-6'):
        ui.label('Детальний супровідний лист (По документах)').classes('text-3xl font-bold')

        with ui.row().classes('items-center gap-4'):
            generate_logs_btn = ui.button('INFO ДЛЯ СEДО', icon='description', on_click=on_generate_logs_click).props('outline color="primary"').classes('h-10')
            generate_logs_btn.disable()

            save_draft_btn = ui.button('ЗБЕРЕГТИ ЧЕРНЕТКУ', icon='save', on_click=on_save_draft_click).props('outline color="primary"').classes('h-10')
            save_draft_btn.disable()

            generate_docs_btn = ui.button('СФОРМУВАТИ (WORD)', icon='print', on_click=on_generate_docs_click).props('color="blue"').classes('h-10')
            generate_docs_btn.disable()

            complete_btn = ui.button('ВІДПРАВКА НА ДБР', icon='send', on_click=on_send_dbr_click).props('color="green"').classes('h-10')
            complete_btn.disable()

    with ui.grid(columns=12).classes('w-full px-4 gap-6 items-start'):

        with ui.card().classes('col-span-12 md:col-span-8 w-full'):
            status_text = state.get('status', 'Draft')
            badge_color = 'green' if status_text == 'Completed' else 'grey'

            with ui.row().classes('w-full items-center gap-5 mb-5'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('Статус:').classes('text-gray-500 font-medium')
                    status_badge = ui.badge(status_text, color=badge_color).classes('text-sm px-2 py-1')
                city = ui.radio(['Миколаїв', 'Дніпро', 'Донецьк'], value='Миколаїв').props('inline')

                supp_number_input = ui.input('Загальний номер супроводу', placeholder='Наприклад: 642/123', validation={
                    'Формат має бути 642/ХХХХ (до 4 цифр)': lambda v: bool(re.match(VALID_PATTERN_DOC_NUM, str(v).strip())) if v else True
                }).bind_value(state, 'support_number').classes('flex-1').props('hide-bottom-space')

                supp_date_input = date_input('Дата формування', state, 'support_date', blur_handler=fix_date).classes('flex-1')

            with ui.row().classes('w-full gap-2 items-center'):
                search_input = ui.input('Пошук військовослужбовця. Введіть прізвище...').classes('flex-grow').props(
                    'clearable autofocus')
                search_btn = ui.button('Шукати', icon='search').props('elevated color="primary"')

            def update_badges(status_val, mil_unit_val, has_multiple_events=False):
                if not status_val:
                    review_status_badge.set_visibility(False)
                else:
                    review_status_badge.set_text(f"Статус: {status_val}")
                    if status_val.strip().upper() == 'ЄРДР':
                        review_status_badge.props('color="red"')
                    else:
                        review_status_badge.props('color="green"')
                    review_status_badge.set_visibility(True)

                if mil_unit_val == 'А7018':
                    mil_unit_badge.set_visibility(True)
                else:
                    mil_unit_badge.set_visibility(False)

                if has_multiple_events:
                    multiple_events_badge.set_visibility(True)
                else:
                    multiple_events_badge.set_visibility(False)
            def on_person_change(e):
                selected_id = e.value
                if selected_id and selected_id in state['current_search_results']:
                    person_data = state['current_search_results'][selected_id]
                    real_name = person_data['name']
                    name_gen_input.value = to_genitive_case(real_name)
                    rnokpp = person_data.get('rnokpp')

                    # 💡 ДОДАНО: Рахуємо скільки подій у цієї людини в поточних результатах пошуку
                    match_count = sum(
                        1 for p in state['current_search_results'].values()
                        if p.get('name') == real_name and p.get('rnokpp') == rnokpp
                    )
                    has_multiple = match_count > 1

                    name_gen_input.value = to_genitive_case(real_name)
                    update_badges(person_data.get('review_status', ''), person_data.get('mil_unit', ''), has_multiple)
                else:
                    update_badges('', '', False)

            with ui.row().classes('w-full items-center gap-4 mb-4'):
                person_select = ui.select(
                    options={},
                    label='Оберіть особу зі знайдених',
                    on_change=on_person_change
                ).classes('flex-1')
                person_select.visible = False

                name_gen_input = ui.input('ПІБ (Родовий відмінок)').classes('flex-1 text-blue-800 font-bold')
                name_gen_input.visible = False

                with ui.column().classes('gap-1 mt-2'):
                    review_status_badge = ui.badge('', color='green').classes('text-xs font-bold px-2 py-1 shadow-sm')
                    review_status_badge.set_visibility(False)

                    mil_unit_badge = ui.badge('БРЕЗ', color='orange').classes('text-xs font-bold px-2 py-1 shadow-sm')
                    mil_unit_badge.set_visibility(False)

                    multiple_events_badge = ui.badge('⚠️ Кілька епізодів СЗЧ!', color='purple').classes('text-xs font-bold px-2 py-1 shadow-sm')
                    multiple_events_badge.set_visibility(False)

            async def perform_search(e=None):
                query = search_input.value
                if not query or len(query) < 2:
                    ui.notify('Введіть мінімум 2 літери для пошуку', type='warning')
                    return

                search_btn.disable()
                try:
                    search_filter = PersonSearchFilter(query=query)
                    results = await run.io_bound(person_controller.search, ctx, search_filter)

                    state['current_search_results'].clear()
                    options = {}

                    for person in results:
                        des_date_val = getattr(person, 'desertion_date', 'Невідомо')
                        if not des_date_val:
                            des_date_val = 'Невідомо'

                        id_num = f"{person.rnokpp}_{person.name}_{des_date_val}"
                        title_val = getattr(person, 'title', '')
                        mil_unit_val = getattr(person, 'mil_unit', '')

                        state['current_search_results'][id_num] = {
                            'name': person.name,
                            'rnokpp': person.rnokpp,
                            'desertion_date': des_date_val,
                            'review_status': getattr(person, 'review_status', ''),
                            'title': title_val,
                            'mil_unit': mil_unit_val,
                            'id_number': id_num
                        }

                        unit_str = " [БРЕЗ]" if mil_unit_val == 'А7018' else ""
                        options[id_num] = f"{person.name}{unit_str} (РНОКПП: {person.rnokpp} СЗЧ: {des_date_val})"

                    person_select.options = options
                    person_select.visible = True
                    name_gen_input.visible = True

                    if options:
                        first_id = list(options.keys())[0]
                        person_select.value = first_id
                        ui.notify(f'Знайдено збігів: {len(options)}', type='info')
                    else:
                        ui.notify('За цим запитом нікого не знайдено', type='warning')
                        person_select.visible = False
                        update_badges('', '')

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
                name_gen_input.value = ''
                name_gen_input.visible = False
                update_badges('', '', False)

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
                title_val = selected_person.get('title', '')
                title_gen_val = to_genitive_title(title_val)
                mil_unit_val = selected_person.get('mil_unit', '')

                total_val = int(total_input.value or 0)
                fields = [notif, assign, result, act, expl, char, med, card, set_docs, move, other]
                calculated_sum = sum([int(f.value or 0) for f in fields])

                if calculated_sum != total_val:
                    ui.notify(f'Помилка! Загальна ({total_val}) != Сумі ({calculated_sum})', type='negative')
                    return

                if edit_idx is not None:
                    assigned_seq_num = buffer_data[edit_idx].get('seq_num', edit_idx + 1)
                else:
                    assigned_seq_num = state['next_seq_num']
                    state['next_seq_num'] += 1

                raw_data = {
                    'id_number': selected_id,
                    'seq_num': assigned_seq_num,
                    'name': name_val,
                    'name_gen': name_gen_input.value.strip(),
                    'title': title_val,
                    'title_gen': title_gen_val,
                    'rnokpp': selected_person.get('rnokpp', ''),
                    'desertion_date': selected_person.get('desertion_date', ''),
                    'review_status': selected_person.get('review_status', ''),
                    'mil_unit': mil_unit_val,
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
                mark_dirty()

            with ui.row().classes('w-full mt-4 gap-2'):
                add_btn = ui.button('Додати до пакету', on_click=on_add_click, icon='add').classes(
                    'flex-grow bg-blue-500 text-white')
                cancel_btn = ui.button('Скасувати', on_click=clear_inputs, icon='close').props('flat').classes(
                    'text-gray-500 bg-gray-200')
                cancel_btn.set_visibility(False)

        with ui.column().classes('col-span-12 md:col-span-4 w-full'):
            ui.label('Поточний пакет:').classes('text-xl font-bold')
            buffer_container = ui.column().classes('w-full gap-2 p-4 border rounded bg-gray-50 min-h-[400px] shadow-inner')

            def on_remove_click(idx):
                if 0 <= idx < len(state['buffer']):
                    state['buffer'].pop(idx)
                if state['edit_idx'] == idx:
                    clear_inputs()
                elif state['edit_idx'] is not None and state['edit_idx'] > idx:
                    state['edit_idx'] -= 1
                refresh_buffer_ui()
                mark_dirty()

            def on_edit_click(idx):
                state['edit_idx'] = idx
                doc = state['buffer'][idx]

                id_num = doc['id_number']
                search_input.value = doc['name']

                state['current_search_results'][id_num] = doc
                rnokpp_str = doc.get('rnokpp', 'Невідомо')
                des_date_str = doc.get('desertion_date', 'Невідомо')
                mil_unit_val = doc.get('mil_unit', '')

                unit_str = " [БРЕЗ]" if mil_unit_val == 'А7018' else ""
                person_select.options = {id_num: f"{doc['name']}{unit_str} (РНОКПП: {rnokpp_str} СЗЧ: {des_date_str})"}
                person_select.value = id_num
                person_select.visible = True
                name_gen_input.value = doc.get('name_gen', to_genitive_case(doc['name']))
                name_gen_input.visible = True

                update_badges(doc.get('review_status', ''), mil_unit_val)

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
                                    'w-full justify-between items-center bg-white p-2 border rounded shadow-sm hover:bg-gray-100 transition-colors'):
                                with ui.column().classes('gap-0 w-3/4'):
                                    seq = doc.get('seq_num', i + 1)
                                    ui.label(f"{seq}. {doc['name']} ({doc['total']} стор.)").classes(
                                        'font-medium text-sm truncate w-full')

                                    with ui.row().classes('gap-1 mt-1'):
                                        if doc.get('review_status') == 'ЄРДР':
                                            ui.badge('ЄРДР', color='red').classes('text-[10px] px-1 py-0 w-min')
                                        if doc.get('mil_unit') == 'А7018':
                                            ui.badge('БРЕЗ', color='orange').classes('text-[10px] px-1 py-0 w-min')

                                with ui.row().classes('gap-1'):
                                    edit_button = ui.button(icon='edit', color='blue',
                                                            on_click=lambda idx=i: on_edit_click(idx)).props(
                                        'flat dense size=sm')
                                    delete_button = ui.button(icon='delete', color='red',
                                                              on_click=lambda idx=i: on_remove_click(idx)).props(
                                        'flat dense size=sm')
                                    if state['status'] == DOC_STATUS_COMPLETED:
                                        edit_button.disable()
                                        delete_button.disable()

                if len(buffer_data) > 0 and state['status'] != DOC_STATUS_COMPLETED:
                    save_draft_btn.enable()
                    generate_docs_btn.enable()
                    complete_btn.enable()
                else:
                    if state['status'] != DOC_STATUS_COMPLETED:
                        save_draft_btn.disable()
                        generate_docs_btn.disable()
                        complete_btn.disable()

            def refresh_status_ui():
                current_status = state.get('status', DOC_STATUS_DRAFT)
                status_badge.set_text(current_status)

                if current_status == DOC_STATUS_COMPLETED:
                    status_badge.props('color="green"')
                    generate_docs_btn.disable()
                    complete_btn.disable()
                    save_draft_btn.disable()
                    generate_logs_btn.enable()
                else:
                    status_badge.props('color="grey"')
                    generate_logs_btn.disable()
                    if state['buffer']:
                        generate_docs_btn.enable()
                        complete_btn.enable()
                        save_draft_btn.enable()

            def load_draft(d_id: int):
                try:
                    draft = controller.get_support_doc_by_id(ctx, d_id)
                    if not draft:
                        ui.notify(f'Помилка: Чернетку №{d_id} не знайдено в базі!', type='negative')
                        return

                    if draft.get('city') in city.options:
                        city.value = draft['city']

                    state['support_date'] = draft.get('support_date', '')
                    supp_date_input.set_value(state['support_date'])

                    state['support_number'] = draft.get('support_number', '')
                    supp_number_input.set_value(state['support_number'])

                    state['buffer'] = draft.get('payload', [])
                    state['status'] = draft.get('status', DOC_STATUS_DRAFT)

                    if state['buffer']:
                        max_seq = max([doc.get('seq_num', i + 1) for i, doc in enumerate(state['buffer'])])
                        state['next_seq_num'] = max_seq + 1
                    else:
                        state['next_seq_num'] = 1

                    refresh_status_ui()
                    ui.notify(f'Чернетку №{d_id} успішно завантажено', type='positive')
                except Exception as e:
                    ui.notify(f'Помилка завантаження чернетки: {e}', type='negative')

            if draft_id is not None:
                load_draft(draft_id)

            refresh_buffer_ui()