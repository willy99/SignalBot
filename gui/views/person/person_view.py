from nicegui import ui, run

from dics.deserter_xls_dic import *
from gui.model.person import Person
import asyncio
from config import UI_DATE_FORMAT

def edit_person(person: Person, person_ctrl, on_close=None):
    ui_options = person_ctrl.get_column_options()

    print(" date " + str(person.birthday))

    with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-none'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(f"Картка: {person.name}").classes('text-xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round')

        # ТАБИ
        with ui.tabs().classes('w-full') as tabs:
            main_tab = ui.tab('🏠 Основна інформація')
            tzk_tab = ui.tab('🏠 ТЦК')
            des_tab = ui.tab('🏠 СЗЧ та повернення')
            bio_tab = ui.tab('📝 Біографія')

        with ui.tab_panels(tabs, value=main_tab).classes('w-full'):
            # ПАНЕЛЬ 1
            with ui.tab_panel(main_tab):
                with ui.row().classes('w-full'):
                    ui.input(COLUMN_NAME).bind_value(person, 'name').classes('flex-grow')
                    ui.input(COLUMN_ID_NUMBER).bind_value(person, 'rnokpp').classes('w-40')

                with ui.row().classes('w-full'):
                    ui.select(
                        options=ui_options[COLUMN_TITLE],
                        label=COLUMN_TITLE,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'title').classes('flex-grow').props('use-input fill-input hide-selected')
                    ui.select(
                        options=ui_options[COLUMN_TITLE_2],
                        label=COLUMN_TITLE_2,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'title2').classes('flex-grow').props('use-input fill-input hide-selected')
                    ui.select(
                        options=ui_options[COLUMN_SUBUNIT],
                        label=COLUMN_SUBUNIT,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'subunit').classes('w-40').props('use-input fill-input hide-selected')
                    ui.select(
                        options=ui_options[COLUMN_SUBUNIT2],
                        label=COLUMN_SUBUNIT2,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'subunit2').classes('w-40').props('use-input fill-input hide-selected')
                with ui.row().classes('w-full'):
                    ui.input(COLUMN_ADDRESS).bind_value(person, 'address').classes('flex-grow')
                    ui.input(COLUMN_PHONE).bind_value(person, 'phone').classes('w-40')
                with ui.row().classes('w-full'):
                    with ui.input(label=COLUMN_BIRTHDAY) as date_input:
                        date_input.bind_value(person, 'birthday')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'birthday').props('mask="'+UI_DATE_FORMAT+'"')

            # ПАНЕЛЬ 2
            with ui.tab_panel(tzk_tab):
                with ui.row().classes('w-full'):
                    ui.input(COLUMN_TZK).bind_value(person, 'tzk').classes('flex-grow')
                    with ui.input(label=COLUMN_ENLISTMENT_DATE) as date_input:
                        date_input.bind_value(person, 'enlistment_date')  # Прив'язуємо до моделі
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'enlistment_date').props('mask="'+UI_DATE_FORMAT+'"')

                with ui.row().classes('w-full'):
                    ui.select(
                        options=ui_options[COLUMN_TZK_REGION],
                        label=COLUMN_TZK_REGION,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'tzk_region').classes('w-1/3').props('use-input fill-input hide-selected')
            # ПАНЕЛЬ 3
            with ui.tab_panel(des_tab):
                with ui.row().classes('w-full'):
                    ui.select(
                        options=ui_options[COLUMN_DESERTION_PLACE],
                        label=COLUMN_DESERTION_PLACE,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'desertion_place').classes('w-40').props('use-input fill-input hide-selected')
                    ui.select(
                        options=ui_options[COLUMN_DESERTION_TYPE],
                        label=COLUMN_DESERTION_TYPE,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'desertion_type').classes('w-40').props('use-input fill-input hide-selected')
                    ui.select(
                        options=ui_options[COLUMN_DESERTION_REGION],
                        label=COLUMN_DESERTION_REGION,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'desertion_region').classes('flex-grow').props('use-input fill-input hide-selected')
                with ui.row().classes('w-full'):
                    with ui.input(label=COLUMN_DESERTION_DATE).classes('w-1/3') as date_input:
                        date_input.bind_value(person, 'desertion_date')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'desertion_date').props('mask="'+UI_DATE_FORMAT+'"')
                with ui.row().classes('w-full'):
                        ui.input(COLUMN_EXECUTOR).bind_value(person, 'executor').classes('flex-grow')
                with ui.row().classes('w-full'):
                    with ui.input(label=COLUMN_RETURN_DATE) as date_input:
                        date_input.bind_value(person, 'return_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'return_date').props('mask="'+UI_DATE_FORMAT+'"')
                    with ui.input(label=COLUMN_RETURN_TO_RESERVE_DATE) as date_input:
                        date_input.bind_value(person, 'return_reserve_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'return_reserve_date').props('mask="'+UI_DATE_FORMAT+'"')
                with ui.row().classes('w-full'):
                    ui.textarea(COLUMN_DESERT_CONDITIONS).bind_value(person, 'desertion_conditions').classes('w-full')


            with ui.tab_panel(bio_tab):
                ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full')

        # КНОПКИ ДІЇ
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Скасувати', on_click=dialog.close).props('outline')
            ui.button('💾 ЗБЕРЕГТИ', on_click=lambda: handle_save(person, person_ctrl, dialog, on_close=on_close)) \
                .classes('bg-green-600 text-white')

    dialog.open()



def edit_erdr(person: Person, person_ctrl, on_close=None):
    ui_options = person_ctrl.get_column_options()
    print(' o_res_num ' + person.o_res_num)

    with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-none'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(f"Картка: {person.name}").classes('text-xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round')

        # ТАБИ
        with ui.tabs().classes('w-full') as tabs:
            main_tab = ui.tab('🏠 ЄРДР')
            bio_tab = ui.tab('🏠 БІО')

        with ui.tab_panels(tabs, value=main_tab).classes('w-full'):
            # ПАНЕЛЬ 1
            with ui.tab_panel(main_tab):
                with ui.row().classes('w-full'):
                    ui.input(COLUMN_NAME).bind_value(person, 'name').classes('flex-grow').props('readonly')
                    ui.input(COLUMN_ID_NUMBER).bind_value(person, 'rnokpp').classes('w-40').props('readonly')

                with ui.row().classes('w-full'):
                    ui.select(
                        options=ui_options[COLUMN_REVIEW_STATUS],
                        label=COLUMN_REVIEW_STATUS,
                        with_input=False  # Дозволяє фільтрувати список текстом
                    ).bind_value(person, 'review_status').classes('flex-grow').props('use-input fill-input hide-selected')
                    ui.input(COLUMN_CC_ARTICLE).bind_value(person, 'cc_article').classes('w-40')
                with ui.row().classes('w-full'):
                    ui.input(COLUMN_ORDER_ASSIGNMENT_NUMBER).bind_value(person, 'o_ass_num').classes('w-40')
                    with ui.input(label=COLUMN_ORDER_ASSIGNMENT_DATE) as date_input:
                        date_input.bind_value(person, 'o_ass_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'o_ass_date').props('mask="'+UI_DATE_FORMAT+'"')

                with ui.row().classes('w-full'):
                    ui.input(COLUMN_ORDER_RESULT_NUMBER).bind_value(person, 'o_res_num').classes('w-40')
                    with ui.input(label=COLUMN_ORDER_RESULT_DATE) as date_input:
                        date_input.bind_value(person, 'o_res_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'o_res_date').props('mask="'+UI_DATE_FORMAT+'"')


                with ui.row().classes('w-full'):
                    ui.input(COLUMN_KPP_NUMBER).bind_value(person, 'kpp_num').classes('w-40')
                    with ui.input(label=COLUMN_KPP_DATE) as date_input:
                        date_input.bind_value(person, 'kpp_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'kpp_date').props('mask="'+UI_DATE_FORMAT+'"')

                with ui.row().classes('w-full'):
                    ui.input(COLUMN_DBR_NUMBER).bind_value(person, 'dbr_num').classes('w-40')
                    with ui.input(label=COLUMN_DBR_DATE) as date_input:
                        date_input.bind_value(person, 'dbr_date').classes('w-1/3')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').classes('cursor-pointer')
                        with ui.menu() as menu:
                            ui.date().bind_value(person, 'dbr_date').props('mask="'+UI_DATE_FORMAT+'"')

            # ПАНЕЛЬ 2
            with ui.tab_panel(bio_tab):
                ui.textarea(COLUMN_BIO).bind_value(person, 'bio').classes('w-full')

        # КНОПКИ ДІЇ
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Скасувати', on_click=dialog.close).props('outline')
            ui.button('💾 ЗБЕРЕГТИ', on_click=lambda: handle_save(person, person_ctrl, dialog, on_close=on_close)) \
                .classes('bg-green-600 text-white')

    dialog.open()


async def handle_save(person, person_ctrl, dialog, on_close=None):
    # Показуємо індикатор завантаження
    with ui.notification(message='Зберігаю дані...', spinner=True, timeout=0) as n:
        await asyncio.sleep(0.1)

        success = await run.io_bound(person_ctrl.save_person, person)

        if success:
            n.message = 'Успішно збережено!'
            n.type = 'positive'
            n.spinner = False
            n.timeout = 2
            ui.timer(1.0, dialog.close, once=True)
            ui.timer(1.0, dialog.close, once=True)
            if on_close:
                # Якщо це асинхронна функція (як do_search)
                if asyncio.iscoroutinefunction(on_close):
                    await on_close()
                else:
                    on_close()

        else:
            n.message = 'Помилка запису!'
            n.type = 'negative'
            n.spinner = False
