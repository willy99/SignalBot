import pytest
from service.processing.processors.ExcelProcessor import ExcelProcessor
from dics.deserter_xls_dic import *
import config

from tests.test_tools import generate_test_records
from utils.utils import format_to_excel_date


def test_upsert_inserts_new_record(temp_excel_file, mock_logger):
    """Перевіряємо, чи додається новий запис, якщо його ще немає в базі"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    new_record = {
        COLUMN_NAME: "Бандера Степан Андрійович",
        COLUMN_ID_NUMBER: "1234567890",
        COLUMN_BIRTHDAY: "01.01.1909",
        COLUMN_DESERTION_DATE: "01.10.2023",
        COLUMN_MIL_UNIT: config.DESERTER_TAB_NAME
    }

    try:
        # 1. Робимо upsert
        success = processor.upsert_record([new_record])
        assert success is True, "upsert_record повернув False"

        # 2. Перевіряємо, чи дані дійсно з'явилися у файлі
        last_row = processor.get_last_row()
        assert last_row >= 2, "Рядок не був доданий"

        # Читаємо значення з колонки ПІБ (знаходимо її індекс)
        pib_col_idx = processor.column_map.get(COLUMN_NAME.lower())
        saved_name = processor.sheet.range((2, pib_col_idx)).value

        assert saved_name == "Бандера Степан Андрійович", "Ім'я збережено неправильно"

    finally:
        processor.close()  # Обов'язково закриваємо процес Excel!


def test_upsert_updates_existing_record(temp_excel_file, mock_logger):
    """Перевіряємо, чи оновлюється існуючий запис (перевірка логіки _find_existing_row)"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    # Створюємо базовий запис
    base_record = {
        COLUMN_NAME: "Бойко Олег Григорович",
        COLUMN_ID_NUMBER: "29110912091",
        COLUMN_BIRTHDAY: "09.03.1999",
        COLUMN_DESERTION_DATE: "15.05.2023",
        COLUMN_MIL_UNIT: config.DESERTER_TAB_NAME
    }

    try:
        # 1. Додаємо запис вперше
        processor.upsert_record([base_record])

        # Перевіряємо, що запис один
        assert processor.get_last_row() == 2

        # 2. "Прилітає" оновлення для цієї ж людини (ті самі ПІБ, РНОКПП, Дата народження)
        # але з новими даними в інших полях (наприклад, з'явилася ВЧ)
        update_record = base_record.copy()
        update_record[COLUMN_TZK_REGION] = "Донецька область"

        # 3. Робимо upsert знову
        processor.upsert_record([update_record])

        # 4. ГОЛОВНА ПЕРЕВІРКА: кількість рядків НЕ ПОВИННА збільшитись!
        assert processor.get_last_row() == 2, "Замість оновлення був створений дублікат!"

    finally:
        processor.close()


def test_upsert_updates_withoutrnokpp_existing_record(temp_excel_file, mock_logger):
    """Перевіряємо, чи оновлюється існуючий запис (перевірка логіки _find_existing_row)"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    # Створюємо базовий запис
    base_record = {
        COLUMN_NAME: "Бойко Олег Григорович",
        COLUMN_ID_NUMBER: None,
        COLUMN_BIRTHDAY: "09.03.1999",
        COLUMN_DESERTION_DATE: "15.05.2023",
        COLUMN_MIL_UNIT: config.DESERTER_TAB_NAME
    }

    try:
        # 1. Додаємо запис вперше
        processor.upsert_record([base_record])

        # Перевіряємо, що запис один
        assert processor.get_last_row() == 2

        # 2. "Прилітає" оновлення для цієї ж людини (ті самі ПІБ, РНОКПП, Дата народження)
        # але з новими даними в інших полях (наприклад, з'явилася ВЧ)
        update_record = base_record.copy()
        update_record[COLUMN_TZK_REGION] = "Донецька область"

        # 3. Робимо upsert знову
        processor.upsert_record([update_record])

        # 4. ГОЛОВНА ПЕРЕВІРКА: кількість рядків НЕ ПОВИННА збільшитись!
        assert processor.get_last_row() == 2, "Замість оновлення був створений дублікат!"

    finally:
        processor.close()


def test_search_people(temp_excel_file, mock_logger):
    """Перевіряємо, чи працює пошук по базі"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    # Спочатку заповнюємо базу
    records = [
        {COLUMN_NAME: "Іванов Іван", COLUMN_ID_NUMBER: "2911111122", COLUMN_DESERTION_DATE: "2023-01-01"},
        {COLUMN_NAME: "Петров Петро", COLUMN_ID_NUMBER: "2911111123", COLUMN_DESERTION_DATE: "2023-01-02"}
    ]

    try:
        processor.upsert_record(records)

        # Створюємо мок для PersonSearchFilter
        from domain.person_filter import PersonSearchFilter
        search_filter = PersonSearchFilter(query="Петро")

        results = processor.search_people(search_filter)

        assert len(results) == 1
        assert results[0]['data'][COLUMN_NAME] == "Петров Петро"

    finally:
        processor.close()


def test_bulk_upsert_and_search(temp_excel_file, mock_logger):
    """Тестуємо вставку 20 записів та пошук по них"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    # Генеруємо 20 записів
    test_data = generate_test_records(20)

    try:
        # 1. Масова вставка
        success = processor.upsert_record(test_data)
        assert success is True

        # 2. Перевіряємо кількість рядків (1 заголовок + 20 записів)
        assert processor.get_last_row() == 21

        # 3. Спробуємо знайти конкретне прізвище з генерації
        target_name = test_data[0][COLUMN_NAME].split()[0]  # Прізвище першого згенерованого

        from domain.person_filter import PersonSearchFilter
        search_filter = PersonSearchFilter(query=target_name)
        results = processor.search_people(search_filter)

        assert len(results) >= 1
        assert target_name in results[0]['data'][COLUMN_NAME]

    finally:
        processor.close()


def test_upsert_logic_with_different_statuses(temp_excel_file, mock_logger):
    """
    Комплексна перевірка:
    1. Якщо статус ЄРДР — він НЕ затирається, але інші поля оновлюються.
    2. Якщо статус інший (наприклад, 'Не призначено') — статус ПЕРЕЗАПИСУЄТЬСЯ новими даними.
    """
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    try:
        # --- СЦЕНАРІЙ 1: Захист ЄРДР (вже перевірений нами) ---
        pib_protected = "Захищений Стус Васильович"
        base_erdr = {
            COLUMN_NAME: pib_protected,
            COLUMN_ID_NUMBER: "3344556677",
            COLUMN_BIRTHDAY: "15.06.1985",
            COLUMN_DESERTION_DATE: "10.10.2023",
            COLUMN_REVIEW_STATUS: REVIEW_STATUS_ERDR,
            COLUMN_TZK_REGION: "Київська область",
            COLUMN_MIL_UNIT: config.DESERTER_TAB_NAME
        }
        processor.upsert_record([base_erdr])

        # Спроба оновити (змінити статус на ASSIGNED та оновити регіон/номери)
        update_erdr = base_erdr.copy()
        update_erdr[COLUMN_REVIEW_STATUS] = REVIEW_STATUS_ASSIGNED
        update_erdr[COLUMN_TZK_REGION] = "Львівська область"
        update_erdr[COLUMN_DBR_NUMBER] = '642/4444'

        processor.upsert_record([update_erdr])

        row_1 = 2
        status_col = processor.column_map.get(COLUMN_REVIEW_STATUS.lower())
        region_col = processor.column_map.get(COLUMN_TZK_REGION.lower())
        dbr_col = processor.column_map.get(COLUMN_DBR_NUMBER.lower())

        assert processor.sheet.range((row_1, status_col)).value == REVIEW_STATUS_ERDR, "ЄРДР МАЄ зберегтися!"
        assert processor.sheet.range((row_1, region_col)).value == "Львівська область", "Регіон МАЄ оновитися!"
        assert processor.sheet.range((row_1, dbr_col)).value == '642/4444', "DBR МАЄ оновитися!"

        # --- СЦЕНАРІЙ 2: Звичайний статус (Перезапис дозволено) ---
        pib_normal = "Звичайний Петренко Петро"
        base_normal = {
            COLUMN_NAME: pib_normal,
            COLUMN_ID_NUMBER: "9988776655",
            COLUMN_BIRTHDAY: "20.05.1990",
            COLUMN_DESERTION_DATE: "12.12.2023",
            COLUMN_REVIEW_STATUS: REVIEW_STATUS_NOT_ASSIGNED,
            COLUMN_TZK_REGION: "Одеська область",
            COLUMN_MIL_UNIT: config.DESERTER_TAB_NAME
        }
        processor.upsert_record([base_normal])

        # Отримуємо номер рядка для другого запису
        row_2 = 3

        # Дані для оновлення
        update_normal = base_normal.copy()
        update_normal[COLUMN_REVIEW_STATUS] = REVIEW_STATUS_ASSIGNED  # Має змінитись!
        update_normal[COLUMN_TZK_REGION] = "Полтавська область"

        processor.upsert_record([update_normal])

        actual_status_2 = processor.sheet.range((row_2, status_col)).value
        actual_region_2 = processor.sheet.range((row_2, region_col)).value

        assert actual_status_2 == REVIEW_STATUS_ASSIGNED, \
            f"Статус МАВ змінитись на {REVIEW_STATUS_ASSIGNED}, але залишився {actual_status_2}"

        assert actual_region_2 == "Полтавська область", "Регіон МАВ оновитися"

    finally:
        processor.close()