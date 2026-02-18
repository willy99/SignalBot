from pywebio.input import *
from pywebio.output import *
from pywebio.session import set_env
from pywebio import session
from pywebio.pin import * # Імпортуємо pin

import config
from dics.deserter_xls_dic import *
import datetime

class PersonSearch:
    def __init__(self, workflow):
        self.workflow = workflow
        self.processor = workflow.excelProcessor

    def show_search_form(self):
        """Показує поле пошуку"""
        set_env(output_max_width='95%')
        with use_scope('content_area'):
            put_markdown("# 🔍 Пошук особи")

        query = input("Введіть ПІБ або РНОКПП:",
                      placeholder="Наприклад: бондаренко або 30455...",
                      required=True)
        return str(query).strip().lower()

    def search(self, query):
        """Шукає збіги в Excel"""
        self.processor.switch_to_sheet(config.DESERTER_TAB_NAME)
        results = []
        # Отримуємо всі дані з листа (через ваш кеш або пряме читання)
        # Припустимо, ми читаємо активну область
        last_row = self.processor.sheet.range((65536, 1)).end('up').row
        data = self.processor.sheet.range(f"A2:Z{last_row}").value  # Читаємо все відразу для швидкості пошуку в пам'яті
        headers = self.processor.header

        # Індекси стовпців
        pib_idx = headers.get(COLUMN_NAME) - 1
        rnokpp_idx = headers.get(COLUMN_ID_NUMBER) - 1

        for i, row in enumerate(data):
            if not row[pib_idx]: continue

            pib_val = str(row[pib_idx]).lower()
            # Обробка РНОКПП (може бути float або int в Excel)
            try:
                rnokpp_val = str(int(float(row[rnokpp_idx]))) if row[rnokpp_idx] else ""
            except:
                rnokpp_val = str(row[rnokpp_idx])

            # print('query ' + str(query) +  ' in ' + str(pib_val) + ' or ' + str(rnokpp_val))
            if query in pib_val or query in rnokpp_val:
                # Зберігаємо номер рядка (i + 2, бо дані з A2) та словник даних

                serialized_row = []
                for cell in row:
                    if isinstance(cell, (datetime.datetime, datetime.date)):
                        # Перетворюємо дату на рядок відразу
                        serialized_row.append(cell.strftime(config.EXCEL_DATE_FORMAT))
                    elif isinstance(cell, float):
                        if cell.is_integer():
                            serialized_row.append(int(cell))
                        else:
                            serialized_row.append(cell)
                    else:
                        serialized_row.append(cell)
                results.append({
                    'row_idx': i + 2,
                    'data': dict(zip(headers, serialized_row))
                })

        return results

    def select_person(self, results, on_select_callback):
        """Виводить результати у вигляді таблиці з кнопкою вибору"""

        with use_scope('content_area', clear=True):
            with use_scope('results', clear=True):
                put_markdown(f"### 📋 Знайдено варіантів: {len(results)}")

                # Готуємо дані для таблиці
                table_data = []
                for res in results:
                    d = res['data']

                    edit_btn = put_buttons(
                        [{'label': '📝 Редагувати', 'value': res, 'color': 'primary'}],
                        onclick=lambda val: on_select_callback(val)  # Тут 'val' отримає 'res' з поля 'value'
                    )

                    table_data.append([
                        d.get(COLUMN_NAME),
                        d.get(COLUMN_ID_NUMBER),
                        d.get(COLUMN_DESERTION_DATE) or '---',
                        d.get(COLUMN_RETURN_DATE) or '---',
                        edit_btn  # Кнопка в останній колонці
                    ])

                # Виводимо таблицю
                put_table(
                    table_data,
                    header=["ПІБ", "РНОКПП", "Дата СЗЧ", "Дата повернення", "Дія"]
                )


                # Додаємо кнопку скасування під таблицею, якщо ніхто не підходить
                put_buttons([{'label': '❌ Скасувати пошук', 'value': 'cancel', 'color': 'danger'}],
                            onclick=lambda val: pin_update('selection_buffer', value=val))

