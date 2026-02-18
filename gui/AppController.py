from pywebio.output import *
from pywebio.input import *
from pywebio.pin import *
import pywebio


class AppController:
    def __init__(self, workflow):
        self.workflow = workflow
        self.current_page = "search_pib"

    def apply_styles(self):
        """Додаємо CSS для розширення та фіксації меню"""
        put_html('''
            <style>
                .container { max-width: 98% !important; }
                .sticky-menu {
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    background: white;
                    padding: 10px 0;
                    border-bottom: 2px solid #3498db;
                    margin-bottom: 20px;
                }
                /* Робимо так, щоб кнопки меню були в ряд */
                .menu-btns { display: flex; justify-content: flex-start; gap: 10px; }
            </style>
        ''')

    def render_layout(self):
        """Створює структуру сторінки"""
        clear()
        self.apply_styles()

        # Створюємо два контейнери: для меню і для контенту
        put_scope('menu_area').addClass('sticky-menu')
        put_scope('content_area')

        self.render_menu()
        self.show_current_page()

    def render_menu(self):
        """Малює кнопки навігації"""
        with use_scope('menu_area', clear=True):
            put_row([
                put_button('🔍 Пошук (ПІБ)', onclick=lambda: self.navigate('search_pib'), color='primary',
                           outline=self.current_page != 'search_pib'),
                put_button('⚖️ Реєстрація ЄРДР', onclick=lambda: self.navigate('erdr_reg'), color='primary',
                           outline=self.current_page != 'erdr_reg'),
                put_button('📅 Дати', onclick=lambda: self.navigate('search_dates'), color='primary',
                           outline=self.current_page != 'search_dates'),
                put_button('⚙️ Налаштування', onclick=lambda: self.navigate('settings'), color='secondary')
            ]).addClass('menu-btns')

    def navigate(self, page_name):
        """Зміна сторінки без перезавантаження всього додатка"""
        self.current_page = page_name
        self.render_menu()  # Оновлюємо вигляд кнопок (активна/неактивна)
        self.show_current_page()

    def show_current_page(self):
        """Диспетчер контенту"""
        with use_scope('content_area', clear=True):
            if self.current_page == "search_pib":
                self.run_search_module()
            elif self.current_page == "erdr_reg":
                self.run_erdr_module()
            elif self.current_page == "settings":
                put_text("Налаштування шляхів до Excel/SQL...")

    def run_search_module(self):
        put_markdown("## 🔍 Пошук по ПІБ / РНОКПП")
        # Тут викликаємо ваш PersonSearch(self.workflow).show()
        # Пам'ятайте, що всередині PersonSearch теж треба використовувати use_scope('content_area')
        put_text("Форма пошуку завантажена...")

    def run_erdr_module(self):
        put_markdown("## ⚖️ Реєстрація ЄРДР")
        order_no = input("Введіть номер наказу для пошуку:")
        put_text(f"Результати для наказу №{order_no}")

    def start(self):
        self.render_layout()
        # Тримаємо сесію відкритою для обробки натискань кнопок
        pywebio.session.hold()