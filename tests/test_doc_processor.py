import pytest
import os
from pathlib import Path
from processing.DocProcessor import DocProcessor
from dics.deserter_xls_dic import *

class MockWorkflow:
    """Заглушка для workflow, щоб збирати статистику без бота"""

    def __init__(self):
        self.stats = type('Stats', (), {
            'attachmentWordProcessed': 0,
            'attachmentPDFProcessed': 0,
            'doc_names': []
        })


@pytest.fixture
def processor_factory():
    """Фабрика для створення процесора з різними файлами"""

    def _create_processor(file_name):
        # Шлях до тестових файлів у папці tests/data
        base_path = Path(__file__).parent / "data" / file_name
        workflow = MockWorkflow()
        return DocProcessor(workflow, str(base_path))

    return _create_processor


def test_process_doc_fedorov(processor_factory):
    # Тестуємо реальний кейс Федорова (СЗЧ)
    filename = "25.01.2026 СЗЧ з РБпНС ББпС Федоров _доповідь.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) > 0

    fields = result[0]

    # 1. Загальні дані та ідентифікація
    assert fields[COLUMN_NAME] == "ФЕДОРОВ Олександр Вікторович"
    assert fields[COLUMN_TITLE] == "солдат"
    assert fields[COLUMN_ID_NUMBER] == "3286702637"
    assert fields[COLUMN_BIRTHDAY] == "12/26/89"  # Згідно вашого формату m/d/yy

    # 2. Військова служба та підрозділ
    assert fields[COLUMN_SUBUNIT] == "ББпС"
    assert fields[COLUMN_SERVICE_TYPE] == "призовом"
    assert fields[COLUMN_MIL_UNIT] == "А0224"
    assert fields[COLUMN_TZK] == "Олександрійським РТЦК та СП"
    assert fields[COLUMN_ENLISTMENT_DATE] == "11/22/25"
    assert fields[COLUMN_SERVICE_DAYS] == 64

    # 3. Обставини СЗЧ
    assert fields[COLUMN_DESERTION_DATE] == "1/25/26"
    assert fields[COLUMN_DESERTION_PLACE] == "РВБЗ"
    assert fields[COLUMN_DESERTION_REGION] == "Шахтарське Дніпропетровської області"
    assert "ФЕДОРОВ Олександр Вікторович" in fields[COLUMN_DESERT_CONDITIONS]
    assert "самовільно залишив" in fields[COLUMN_DESERT_CONDITIONS]

    # 4. Контакти та адреса
    assert fields[COLUMN_PHONE] == "0680773315"
    assert fields[COLUMN_ADDRESS] == "Кіровоградська область, Олександрійський район, м. Олександрія, вул. Дружби 8, кв. 8"

    # 5. Специфічні умови (немає "був присутній" - дата порожня)
    assert fields[COLUMN_RETURN_DATE] == ""

    # 6. Виконавець
    assert fields[COLUMN_EXECUTOR] == "МОГУТОВ Ігор Миколайович"

'''def test_extract_military_subunit_from_filename(processor_factory):
    # Перевірка логіки витягування підрозділу з назви файлу з підкресленнями
    filename = "04.02.2026_СЗЧ_3_АЕМР_АЕМБ_ЄФРЕМОВ.docx"
    processor = processor_factory(filename)

    # Викликаємо метод напряму для тесту
    res = processor._extract_military_subunit("якийсь текст", file_name=filename)
    assert "3 АЕМР" in res


def test_calculate_service_days(processor_factory):
    processor = processor_factory("any.docx")
    # 20.07.2025 до 04.02.2026
    # Формат у вас m/d/yy (згідно з вашим format_to_excel_date)
    days = processor._calculate_service_days("7/20/25", "2/4/26")
    assert days > 190


def test_rtzk_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "Призваний Слов'янським ТЦК 10.09.2025. РНОКПП 1234567890"
    res = processor._extract_rtzk(text)
    assert "Слов'янським ТЦК" in res'''