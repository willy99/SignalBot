import pytest
from service.processing.processors.ExcelProcessor import ExcelProcessor
from dics.deserter_xls_dic import COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_BIRTHDAY, COLUMN_DESERTION_DATE, COLUMN_INCREMENTAL, COLUMN_MIL_UNIT, COLUMN_TZK_REGION
from config import DESERTER_TAB_NAME


def test_upsert_inserts_new_record(temp_excel_file, mock_logger):
    """Перевіряємо, чи додається новий запис, якщо його ще немає в базі"""
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    new_record = {
        COLUMN_NAME: "Бандера Степан Андрійович",
        COLUMN_ID_NUMBER: "1234567890",
        COLUMN_BIRTHDAY: "01.01.1909",
        COLUMN_DESERTION_DATE: "01.10.2023",
        COLUMN_MIL_UNIT: DESERTER_TAB_NAME
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
        COLUMN_MIL_UNIT: DESERTER_TAB_NAME
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