from pywebio.input import *
from pywebio.output import *
from pywebio import session
import config
from dics.deserter_xls_dic import *
import datetime
from utils.utils import format_to_excel_date, to_html_date
from pywebio.pin import * # Важливо для "живих" форм
from gui. style import *

class PersonEditor:
    def __init__(self, row_data, callback_save, gui_helper):
        self.row_data = row_data
        self.state = {k: v for k, v in row_data.items()}
        self.callback_save = callback_save
        self.current_tab = "main"  # Початкова вкладка
        self.gui = gui_helper

    def show(self):
        put_html("""
                <style>
                    .compact-form p { margin-bottom: 0.2rem !important; margin-top: 0.5rem !important; font-weight: bold; }
                    .compact-form div { margin-bottom: 0.2rem !important; }
                </style>
            """)

        self.render_editor_ui()

    def render_editor_ui(self):
        with use_scope('content_area', clear=True):
            clear()
            put_markdown(f"# 👤 Редагування: {self.state.get(COLUMN_NAME, 'Картка')}")
            # 1. Створюємо зону для кнопок-табів (вони будуть завжди видимі)
            put_scope('editor_tabs')
            # 2. Створюємо зону для самої форми
            put_scope('editor_form')

            self._draw_tabs()
            self._draw_form()

    def _switch_tab(self, tab_name):
        self._sync_state_from_pin()
        self.current_tab = tab_name
        self._draw_tabs()  # Оновлюємо вигляд кнопок
        self._draw_form()  # Оновлюємо форму

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
                None,
                put_button('💾 ЗБЕРЕГТИ', onclick=self._handle_save, color='success').style(css_style=css_button),
                put_button('❌ Закрити', onclick=lambda: self.gui.navigate('search_pib'), color='danger').style(css_style=css_button),
            ], size='auto auto 1fr auto auto').style(css_style=css_tab_button)

    def _draw_form(self):
        with use_scope('editor_form', clear=True):
            # Додаємо клас compact-form для управління відступами
            with put_column().style('margin-top: 10px; padding: 5px;'):
                if self.current_tab == 'main':
                    put_text(COLUMN_NAME)
                    put_input('pin_name', value=str(self.state.get(COLUMN_NAME, "")))

                    put_text(COLUMN_ID_NUMBER)
                    put_input('pin_id', value=str(self.state.get(COLUMN_ID_NUMBER, "")))

                    put_text(COLUMN_BIRTHDAY)
                    put_input('pin_dob', type=DATE, value=to_html_date(self.state.get(COLUMN_BIRTHDAY)))

                    put_text(COLUMN_DESERTION_DATE)
                    put_input('pin_des', type=DATE, value=to_html_date(self.state.get(COLUMN_DESERTION_DATE)))

                elif self.current_tab == 'bio':
                    put_text(COLUMN_BIO)
                    put_textarea('pin_bio', value=str(self.state.get(COLUMN_BIO, "")), rows=8)

                    put_text(COLUMN_DESERT_CONDITIONS)
                    put_textarea('pin_cond', value=str(self.state.get(COLUMN_DESERT_CONDITIONS, "")), rows=8)

    def _sync_state_from_pin(self):
        """Зчитує дані з усіх можливих pin-полів у self.state"""

        mapping = {
            'pin_name': COLUMN_NAME,
            'pin_id': COLUMN_ID_NUMBER,
            'pin_dob': COLUMN_BIRTHDAY,
            'pin_des': COLUMN_DESERTION_DATE,
            'pin_bio': COLUMN_BIO,
            'pin_cond': COLUMN_DESERT_CONDITIONS
        }

        for pin_name, excel_col in mapping.items():
            try:
                # В деяких версіях краще працює pin[name]
                if pin_name in pin:
                    val = pin[pin_name]
                    # Зберігаємо навіть порожні рядки, щоб можна було видалити дані
                    self.state[excel_col] = val
            except Exception:
                continue

    def _handle_save(self):
        # 1. Збираємо дані з полів, які зараз на екрані
        self._sync_state_from_pin()
        with use_scope('editor_form'):
            put_loading()
            try:
                self.callback_save(self.state)
                clear('content_area')
                self.gui.navigate('search_pib')
            except Exception as e:
                clear('editor_form')
                put_error(f"Помилка при збереженні: {e}")

    def validate_rnokpp(self, val):
        """Валідація РНОКПП: рівно 10 цифр"""
        if not val or not str(val).isdigit() or len(str(val)) != 10:
            return "РНОКПП має складатися рівно з 10 цифр"
        return None