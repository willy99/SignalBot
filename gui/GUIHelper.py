from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import set_env, hold
from gui.PersonSearch import PersonSearch
from gui.PersonEditor import PersonEditor
import threading

class GUIHelper:
    def __init__(self):
        self.current_page = "search_pib"
        self.workflow = None

    def open_editor_from_excel(self, workflow):
        self.workflow = workflow

        def main_logic():
            set_env(output_max_width='95%')
            # 1. Створюємо стилі та структуру (меню + контент)
            put_html('''
                            <style>
                                .sticky-menu {
                                    position: sticky; top: 0; z-index: 1000;
                                    background: #f8f9fa; padding: 10px;
                                    border-bottom: 2px solid #007bff; margin-bottom: 20px;
                                }
                            </style>
                        ''')

            # 2. Оголошуємо СТРУКТУРУ (порядок цих рядків визначає порядок на екрані)
            put_scope('menu_area').style(
                'position: sticky; top: 0; z-index: 1000; background: #f8f9fa; border-bottom: 2px solid #007bff;')
            put_scope('content_area')

            # 2. Малюємо меню вперше
            self.render_menu()
            # 3. Відображаємо початкову сторінку
            self.show_page()

            # Тримаємо сесію відкритою, щоб працювали кліки меню
            hold()
        threading.Thread(target=lambda: start_server(main_logic, port=0, auto_open_webbrowser=True),
                         daemon=True).start()


    def render_menu(self):
        with use_scope('menu_area', clear=True):
            clear()
            put_row([
                put_button('🔍 Пошук ПІБ/ІПН', onclick=lambda: self.navigate('search_pib'),
                           color='primary', outline=self.current_page != 'search_pib'),
                put_button('⚖️ Реєстрація ЄРДР', onclick=lambda: self.navigate('erdr_reg'),
                           color='primary', outline=self.current_page != 'erdr_reg'),
                put_button('⚙️ Налаштування', onclick=lambda: self.navigate('settings'),
                           color='secondary')
            ], size='200px 200px 1fr')

    def navigate(self, page_name):
        self.current_page = page_name
        self.render_menu()  # Оновити кнопки (підсвітити активну)
        self.show_page()

    def show_page(self):
        """Диспетчер сторінок — сюди переїхала ваша логіка"""
        clear('content_area')
        with use_scope('content_area', clear=True):
            if self.current_page == "search_pib":
                self.run_search_flow()
            elif self.current_page == "erdr_reg":
                self.run_erdr_flow()
            elif self.current_page == "settings":
                put_text("Налаштування будуть тут...")

    def run_search_flow(self):
        """Ваша стара логіка main_logic, адаптована під scope"""
        search_engine = PersonSearch(self.workflow)

        while self.current_page == "search_pib":
            # 1. Форма пошуку
            query = search_engine.show_search_form()

            # Очищуємо все, крім самого верху, щоб результати не накопичувалися від попередніх пошуків
            clear('results')

            with use_scope('results'):
                put_text("⏳ Шукаю в базі...")

            results = search_engine.search(query)

            if not results:
                with use_scope('results', clear=True):
                    put_error(f"❌ Нікого не знайдено за запитом: {query}")
                continue  # Повертаємося до input() автоматично

            # 2. Вибір особи (якщо один — одразу, якщо багато — список)
            target_person = None
            if len(results) == 1:
                self.open_editor(results[0])
                break
            else:
                search_engine.select_person(results, on_select_callback=self.open_editor)
                break

    def open_editor(self, target_person):
        row_idx = target_person['row_idx']
        row_data = target_person['data']

        def save_to_excel(updated_data):
            sheet = self.workflow.excelProcessor.sheet
            headers = self.workflow.excelProcessor.header
            max_col = max(headers.values())
            current_row_values = list(sheet.range((row_idx, 1), (row_idx, max_col)).value)

            # 3. Оновлюємо значення у списку
            for key, val in updated_data.items():
                if key in headers:
                    col_idx = headers[key]
                    # Індексація в Python починається з 0, а в Excel з 1
                    current_row_values[col_idx - 1] = val
                else:
                    print(f"⚠️ Ключ '{key}' не знайдено в Excel")
            sheet.range((row_idx, 1), (row_idx, max_col)).value = current_row_values

            try:
                self.workflow.excelProcessor.workbook.save()
                put_success(f"💾 Дані записано та файл збережено (рядок {row_idx})")
            except Exception as e:
                put_error(f"Помилка при збереженні файлу: {e}")

        editor = PersonEditor(row_data, save_to_excel, self)
        editor.show()

    def run_erdr_flow(self):
        put_markdown("## ⚖️ Реєстрація даних ЄРДР")
        order_no = input("Введіть номер наказу:")
        put_text(f"Пошук за наказом №{order_no}...")
        # Сюди ми допишемо логіку пошуку по конкретному стовпцю