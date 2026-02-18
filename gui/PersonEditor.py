from pywebio.input import *
from pywebio.output import *
from pywebio import session
import config
from dics.deserter_xls_dic import *
import datetime
from utils.utils import format_to_excel_date, to_html_date

class PersonEditor:
    def __init__(self, row_data, callback_save):
        self.row_data = row_data
        self.state = {k: v for k, v in row_data.items()}
        self.callback_save = callback_save
        self.current_tab = "main"  # Початкова вкладка

    def show(self):
        """Головний метод малювання редактора"""
        self.render_editor_ui()

    def render_editor_ui(self):
        with use_scope('content_area', clear=True):
            put_markdown(f"# 👤 Редагування: {self.state.get(COLUMN_NAME, 'Картка')}")
            # 1. Створюємо зону для кнопок-табів (вони будуть завжди видимі)
            put_scope('editor_tabs')
            # 2. Створюємо зону для самої форми
            put_scope('editor_form')

            self._draw_tabs()
            self._draw_form()

    def _draw_tabs(self):
        with use_scope('editor_tabs', clear=True):
            # Малюємо "Таби" як кнопки зверху
            put_row([
                put_button('🏠 Основна інформація',
                           onclick=lambda: self._switch_tab('main'),
                           color='primary', outline=self.current_tab != 'main'),
                put_button('📝 Біографія та ЄРДР',
                           onclick=lambda: self._switch_tab('bio'),
                           color='primary', outline=self.current_tab != 'bio'),
                put_button('💾 ЗБЕРЕГТИ', onclick=self._handle_save, color='success'),
                put_button('❌ Закрити', onclick=lambda: clear('content_area'), color='danger'),
            ], size='25% 25% 25% 25%').style('margin-bottom: 20px;')

    def _switch_tab(self, tab_name):
        self.current_tab = tab_name
        self._draw_tabs()  # Оновлюємо вигляд кнопок
        self._draw_form()  # Оновлюємо форму

    def _draw_form(self):
        with use_scope('editor_form', clear=True):
            if self.current_tab == 'main':
                # Використовуємо input_group. При натисканні "Submit" дані оновлять self.state
                data = input_group("Основні дані", [
                    input(COLUMN_NAME, name="name", value=str(self.state.get(COLUMN_NAME, ""))),
                    input(COLUMN_ID_NUMBER, name="id_number",
                          value=str(self.state.get(COLUMN_ID_NUMBER, "") or "")),
                    input(COLUMN_BIRTHDAY, name="dob", type=DATE,
                          value=to_html_date(self.state.get(COLUMN_BIRTHDAY))),
                    input(COLUMN_DESERTION_DATE, name="des_date", type=DATE,
                          value=to_html_date(self.state.get(COLUMN_DESERTION_DATE))),
                ], cancelable=True)

                if data:  # Якщо не натиснуто "Cancel" у групі
                    self._update_state(data, 'main')
                    put_success("Дані вкладки тимчасово збережені в пам'ять")

            elif self.current_tab == 'bio':
                data = input_group("Біографія та обставини", [
                    textarea("Біографія (Обставини)", name="bio",
                             value=str(self.state.get(COLUMN_BIO, "")), rows=8),
                    input("Номер ЄРДР", name="erdr", value=str(self.state.get("COLUMN_ERDR", ""))),
                    input("Стаття ККУ", name="article", value=str(self.state.get("COLUMN_ARTICLE", ""))),
                ], cancelable=True)

                if data:
                    self._update_state(data, 'bio')
                    put_success("Дані вкладки тимчасово збережені в пам'ять")

    def _update_state(self, data, tab):
        """Синхронізація вводу зі станом об'єкта"""
        if tab == 'main':
            self.state[COLUMN_NAME] = data["name"]
            self.state[COLUMN_ID_NUMBER] = data["id_number"]
            self.state[COLUMN_BIRTHDAY] = data["dob"]
            self.state[COLUMN_DESERTION_DATE] = data["des_date"]
        elif tab == 'bio':
            self.state[COLUMN_BIO] = data["bio"]
            self.state["COLUMN_ERDR"] = data["erdr"]
            self.state["COLUMN_ARTICLE"] = data["article"]

    def _handle_save(self):
        """Фінальне збереження через callback"""
        put_loading()  # Візуальний ефект
        self.callback_save(self.state)
        put_success("🎉 Всі зміни успішно записані в Excel файл!")
        # Можна автоматично повернутися на пошук через пару секунд

    def validate_rnokpp(self, val):
        """Валідація РНОКПП: рівно 10 цифр"""
        if not val or not str(val).isdigit() or len(str(val)) != 10:
            return "РНОКПП має складатися рівно з 10 цифр"
        return None