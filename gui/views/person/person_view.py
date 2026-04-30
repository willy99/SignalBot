from nicegui import ui
from domain.person import Person
import asyncio
from gui.controllers.person_controller import PersonController
from gui.services.auth_manager import AuthManager
from gui.tools.ui_components import date_input, fix_date, confirm_delete_dialog
from dics.security_config import MODULE_PERSON, PERM_DELETE, PERM_EDIT
from datetime import datetime, timedelta

from utils.regular_expressions import *
from utils.utils import calculate_days_between, check_birthday_id_number


def search_select(options: list, label: str, person: Person, field: str):
    sel = ui.select(options=options, label=label, with_input=False)
    sel.bind_value(person, field).props('use-input fill-input hide-selected')
    return sel


def is_delete_allowed(person: Person) -> bool:
    ins_date_val = getattr(person, 'insert_date', getattr(person, 'ins_date', None))

    if not ins_date_val:
        return False

    try:
        if isinstance(ins_date_val, str):
            parsed_date = datetime.strptime(ins_date_val, '%d.%m.%Y').date()
        elif isinstance(ins_date_val, datetime):
            parsed_date = ins_date_val.date()
        else:
            parsed_date = ins_date_val

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        return parsed_date in (today, yesterday)
    except Exception:
        return False


# ==========================================
# 🪟 ВІКНА ДІАЛОГІВ
# ==========================================

def edit_person(person: Person, person_ctrl, auth_manager: AuthManager, on_close=None):
    ui_options = person_ctrl.get_column_options()
    can_edit = auth_manager.has_access(MODULE_PERSON, PERM_EDIT)
    can_delete = auth_manager.has_access(MODULE_PERSON, PERM_DELETE)
    req = {'Обов’язкове поле': lambda v: bool(v and str(v).strip())}

    def recalculate_days():
        days = calculate_days_between(person.enlistment_date, person.desertion_date)
        person.service_days = days

        if person.desertion_date:
            person.desertion_term = "більше 3 діб"
            ret_date = person.return_date or person.return_reserve_date

            if ret_date:
                try:
                    term_days = calculate_days_between(person.desertion_date, ret_date)

                    if term_days <= 3:
                        person.desertion_term = "до 3 діб"
                    else:
                        person.desertion_term = "більше 3 діб"
                except:
                    pass
        else:
            person.desertion_term = ""

        service_days_input.update()
        term_select.update()

    def auto_fill_tzk_region():
        if person.tzk:
            region = extract_desertion_region(person.tzk)
            if region:
                person.tzk_region = region
                tzk_region_select.update()

    def auto_fill_desertion_place_fields():
        des_place_val = des_place.value
        des_cond = cond_area.value
        if des_place_val == EDU_CENTER:
            person.review_status = DEFAULT_REVIEW_STATUS_FOR_EDU_CENTER
            person.desertion_type = DEFAULT_DESERTION_TYPE_FOR_EDU_CENTER
            person.cc_article = ARTICLE_407_ABANDONEMENT
            desertion_type.update()
            person.o_ass_num = EDU_CENTER
            person.o_ass_date = desert_inp.value
            person.kpp_num = EDU_CENTER
            person.kpp_date = desert_inp.value
        else:
            person.review_status = DEFAULT_REVIEW_STATUS
            person.desertion_type = extract_desertion_type(des_cond, des_place_val)
            person.cc_article = extract_cc_article(person.desertion_type)
            desertion_type.update()
            person.kpp_num = None
            person.kpp_date = None
            person.o_ass_num = None
            person.o_ass_date = None

    def auto_fill_titles():
        if person.title:
            short_title = extract_title_2(person.title)
            if short_title:
                person.title2 = short_title
                title2_select.update()

    async def run_bio_parser():
        if not person.bio:
            ui.notify('Поле біографії порожнє', type='warning')
            return

        person.name = extract_name(person.bio)
        person.rnokpp = extract_id_number(person.bio)
        person.title = extract_title(person.bio)
        person.title2 = extract_title_2(person.title)
        person.service_type = extract_service_type(person.bio, person.desertion_conditions)
        person.subunit = extract_military_subunit(person.bio, mapping=PATTERN_SUBUNIT_MAPPING)
        person.subunit2 = extract_military_subunit(person.bio, mapping=PATTERN_SUBUNIT2_MAPPING)
        person.birthday = extract_birthday(person.bio)

        person.phone = extract_phone(person.bio)
        person.tzk = extract_rtzk(person.bio)
        person.tzk_region = extract_region(person.tzk)
        person.enlistment_date = extract_conscription_date(person.bio)
        person.address = extract_address(person.bio)

        refresh_validation()
        ui.notify('Дані біографії розпарсено', type='positive')

    async def run_desertion_parser():
        text_to_parse = person.desertion_conditions
        if not text_to_parse:
            ui.notify('Опишіть обставини СЗЧ для парсингу', type='warning')
            return

        person.desertion_place = extract_desertion_place(person.desertion_conditions)
        auto_fill_desertion_place_fields()
        person.desertion_date = extract_desertion_date(person.desertion_conditions)
        person.desertion_type = extract_desertion_type(person.desertion_conditions, person.desertion_place)
        person.desertion_region = extract_desertion_region(person.desertion_conditions)
        person.cc_article = extract_cc_article(person.desertion_type)
        person.experience = extract_experience(person.service_days)

        refresh_validation()
        ui.notify('Дані СЗЧ розпарсено', type='positive')

    def validate_date_sequence(person: Person) -> bool:
        if not person.enlistment_date or not person.desertion_date:
            return True

        try:
            start = datetime.strptime(person.enlistment_date, '%d.%m.%Y')
            end = datetime.strptime(person.desertion_date, '%d.%m.%Y')
            return end >= start
        except (ValueError, TypeError):
            return True

    def validate_id_vs_birthday(person: Person) -> bool:
        if not person.rnokpp or not person.birthday or len(str(person.rnokpp)) < 5:
            return True

        try:
            if isinstance(person.birthday, str):
                bday_dt = datetime.strptime(person.birthday, '%d.%m.%Y')
            else:
                bday_dt = person.birthday

            return check_birthday_id_number(bday_dt, str(person.rnokpp))
        except Exception:
            return True

    def refresh_validation():
        recalculate_days()
        enlist_inp.validate()
        desert_inp.validate()
        rnokpp_inp.validate()
        birthday_inp.validate()

    date_logic_error = '⚠️ Дата СЗЧ не може бути раніше дати призову'
    date_rules = {date_logic_error: lambda _: validate_date_sequence(person)}
    id_mismatch_err = '⚠️ РНОКПП не збігається з датою народження!'

    async def handle_save(person, person_ctrl: PersonController, dialog, on_close=None, paint_color=None, btns=None):
        critical_inputs = [name_input]
        is_valid = all([i.validate() for i in critical_inputs])

        if not is_valid:
            ui.notify('❌ Форма заповнена некоректно. Перевірте всі вкладки (ТЦК, Основна, СЗЧ)!', type='negative')
            return

        if btns:
            for btn in btns:
                if btn: btn.disable()

        try:
            with ui.notification(message='Зберігаю дані...', spinner=True, timeout=0) as n:
                await asyncio.sleep(0.1)
                success = await auth_manager.execute(person_ctrl.save_person, auth_manager.get_current_context(), person, paint_color)

                if success:
                    n.message = 'Успішно збережено!'
                    n.type = 'positive'
                    n.spinner = False
                    n.timeout = 2
                    dialog.close()
                    if on_close:
                        if asyncio.iscoroutinefunction(on_close):
                            await on_close()
                        else:
                            on_close()
                else:
                    n.message = 'Помилка запису!'
                    n.type = 'negative'
                    n.spinner = False
        except Exception as e:
            ui.notify(f'Критична помилка: {e}', type='negative')
        finally:
            if btns:
                for btn in btns:
                    if btn: btn.enable()

    async def handle_delete(person, person_ctrl: PersonController, dialog, on_close=None):
        result = await confirm_delete_dialog('Ви дійсно бажаєте видалити цей запис?')
        if not result: return
        with ui.notification(message='Видаляю дані...', spinner=True, timeout=0) as n:
            await asyncio.sleep(0.1)
            success = await auth_manager.execute(person_ctrl.delete_record, auth_manager.get_current_context(), person)

            if success:
                n.message = 'Успішно видалено!'
                n.type = 'positive'
                n.spinner = False
                n.timeout = 2
                dialog.close()
                if on_close:
                    if asyncio.iscoroutinefunction(on_close):
                        await on_close()
                    else:
                        on_close()
            else:
                n.message = 'Помилка видалення!'
                n.type = 'negative'
                n.spinner = False

    # 🎨 ІНЖЕКЦІЯ CSS: Ховаємо текст на табах для екранів менше 640px (телефони)
    ui.html('''
        <style>
            @media (max-width: 639px) {
                .mobile-icon-tabs .q-tab__label { display: none !important; }
                .mobile-icon-tabs .q-tab { padding: 0 12px !important; min-height: 48px !important; }
                .mobile-icon-tabs .q-tab__icon { font-size: 24px !important; margin: 0 !important; }
            }
        </style>
    ''').classes('hidden')

    with ui.dialog().props('maximized') as dialog:
        # 🛡 ГОЛОВНИЙ КОНТЕЙНЕР: Суворо обмежуємо висоту до 100% екрану і забороняємо загальний скрол
        with ui.card().classes('w-full h-full max-w-none p-0 m-0 gap-0 flex flex-col bg-gray-50 overflow-hidden'):

            # 1️⃣ HEADER (shrink-0 не дає йому стискатися)
            with ui.row().classes('w-full justify-between items-center bg-blue-700 text-white p-3 sm:p-4 m-0 shrink-0 shadow-md'):
                with ui.row().classes('items-center gap-2 sm:gap-3 flex-nowrap overflow-hidden flex-grow'):
                    ui.icon('person', size='sm').classes('text-2xl sm:text-3xl shrink-0')
                    ui.label(f"{person.name or 'Новий запис'}").classes('text-lg sm:text-xl font-bold truncate')
                ui.button(icon='close', on_click=dialog.close).props('flat round text-white').classes('shrink-0')

            # 2️⃣ КНОПКИ (shrink-0)
            with ui.row().classes('w-full justify-center sm:justify-start items-center p-2 sm:p-4 bg-white border-b border-gray-300 shrink-0 gap-2 flex-wrap shadow-sm'):
                cancel_btn = ui.button('Скасувати', icon='close', on_click=dialog.close).props('outline color="gray"').classes('flex-grow sm:flex-grow-0 h-10 sm:h-12')

                if person_ctrl.auth_manager.has_access('person', 'write'):
                    if can_edit:
                        save_btn = ui.button('ЗБЕРЕГТИ', icon='save',
                                             on_click=lambda: handle_save(person, person_ctrl, dialog, on_close=on_close,
                                                                          btns=[save_btn, cancel_btn, del_btn if can_delete else None], paint_color=None)) \
                            .classes('flex-grow sm:flex-grow-0 bg-green-600 text-white h-10 sm:h-12 font-bold shadow-md hover:bg-green-700')

                    if can_delete:
                        del_btn = ui.button('ВИДАЛИТИ', icon='delete',
                                            on_click=lambda: handle_delete(person, person_ctrl, dialog, on_close=on_close)) \
                            .classes('flex-grow sm:flex-grow-0 bg-red-600 text-white h-10 sm:h-12 font-bold shadow-md hover:bg-red-700').props('color="red"')

                        if getattr(person, 'id', None) is None:
                            del_btn.disable()
                            del_btn.tooltip('Неможливо видалити запис, який ще не збережено в базі.')
                        elif not is_delete_allowed(person):
                            del_btn.disable()
                            del_btn.tooltip('Видалення можливе лише для записів, які були додані сьогодні або вчора.')

            # 3️⃣ ТАБИ (shrink-0)
            with ui.tabs().classes('w-full text-black bg-white border-b border-gray-200 shrink-0 mobile-icon-tabs').props('dense outside-arrows mobile-arrows') as tabs:
                main_tab = ui.tab('Основна', icon='contact_mail')
                tzk_tab = ui.tab('ТЦК', icon='account_balance')
                des_tab = ui.tab('СЗЧ', icon='directions_run')
                bio_tab = ui.tab('Біографія', icon='history_edu')
                erdr_tab = ui.tab('Оформлення', icon='gavel')

            # 4️⃣ ПАНЕЛІ ТАБІВ (Магія: забирають РІВНО залишок висоти екрану)
            with ui.tab_panels(tabs, value=main_tab).classes('w-full p-0 m-0 bg-transparent').style('flex: 1 1 0px; min-height: 0;'):

                # ==========================================
                # ПАНЕЛЬ 1: Основна інформація
                # ==========================================
                with ui.tab_panel(main_tab).classes('p-0 m-0 w-full h-full'):
                    # Цей div створює внутрішній скрол ТІЛЬКИ для цієї вкладки!
                    with ui.element('div').classes('w-full h-full overflow-y-auto overflow-x-hidden p-2 sm:p-6'):
                        with ui.card().classes('w-full max-w-5xl mx-auto p-4 sm:p-6 shadow-sm border border-gray-200 mb-8'):

                            # Використовуємо ЄДИНУ сітку на 12 колонок для всієї форми.
                            # items-start гарантує, що якщо вилізе текст помилки (валідація), сусідні поля не перекосить.
                            with ui.grid(columns=12).classes('w-full gap-4 items-start'):

                                # --- РЯДОК 1 НА ПК (В/Ч, ПІБ, Дата нар., РНОКПП) = 2 + 5 + 2 + 3 = 12 колонок ---
                                mil_unit_select = search_select(MIL_UNITS, COLUMN_MIL_UNIT, person, 'mil_unit').classes('col-span-12 sm:col-span-2')
                                if person.id is not None:
                                    mil_unit_select.props('disable')
                                else:
                                    if person.mil_unit is None:
                                        mil_unit_select.value = MIL_UNITS[0]

                                name_input = ui.input(COLUMN_NAME, validation=req).bind_value(person, 'name').classes('col-span-12 sm:col-span-5')

                                birthday_inp = date_input(
                                    COLUMN_BIRTHDAY, person, 'birthday',
                                    blur_handler=lambda e: [fix_date(e), refresh_validation()]
                                ).classes('col-span-12 sm:col-span-2')
                                birthday_inp.validation.update({
                                    id_mismatch_err: lambda _: validate_id_vs_birthday(person)
                                })

                                rnokpp_inp = ui.input(COLUMN_ID_NUMBER, placeholder='xxxxxxxxxx', validation={
                                    'Обов’язкове поле': lambda v: bool(v),
                                    'Формат має бути 10 цифр': lambda v: len(str(v)) == 10 if v else True,
                                    id_mismatch_err: lambda _: validate_id_vs_birthday(person)
                                }).bind_value(person, 'rnokpp').classes('col-span-12 sm:col-span-3')
                                rnokpp_inp.on('blur', refresh_validation)

                                # --- РЯДОК 2 НА ПК (Звання, Кор. Звання, Підр.1, Підр.2) = 4 + 2 + 3 + 3 = 12 колонок ---
                                title_select = search_select(ui_options.get(COLUMN_TITLE, []), COLUMN_TITLE, person, 'title') \
                                    .classes('col-span-12 sm:col-span-4').props('rules="[val => !!val || \'Обов’язково\']"')
                                title_select.on_value_change(auto_fill_titles)

                                title2_select = search_select(ui_options.get(COLUMN_TITLE_2, []), COLUMN_TITLE_2, person, 'title2').classes('col-span-12 sm:col-span-2')

                                subunit = search_select(ui_options.get(COLUMN_SUBUNIT, []), COLUMN_SUBUNIT, person, 'subunit') \
                                    .classes('col-span-12 sm:col-span-3').props('rules="[val => !!val || \'Обов’язково\']"')

                                subunit2 = search_select(ui_options.get(COLUMN_SUBUNIT2, []), COLUMN_SUBUNIT2, person, 'subunit2').classes('col-span-12 sm:col-span-3')

                                # --- РЯДОК 3 НА ПК (Адреса, Телефон) = 8 + 4 = 12 колонок ---
                                address_input = ui.input(COLUMN_ADDRESS, validation=req).bind_value(person, 'address').classes('col-span-12 sm:col-span-8')
                                phone_input = ui.input(COLUMN_PHONE, placeholder='0xxxxxxxxx', validation={
                                    'Формат має бути 0xxxxxxxxx': lambda v: bool(re.match(VALID_PATTERN_PHONE, v.strip())) if v else True
                                }).bind_value(person, 'phone').classes('col-span-12 sm:col-span-4')
                # ==========================================
                # ПАНЕЛЬ 2: ТЦК
                # ==========================================
                with ui.tab_panel(tzk_tab).classes('p-0 m-0 w-full h-full'):
                    with ui.element('div').classes('w-full h-full overflow-y-auto overflow-x-hidden p-2 sm:p-6'):
                        with ui.card().classes('w-full max-w-5xl mx-auto p-4 sm:p-6 shadow-sm border border-gray-200 mb-8'):
                            # Використовуємо ui.grid на 12 колонок для всієї панелі
                            with ui.grid(columns=12).classes('w-full gap-4 items-start'):
                                # ТЦК (5 колонок)
                                tzk_input = ui.input(COLUMN_TZK, validation=req).bind_value(person, 'tzk').classes('col-span-12 sm:col-span-5')
                                tzk_input.on('blur', auto_fill_tzk_region)

                                # Регіон ТЦК (3 колонки)
                                tzk_region_select = search_select(ui_options.get(COLUMN_TZK_REGION, []), COLUMN_TZK_REGION, person, 'tzk_region') \
                                    .classes('col-span-12 sm:col-span-3').props('rules="[val => !!val || \'Виберіть регіон\']"')

                                # Дата призову (2 колонки)
                                enlist_inp = date_input(COLUMN_ENLISTMENT_DATE, person, 'enlistment_date', blur_handler=lambda e: [fix_date(e), refresh_validation()]) \
                                    .classes('col-span-12 sm:col-span-2')
                                enlist_inp.props(f'validation-rules="{date_rules}"')
                                enlist_inp.validation = date_rules
                                enlist_inp.validation.update(req)

                                # Дні служби (2 колонки)
                                service_days_input = ui.input(COLUMN_SERVICE_DAYS, validation={
                                    'Нелогічна кількість': lambda v: 0 <= (int(v) if str(v).isdigit() else 0) <= 6000
                                }).bind_value(person, 'service_days').classes('col-span-12 sm:col-span-2')
                # ==========================================
                # ПАНЕЛЬ 3: СЗЧ
                # ==========================================
                with ui.tab_panel(des_tab).classes('p-0 m-0 w-full h-full'):
                    with ui.element('div').classes('w-full h-full overflow-y-auto overflow-x-hidden p-2 sm:p-6'):
                        with ui.card().classes('w-full max-w-5xl mx-auto p-4 sm:p-6 shadow-sm border border-gray-200 mb-8'):
                            with ui.grid(columns=12).classes('w-full gap-4 items-start'):
                                # --- РЯДОК 1: Звідки, Тип, Область (4 + 4 + 4 = 12) ---
                                des_place = search_select(ui_options.get(COLUMN_DESERTION_PLACE, []), COLUMN_DESERTION_PLACE, person, 'desertion_place').classes(
                                    'col-span-12 sm:col-span-4')
                                des_place.on('blur', auto_fill_desertion_place_fields)

                                desertion_type = search_select(ui_options.get(COLUMN_DESERTION_TYPE, []), COLUMN_DESERTION_TYPE, person, 'desertion_type').classes(
                                    'col-span-12 sm:col-span-4')

                                search_select(ui_options.get(COLUMN_DESERTION_REGION, []), COLUMN_DESERTION_REGION, person, 'desertion_region').classes('col-span-12 sm:col-span-4')

                                # --- РЯДОК 2: Дата, Термін (4 + 8 = 12) ---
                                desert_inp = date_input(COLUMN_DESERTION_DATE, person, 'desertion_date',
                                                        blur_handler=lambda e: [fix_date(e), refresh_validation()]).classes('col-span-12 sm:col-span-4')
                                desert_inp.validation = date_rules

                                term_select = ui.select(
                                    options=["до 3 діб", "більше 3 діб"],
                                    label=COLUMN_DESERTION_TERM
                                ).bind_value(person, 'desertion_term').classes('col-span-12 sm:col-span-8')

                                # --- РЯДОК 3: Виконавець (12) ---
                                ui.input(COLUMN_EXECUTOR).bind_value(person, 'executor').classes('col-span-12')

                                # --- РЯДОК 4: Дати повернення (6 + 6 = 12) ---
                                date_input(COLUMN_RETURN_DATE, person, 'return_date',
                                           blur_handler=lambda e: [fix_date(e), refresh_validation()]).classes('col-span-12 sm:col-span-6')
                                date_input(COLUMN_RETURN_TO_RESERVE_DATE, person, 'return_reserve_date',
                                           blur_handler=lambda e: [fix_date(e), refresh_validation()]).classes('col-span-12 sm:col-span-6')

                                # --- РЯДОК 5: Обставини СЗЧ (12) ---
                                with ui.textarea(COLUMN_DESERT_CONDITIONS).bind_value(person, 'desertion_conditions').classes('col-span-12') as cond_area:
                                    with cond_area.add_slot('append'):
                                        ui.button(icon='psychology', on_click=run_desertion_parser).props('flat round color=orange')
                # ==========================================
                # ПАНЕЛЬ 4: Біографія
                # ==========================================
                with ui.tab_panel(bio_tab).classes('p-0 m-0 w-full h-full'):
                    with ui.element('div').classes('w-full h-full overflow-y-auto overflow-x-hidden p-2 sm:p-6'):
                        with ui.card().classes('w-full max-w-5xl mx-auto p-4 sm:p-6 shadow-sm border border-gray-200 mb-8'):
                            with ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full min-h-[400px]') as bio_area:
                                with bio_area.add_slot('append'):
                                    ui.button(icon='auto_fix_high', on_click=run_bio_parser).props('flat round')

                # ==========================================
                # ПАНЕЛЬ 5: ЕРДР, КПП
                # ==========================================
                with ui.tab_panel(erdr_tab).classes('p-0 m-0 w-full h-full'):
                    with ui.element('div').classes('w-full h-full overflow-y-auto overflow-x-hidden p-2 sm:p-6'):
                        with ui.row().classes('w-full max-w-6xl mx-auto gap-4 sm:gap-6 flex-wrap items-start mb-8'):
                            # --- ЛІВА КОЛОНКА (Накази та статуси) ---
                            with ui.card().classes('w-full lg:w-[58%] p-4 sm:p-6 shadow-sm border border-gray-200 gap-0'):
                                ui.label('Документальне оформлення').classes('text-lg sm:text-xl font-bold text-gray-800 mb-4 border-b pb-2 w-full')

                                # Використовуємо сітку 12 колонок для ідеального вирівнювання
                                with ui.grid(columns=12).classes('w-full gap-4 items-start'):
                                    # Статус (8) + Стаття (4)
                                    review_status = search_select(ui_options.get(COLUMN_REVIEW_STATUS, []), COLUMN_REVIEW_STATUS, person, 'review_status').classes(
                                        'col-span-12 sm:col-span-8')
                                    ui.input(COLUMN_CC_ARTICLE).bind_value(person, 'cc_article').classes('col-span-12 sm:col-span-4')

                                    # Наказ СЗЧ: Номер (8) + Дата (4)
                                    ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(person, 'o_ass_num').classes('col-span-12 sm:col-span-8')
                                    date_input(COLUMN_ORDER_ASSIGNMENT_DATE, person, 'o_ass_date', blur_handler=fix_date).classes('col-span-12 sm:col-span-4')

                                    # Наказ Повернення: Номер (8) + Дата (4)
                                    ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(person, 'o_res_num').classes('col-span-12 sm:col-span-8')
                                    date_input(COLUMN_ORDER_RESULT_DATE, person, 'o_res_date', blur_handler=fix_date).classes('col-span-12 sm:col-span-4')

                                    # КПП: Номер (8) + Дата (4)
                                    kpp_num = ui.input(COLUMN_KPP_NUMBER).bind_value(person, 'kpp_num').classes('col-span-12 sm:col-span-8')
                                    kpp_date = date_input(COLUMN_KPP_DATE, person, 'kpp_date', blur_handler=fix_date).classes('col-span-12 sm:col-span-4')

                                    # ДБР: Номер (8) + Дата (4)
                                    ui.input(COLUMN_DBR_NUMBER).bind_value(person, 'dbr_num').classes('col-span-12 sm:col-span-8')
                                    date_input(COLUMN_DBR_DATE, person, 'dbr_date', blur_handler=fix_date).classes('col-span-12 sm:col-span-4')

                            # --- ПРАВА КОЛОНКА (Дані ЄРДР) - Залишається як є ---
                            with ui.card().classes('w-full lg:w-[38%] p-4 sm:p-6 shadow-sm border border-gray-200 gap-0 flex-grow'):
                                with ui.row().classes('items-center gap-2 mb-4 w-full border-b pb-2 flex-wrap'):
                                    ui.icon('policy', size='sm', color='blue-600')
                                    ui.label('Дані ЄРДР').classes('text-lg sm:text-xl font-bold text-gray-800')

                                date_input(COLUMN_ERDR_DATE, person, 'erdr_date', blur_handler=fix_date).classes('w-full mb-4').props('filled')
                                ui.textarea(COLUMN_ERDR_NOTATION).bind_value(person, 'erdr_notation').classes('w-full').props('filled autogrow')

                                ui.textarea(COLUMN_NOTATION).bind_value(person, 'notation').classes('w-full min-h-[200px] sm:min-h-[300px] mt-4')
    dialog.open()
    return dialog