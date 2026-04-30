import pytest
from dics.deserter_xls_dic import *
import random
from datetime import datetime, timedelta
from utils.utils import format_to_excel_date


def generate_test_records(count=20):
    """Генерує список випадкових записів для тестів ExcelProcessor"""
    names = ["Іваненко", "Петренко", "Сидоренко", "Коваленко", "Бондаренко", "Ткаченко", "Кравченко"]
    first_names = ["Олександр", "Дмитро", "Сергій", "Андрій", "Володимир", "Микола", "Олег"]
    patronymics = ["Іванович", "Петрович", "Миколайович", "Олександрович", "Андрійович", "Вікторович"]
    regions = ["Київська", "Одеська", "Львівська", "Харківська", "Донецька", "Дніпропетровська"]
    titles = ["cолдат", "старший солдат"]
    des_place = ["РВБЗ", "лікування", "відпустка"]

    records = []

    for i in range(count):
        # Генеруємо ПІБ
        full_name = f"{random.choice(names)} {random.choice(first_names)} {random.choice(patronymics)}"

        # Генеруємо випадковий РНОКПП (10 цифр)
        rnokpp = "".join([str(random.randint(0, 9)) for _ in range(10)])

        # Генеруємо випадкову дату народження (між 1970 та 2000 роками)
        birth_date = (datetime(1970, 1, 1) + timedelta(days=random.randint(0, 11000))).strftime("%d.%m.%Y")

        # Дата дезертирства (недавня)
        desertion_date = (datetime(2022, 2, 24) + timedelta(days=random.randint(0, 700))).strftime("%d.%m.%Y")

        record = {
            COLUMN_INSERT_DATE: format_to_excel_date(datetime.now()),
            COLUMN_NAME: full_name,
            COLUMN_ID_NUMBER: rnokpp if random.random() > 0.1 else None,  # 10% шанс, що РНОКПП порожній
            COLUMN_BIRTHDAY: birth_date,
            COLUMN_DESERTION_DATE: desertion_date,
            COLUMN_MIL_UNIT: f"ВЧ А{random.randint(1000, 9999)}",
            COLUMN_TZK_REGION: f"{random.choice(regions)} область",
            COLUMN_DESERTION_REGION: f"{random.choice(regions)} область",
            COLUMN_TITLE: f"{random.choice(titles)}",
            COLUMN_DESERTION_PLACE: f"{random.choice(des_place)}",
            COLUMN_TITLE_2: f"солдат",
            COLUMN_REVIEW_STATUS: REVIEW_STATUS_NOT_ASSIGNED,
            COLUMN_CC_ARTICLE: ARTICLE_407_ABANDONEMENT,
            "source_file": "test_batch.pdf"
        }
        records.append(record)

    return records

