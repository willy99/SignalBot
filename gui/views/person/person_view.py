from nicegui import ui, run
from dics.deserter_xls_dic import *
from domain.person import Person
import asyncio
from config import UI_DATE_FORMAT, EXCEL_BLUE_COLOR
from datetime import datetime
from gui.services.request_context import RequestContext

def fix_date(e):
    val = e.sender.value
    if not val:
        return
    parts = val.split('.')
    # Якщо введено "ДД.ММ" (наприклад, 12.06)
    if len(parts) == 2:
        current_year = datetime.now().year
        # Оновлюємо значення в полі
        e.sender.value = f"{val}.{current_year}"


# ==========================================
# 🛠 UI ХЕЛПЕРИ (Компоненти)
# ==========================================

def date_input(label: str, person: Person, field: str, blur_handler=None):
    """Створює поле для вводу дати зі спливаючим календарем (іконкою)"""
    inp = ui.input(label=label)
    inp.bind_value(person, field)

    if blur_handler:
        inp.on('blur', blur_handler)

    with inp.add_slot('append'):
        ui.icon('edit_calendar').classes('cursor-pointer')
        with ui.menu():
            ui.date().bind_value(person, field).props(f'mask="{UI_DATE_FORMAT}"')

    return inp


def search_select(options: list, label: str, person: Person, field: str):
    """Створює випадаючий список із можливістю пошуку"""
    # dict.get(KEY, []) захищає від помилок, якщо ключа раптом немає в ui_options
    sel = ui.select(options=options, label=label, with_input=False)
    sel.bind_value(person, field).props('use-input fill-input hide-selected')
    return sel


# ==========================================
# 🪟 ВІКНА ДІАЛОГІВ
# ==========================================

def edit_person(person: Person, person_ctrl, ctx: RequestContext, on_close=None):
    ui_options = person_ctrl.get_column_options()

    with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-none p-0 gap-0'):
        with ui.row().classes('w-full justify-between items-center bg-blue-600 text-white p-4 m-0 rounded-t-lg'):
            ui.label(f"Картка: {person.name}").classes('text-xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round text-white')

        with ui.column().classes('w-full p-4'):
            with ui.tabs().classes('w-full text-black') as tabs:
                main_tab = ui.tab('Основна інформація', icon='contact_mail')
                tzk_tab = ui.tab('ТЦК', icon='account_balance')
                des_tab = ui.tab('СЗЧ та повернення', icon='directions_run')
                bio_tab = ui.tab('Біографія', icon='history_edu')
                erdr_tab = ui.tab('Стан розслідування', icon='gavel')

            with ui.tab_panels(tabs, value=main_tab).classes('w-full'):
                # ПАНЕЛЬ 1: Основна інформація
                with ui.tab_panel(main_tab):
                    with ui.row().classes('w-full gap-4'):
                        ui.input(COLUMN_NAME).bind_value(person, 'name').classes('flex-grow')
                        ui.input(COLUMN_ID_NUMBER).bind_value(person, 'rnokpp').classes('w-40')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        search_select(ui_options.get(COLUMN_TITLE, []), COLUMN_TITLE, person, 'title').classes('flex-grow')
                        search_select(ui_options.get(COLUMN_TITLE_2, []), COLUMN_TITLE_2, person, 'title2').classes(
                            'flex-grow')
                        search_select(ui_options.get(COLUMN_SUBUNIT, []), COLUMN_SUBUNIT, person, 'subunit').classes('w-40')
                        search_select(ui_options.get(COLUMN_SUBUNIT2, []), COLUMN_SUBUNIT2, person, 'subunit2').classes(
                            'w-40')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.input(COLUMN_ADDRESS).bind_value(person, 'address').classes('flex-grow')
                        ui.input(COLUMN_PHONE).bind_value(person, 'phone').classes('w-40')

                    with ui.row().classes('w-full mt-2'):
                        date_input(COLUMN_BIRTHDAY, person, 'birthday', blur_handler=fix_date).classes('w-1/3')

                # ПАНЕЛЬ 2: ТЦК
                with ui.tab_panel(tzk_tab):
                    with ui.row().classes('w-full gap-4'):
                        ui.input(COLUMN_TZK).bind_value(person, 'tzk').classes('flex-grow')
                        date_input(COLUMN_ENLISTMENT_DATE, person, 'enlistment_date', blur_handler=fix_date).classes('w-1/3')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        search_select(ui_options.get(COLUMN_TZK_REGION, []), COLUMN_TZK_REGION, person,
                                      'tzk_region').classes('w-1/3')

                # ПАНЕЛЬ 3: СЗЧ
                with ui.tab_panel(des_tab):
                    with ui.row().classes('w-full gap-4'):
                        search_select(ui_options.get(COLUMN_DESERTION_PLACE, []), COLUMN_DESERTION_PLACE, person,
                                      'desertion_place').classes('w-40')
                        search_select(ui_options.get(COLUMN_DESERTION_TYPE, []), COLUMN_DESERTION_TYPE, person,
                                      'desertion_type').classes('w-40')
                        search_select(ui_options.get(COLUMN_DESERTION_REGION, []), COLUMN_DESERTION_REGION, person,
                                      'desertion_region').classes('flex-grow')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        date_input(COLUMN_DESERTION_DATE, person, 'desertion_date').classes('w-1/3')

                    with ui.row().classes('w-full mt-2'):
                        ui.input(COLUMN_EXECUTOR).bind_value(person, 'executor').classes('flex-grow')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        date_input(COLUMN_RETURN_DATE, person, 'return_date').classes('w-1/3')
                        date_input(COLUMN_RETURN_TO_RESERVE_DATE, person, 'return_reserve_date', blur_handler=fix_date).classes('w-1/3')

                    with ui.row().classes('w-full mt-2'):
                        ui.textarea(COLUMN_DESERT_CONDITIONS).bind_value(person, 'desertion_conditions').classes('w-full')

                # ПАНЕЛЬ 4: Біографія
                with ui.tab_panel(bio_tab):
                    ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full')

                # ПАНЕЛЬ 5: ЕРДР, КПП
                with ui.tab_panel(erdr_tab):
                    with ui.row().classes('w-full gap-4 mt-2'):
                        search_select(ui_options.get(COLUMN_REVIEW_STATUS, []), COLUMN_REVIEW_STATUS, person,
                                      'review_status').classes('flex-grow')
                        ui.input(COLUMN_CC_ARTICLE).bind_value(person, 'cc_article').classes('w-40')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(person, 'o_ass_num').classes('w-1/3')
                        date_input(COLUMN_ORDER_ASSIGNMENT_DATE, person, 'o_ass_date', blur_handler=fix_date).classes('w-1/3')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(person, 'o_res_num').classes('w-1/3')
                        date_input(COLUMN_ORDER_RESULT_DATE, person, 'o_res_date', blur_handler=fix_date).classes('w-1/3')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.input(COLUMN_KPP_NUMBER).bind_value(person, 'kpp_num').classes('w-1/3')
                        date_input(COLUMN_KPP_DATE, person, 'kpp_date', blur_handler=fix_date).classes('w-1/3')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.input(COLUMN_DBR_NUMBER).bind_value(person, 'dbr_num').classes('w-1/3')
                        date_input(COLUMN_DBR_DATE, person, 'dbr_date', blur_handler=fix_date).classes('w-1/3')


        # КНОПКИ ДІЇ
        with ui.row().classes('w-full justify-end mt-4 gap-2'):
            ui.button('Скасувати', on_click=dialog.close).props('outline')
            if person_ctrl.auth_manager.has_access('person', 'write'):
                ui.button('💾 ЗБЕРЕГТИ',
                          on_click=lambda: handle_save(person, person_ctrl, ctx, dialog, on_close=on_close, paint_color=None)) \
                    .classes('bg-green-600 text-white')

    dialog.open()


def edit_erdr(person: Person, person_ctrl, ctx: RequestContext, on_close=None):
    ui_options = person_ctrl.get_column_options()

    with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-none'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(f"Картка Військовослужбовця: {person.name}").classes('text-xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round')

        # ТАБИ
        with ui.tabs().classes('w-full') as tabs:
            main_tab = ui.tab('💼 ДБР')
            bio_tab = ui.tab('📝 БІО')

        with ui.tab_panels(tabs, value=main_tab).classes('w-full'):
            # ВАЖЛИВО: Встановлюємо дефолтний статус ЛИШЕ якщо поле порожнє
            if not person.review_status:
                person.review_status = REVIEW_STATUS_WAITING

            with ui.tab_panel(main_tab):
                with ui.row().classes('w-full gap-4'):
                    ui.input(COLUMN_NAME).bind_value(person, 'name').classes('flex-grow').props('readonly')
                    ui.input(COLUMN_ID_NUMBER).bind_value(person, 'rnokpp').classes('w-40').props('readonly')

                with ui.row().classes('w-full gap-4 mt-2'):
                    search_select(ui_options.get(COLUMN_REVIEW_STATUS, []), COLUMN_REVIEW_STATUS, person,
                                  'review_status').classes('flex-grow')
                    ui.input(COLUMN_CC_ARTICLE).bind_value(person, 'cc_article').classes('w-40')

                with ui.row().classes('w-full gap-4 mt-2'):
                    ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(person, 'o_ass_num').classes('w-40')
                    date_input(COLUMN_ORDER_ASSIGNMENT_DATE, person, 'o_ass_date').classes('w-1/3')

                with ui.row().classes('w-full gap-4 mt-2'):
                    ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(person, 'o_res_num').classes('w-40')
                    date_input(COLUMN_ORDER_RESULT_DATE, person, 'o_res_date', blur_handler=fix_date).classes('w-1/3')

                with ui.row().classes('w-full gap-4 mt-2'):
                    ui.input(COLUMN_KPP_NUMBER).bind_value(person, 'kpp_num').classes('w-40')
                    date_input(COLUMN_KPP_DATE, person, 'kpp_date', blur_handler=fix_date).classes('w-1/3')

                with ui.row().classes('w-full gap-4 mt-2'):
                    ui.input(COLUMN_DBR_NUMBER).bind_value(person, 'dbr_num').classes('w-40')
                    # Передаємо blur_handler для фіксу дати
                    date_input(COLUMN_DBR_DATE, person, 'dbr_date', blur_handler=fix_date).classes('w-1/3')

            with ui.tab_panel(bio_tab):
                ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full')

        # КНОПКИ ДІЇ
        with ui.row().classes('w-full justify-end mt-4 gap-2'):
            ui.button('Скасувати', on_click=dialog.close).props('outline')
            if person_ctrl.auth_manager.has_access('person', 'write'):
                ui.button('💾 ЗБЕРЕГТИ', on_click=lambda: handle_save(person, person_ctrl, ctx, dialog, on_close=on_close,
                                                                     paint_color=EXCEL_BLUE_COLOR)) \
                .classes('bg-green-600 text-white')

    dialog.open()


async def handle_save(person, person_ctrl, ctx, dialog, on_close=None, paint_color=None):
    with ui.notification(message='Зберігаю дані...', spinner=True, timeout=0) as n:
        await asyncio.sleep(0.1)  # Даємо UI відмалювати спінер

        success = await run.io_bound(person_ctrl.save_person, ctx, person, paint_color)

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