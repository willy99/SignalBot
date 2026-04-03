from nicegui import ui, run
from dics.deserter_xls_dic import *
from domain.person import Person
import asyncio
from gui.controllers.person_controller import PersonController
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
import re
from gui.tools.ui_components import date_input, fix_date, confirm_delete_dialog
from dics.security_config import MODULE_PERSON, PERM_DELETE, PERM_EDIT
from datetime import datetime, timedelta

from utils.utils import calculate_days_between, check_birthday_id_number


def search_select(options: list, label: str, person: Person, field: str):
    """Створює випадаючий список із можливістю пошуку"""
    sel = ui.select(options=options, label=label, with_input=False)
    sel.bind_value(person, field).props('use-input fill-input hide-selected')
    return sel


def is_delete_allowed(person: Person) -> bool:
    """Перевіряє, чи запис було додано сьогодні або вчора."""
    ins_date_val = getattr(person, 'insert_date', getattr(person, 'ins_date', None))

    if not ins_date_val:
        return False

    try:
        if isinstance(ins_date_val, str):
            parsed_date = datetime.strptime(ins_date_val, '%d.%m.%Y').date()
        elif isinstance(ins_date_val, datetime):
            parsed_date = ins_date_val.date()
        else:
            parsed_date = ins_date_val  # Якщо це вже об'єкт datetime.date

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
        """Оновлює кількість днів та валідує результат"""
        days = calculate_days_between(person.enlistment_date, person.desertion_date)
        person.service_days = days

        # Оновлюємо UI (якщо потрібно примусово, хоча bind_value має підхопити)
        service_days_input.update()

    def validate_date_sequence(person: Person) -> bool:
        """Перевіряє, чи дата СЗЧ не раніше дати призову"""
        if not person.enlistment_date or not person.desertion_date:
            return True  # Якщо однієї з дат немає, валідація проходить

        try:
            # Парсимо дати (використовуємо вашу логіку парсингу)
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
        recalculate_days()  # Ваша попередня функція розрахунку днів
        enlist_inp.validate()
        desert_inp.validate()
        rnokpp_inp.validate()
        birthday_inp.validate()


    date_logic_error = '⚠️ Дата СЗЧ не може бути раніше дати призову'
    date_rules = {date_logic_error: lambda _: validate_date_sequence(person)}
    id_mismatch_err = '⚠️ РНОКПП не збігається з датою народження!'

    async def handle_save(person, person_ctrl: PersonController, dialog, on_close=None, paint_color=None, btns=None):
        critical_inputs = [
            rnokpp_inp, birthday_inp, tzk_input, name_input
        ]
        is_valid = all([i.validate() for i in critical_inputs])

        if not is_valid:
            ui.notify('❌ Форма заповнена некоректно. Перевірте всі вкладки (ТЦК, Основна, СЗЧ)!', type='negative')
            return

        if btns:
            for btn in btns:
                if btn: btn.disable()

        try:
            with ui.notification(message='Зберігаю дані...', spinner=True, timeout=0) as n:
                await asyncio.sleep(0.1)  # Даємо UI відмалювати спінер

                success = await auth_manager.execute(person_ctrl.save_person, auth_manager.get_current_context(), person, paint_color)

                if success:
                    n.message = 'Успішно збережено!'
                    n.type = 'positive'
                    n.spinner = False
                    n.timeout = 2

                    # Закриваємо діалог миттєво після успіху
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
            await asyncio.sleep(0.1)  # Даємо UI відмалювати спінер

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

    with ui.dialog().props('maximized') as dialog, ui.card().classes(
            'w-full h-full max-w-none p-0 gap-0 flex flex-col bg-gray-50'):
        with ui.row().classes(
                'w-full justify-between items-center bg-blue-700 text-white p-4 m-0 shrink-0 shadow-md z-10'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('person', size='md')
                ui.label(f"Картка: {person.name}").classes('text-2xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round text-white')

        with ui.column().classes('w-full flex-grow overflow-hidden p-0 gap-0'):
            with ui.tabs().classes('w-full text-black bg-white border-b border-gray-200 shrink-0') as tabs:
                main_tab = ui.tab('Основна інформація', icon='contact_mail')
                tzk_tab = ui.tab('ТЦК', icon='account_balance')
                des_tab = ui.tab('СЗЧ та повернення', icon='directions_run')
                bio_tab = ui.tab('Біографія', icon='history_edu')
                erdr_tab = ui.tab('Стан розслідування', icon='gavel')

            with ui.tab_panels(tabs, value=main_tab).classes('w-full flex-grow overflow-y-auto p-6 bg-transparent'):
                # ПАНЕЛЬ 1: Основна інформація
                with ui.tab_panel(main_tab):
                    with ui.card().classes('w-full max-w-5xl mx-auto p-6 shadow-sm border border-gray-200'):
                        with ui.row().classes('w-full gap-6'):
                            mil_unit_select = search_select(MIL_UNITS, COLUMN_MIL_UNIT, person, 'mil_unit').classes('w-32')
                            if person.id is not None:
                                mil_unit_select.props('disable')
                                mil_unit_select.tooltip('Зміна в/ч для існуючого запису заборонена. Видаліть та створіть новий, якщо помилилися.')
                            else:
                                mil_unit_select.value = MIL_UNITS[0]
                            name_input = ui.input(COLUMN_NAME, validation=req).bind_value(person, 'name').classes('flex-grow')
                            rnokpp_inp = ui.input(COLUMN_ID_NUMBER, placeholder='xxxxxxxxxx', validation={
                                'Обов’язкове поле': lambda v: bool(v),
                                'Формат має бути 10 цифр': lambda v: len(str(v)) == 10 if v else True,
                                id_mismatch_err: lambda _: validate_id_vs_birthday(person)
                            }).bind_value(person, 'rnokpp').classes('w-48')

                            rnokpp_inp.on('blur', refresh_validation)

                        with ui.row().classes('w-full gap-6 mt-4'):
                            title = search_select(ui_options.get(COLUMN_TITLE, []), COLUMN_TITLE, person, 'title').classes('flex-grow').props('rules="[val => !!val || \'Обов’язково\']"')
                            search_select(ui_options.get(COLUMN_TITLE_2, []), COLUMN_TITLE_2, person, 'title2').classes('flex-grow')
                            subunit = search_select(ui_options.get(COLUMN_SUBUNIT, []), COLUMN_SUBUNIT, person,'subunit').classes('w-48').props('rules="[val => !!val || \'Обов’язково\']"')
                            search_select(ui_options.get(COLUMN_SUBUNIT2, []), COLUMN_SUBUNIT2, person,'subunit2').classes('w-48')

                        with ui.row().classes('w-full gap-6 mt-4'):
                            address_input = ui.input(COLUMN_ADDRESS, validation=req).bind_value(person, 'address').classes('flex-grow')
                            ui.input(COLUMN_PHONE, placeholder='0xxxxxxxxx', validation={
                                'Формат має бути 0xxxxxxxxx': lambda v: bool(re.match(VALID_PATTERN_PHONE, v.strip())) if v else True
                            }).bind_value(person, 'phone').classes('w-48')

                        with ui.row().classes('w-full mt-4'):
                            birthday_inp = date_input(
                                COLUMN_BIRTHDAY,
                                person,
                                'birthday',
                                # Тут обов'язково fix_date(e) та оновлення валідації
                                blur_handler=lambda e: [fix_date(e), refresh_validation()]
                            ).classes('w-1/3')
                            birthday_inp.validation.update({
                                id_mismatch_err: lambda _: validate_id_vs_birthday(person)
                            })

                # ПАНЕЛЬ 2: ТЦК
                with ui.tab_panel(tzk_tab):
                    with ui.card().classes('w-full max-w-5xl mx-auto p-6 shadow-sm border border-gray-200'):
                        with ui.row().classes('w-full gap-6'):
                            tzk_input = ui.input(COLUMN_TZK, validation=req).bind_value(person, 'tzk').classes('flex-grow')
                            enlist_inp = date_input(COLUMN_ENLISTMENT_DATE, person, 'enlistment_date', blur_handler=lambda e: [fix_date(e), refresh_validation()]).classes('w-1/3')
                            enlist_inp.props(f'validation-rules="{date_rules}"')
                            enlist_inp.validation = date_rules
                            enlist_inp.validation.update(req)

                            service_days_input = ui.input(COLUMN_SERVICE_DAYS, validation={
                                '⚠️ Нелогічна кількість днів служби. Перевірте дати.':
                                    lambda v: 0 <= (int(v) if str(v).isdigit() else 0) <= 4000
                            }).bind_value(person, 'service_days').classes('flex-grow')

                        with ui.row().classes('w-full gap-6 mt-4'):
                            search_select(ui_options.get(COLUMN_TZK_REGION, []), COLUMN_TZK_REGION, person,'tzk_region').classes('w-1/3').props('rules="[val => !!val || \'Виберіть регіон\']"')

                # ПАНЕЛЬ 3: СЗЧ
                with ui.tab_panel(des_tab):
                    with ui.card().classes('w-full max-w-5xl mx-auto p-6 shadow-sm border border-gray-200'):
                        with ui.row().classes('w-full gap-6'):
                            search_select(ui_options.get(COLUMN_DESERTION_PLACE, []), COLUMN_DESERTION_PLACE, person,'desertion_place').classes('w-48')
                            search_select(ui_options.get(COLUMN_DESERTION_TYPE, []), COLUMN_DESERTION_TYPE, person,'desertion_type').classes('w-48')
                            search_select(ui_options.get(COLUMN_DESERTION_REGION, []), COLUMN_DESERTION_REGION, person,'desertion_region').classes('flex-grow')

                        with ui.row().classes('w-full gap-6 mt-4'):
                            desert_inp = date_input(COLUMN_DESERTION_DATE, person, 'desertion_date', blur_handler=lambda e: [fix_date(e), refresh_validation()]).classes('w-1/3')
                            desert_inp.validation = date_rules
                            ui.input(COLUMN_DESERTION_TERM).bind_value(person, 'desertion_term').classes('flex-grow')

                        with ui.row().classes('w-full mt-4'):
                            ui.input(COLUMN_EXECUTOR).bind_value(person, 'executor').classes('flex-grow')

                        with ui.row().classes('w-full gap-6 mt-4'):
                            date_input(COLUMN_RETURN_DATE, person, 'return_date', blur_handler=fix_date).classes('w-1/3')
                            date_input(COLUMN_RETURN_TO_RESERVE_DATE, person, 'return_reserve_date',blur_handler=fix_date).classes('w-1/3')

                        with ui.row().classes('w-full mt-4'):
                            ui.textarea(COLUMN_DESERT_CONDITIONS).bind_value(person, 'desertion_conditions').classes('w-full')

                # ПАНЕЛЬ 4: Біографія
                with ui.tab_panel(bio_tab):
                    with ui.card().classes('w-full max-w-5xl mx-auto p-6 shadow-sm border border-gray-200'):
                        ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full min-h-[300px]')

                # ПАНЕЛЬ 5: ЕРДР, КПП (ОНОВЛЕНО З ДВОМА КОЛОНКАМИ)
                with ui.tab_panel(erdr_tab):
                    with ui.grid(columns=12).classes('w-full max-w-6xl mx-auto gap-8'):
                        # Ліва колонка (Накази та статуси)
                        with ui.card().classes('col-span-12 md:col-span-7 p-6 shadow-sm border border-gray-200 gap-0'):
                            ui.label('Документальне оформлення').classes('text-xl font-bold text-gray-800 mb-4 border-b pb-2 w-full')

                            with ui.row().classes('w-full gap-4'):
                                search_select(ui_options.get(COLUMN_REVIEW_STATUS, []), COLUMN_REVIEW_STATUS, person,'review_status').classes('flex-grow')
                                ui.input(COLUMN_CC_ARTICLE).bind_value(person, 'cc_article').classes('w-1/3')

                            with ui.row().classes('w-full gap-4 mt-4'):
                                ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(person, 'o_ass_num').classes('flex-grow')
                                date_input(COLUMN_ORDER_ASSIGNMENT_DATE, person, 'o_ass_date',blur_handler=fix_date).classes('w-1/3')

                            with ui.row().classes('w-full gap-4 mt-4'):
                                ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(person, 'o_res_num').classes('flex-grow')
                                date_input(COLUMN_ORDER_RESULT_DATE, person, 'o_res_date',blur_handler=fix_date).classes('w-1/3')

                            with ui.row().classes('w-full gap-4 mt-4'):
                                ui.input(COLUMN_KPP_NUMBER).bind_value(person, 'kpp_num').classes('flex-grow')
                                date_input(COLUMN_KPP_DATE, person, 'kpp_date', blur_handler=fix_date).classes('w-1/3')

                            with ui.row().classes('w-full gap-4 mt-4'):
                                ui.input(COLUMN_DBR_NUMBER).bind_value(person, 'dbr_num').classes('flex-grow')
                                date_input(COLUMN_DBR_DATE, person, 'dbr_date', blur_handler=fix_date).classes('w-1/3')

                        # Права колонка (ЄРДР Секція)
                        with ui.card().classes('col-span-12 md:col-span-5 p-6 shadow-sm border border-gray-200 gap-0'):
                            with ui.row().classes('items-center gap-2 mb-4 w-full border-b pb-2'):
                                ui.icon('policy', size='sm', color='blue-600')
                                ui.label('Дані ЄРДР').classes('text-xl font-bold text-gray-800')

                            date_input(COLUMN_ERDR_DATE, person, 'erdr_date', blur_handler=fix_date).classes('w-full mb-4').props('filled')
                            ui.textarea(COLUMN_ERDR_NOTATION).bind_value(person, 'erdr_notation').classes('w-full').props('filled autogrow')

                            ui.textarea(COLUMN_NOTATION).bind_value(person, 'notation').classes('w-full min-h-[300px]')

        # ФУТЕР З КНОПКАМИ ДІЇ (Фіксований внизу екрану)
        with ui.row().classes('w-full justify-end items-center p-4 bg-white border-t border-gray-300 shrink-0 gap-4 shadow-inner z-10'):
            cancel_btn = ui.button('Скасувати', icon='close', on_click=dialog.close).props('outline color="gray"').classes('px-6 h-12')
            if person_ctrl.auth_manager.has_access('person', 'write'):
                if can_edit:
                    save_btn = ui.button('ЗБЕРЕГТИ ДАНІ', icon='save',
                              on_click=lambda: handle_save(person, person_ctrl, dialog, on_close=on_close, btns=[save_btn, cancel_btn, del_btn if can_delete else None], paint_color=None)) \
                        .classes('bg-green-600 text-white px-8 h-12 text-lg font-bold shadow-md hover:bg-green-700 transition-colors')

                if can_delete:
                    del_btn = ui.button('ВИДАЛИТИ', icon='delete',
                                        on_click=lambda: handle_delete(person, person_ctrl, dialog, on_close=on_close)) \
                        .classes('bg-red-600 text-white px-8 h-12 text-lg font-bold shadow-md hover:bg-red-700 transition-colors').props('color="red"')

                    if getattr(person, 'id', None) is None:
                        del_btn.disable()
                        del_btn.tooltip('Неможливо видалити запис, який ще не збережено в базі.')
                    elif not is_delete_allowed(person):
                        del_btn.disable()
                        del_btn.tooltip('Видалення можливе лише для записів, які були додані сьогодні або вчора.')

    dialog.open()
    return dialog


