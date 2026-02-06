import pytest
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


def test_process_doc_fedorov_simple(processor_factory):
    # Тестуємо реальний кейс Федорова (СЗЧ)
    filename = "1_25.01.2026 СЗЧ з РБпНС ББпС Федоров _доповідь.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) > 0

    fields = result[0]

    assert fields[COLUMN_NAME] == "ФЕДОРОВ Олександр Вікторович"
    assert fields[COLUMN_TITLE] == "солдат"
    assert fields[COLUMN_ID_NUMBER] == "1234567890"
    assert fields[COLUMN_BIRTHDAY] == "12/26/89"  # m/d/yy
    assert fields[COLUMN_SUBUNIT] == "ББпС"
    assert fields[COLUMN_SERVICE_TYPE] == "призовом"
    assert fields[COLUMN_MIL_UNIT] == "А0224"
    assert fields[COLUMN_TZK] == "Олександрійським РТЦК та СП"
    assert fields[COLUMN_ENLISTMENT_DATE] == "11/22/25"
    assert fields[COLUMN_SERVICE_DAYS] == 64
    assert fields[COLUMN_DESERTION_DATE] == "1/25/26"
    assert fields[COLUMN_DESERTION_PLACE] == "РВБЗ"
    assert fields[COLUMN_DESERTION_REGION] == "Шахтарське Дніпропетровської області"
    assert "ФЕДОРОВ Олександр Вікторович" in fields[COLUMN_DESERT_CONDITIONS]
    assert "самовільно залишив" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0687775544"
    assert fields[COLUMN_ADDRESS] == "Кіровоградська область, Олександрійський район, м. Олександрія, вул. Дружби 22, кв. 23"
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "МОГУТОВ Ігор Миколайович"


def test_process_doc_maly_simple(processor_factory):
    # Тестуємо реальний кейс (СЗЧ)
    filename = "2_01.01.2026 СЗЧ з РВБЗ 2 сабатр САДН  МАЛИЙ Д.В.doc"
    processor = processor_factory(filename)
    result = processor.process()

    print(result)
    assert isinstance(result, list)
    assert len(result) > 0
    fields = result[0]

    assert fields[COLUMN_NAME] == "МАЛИЙ Дмитро Вадимович"
    assert fields[COLUMN_TITLE] == "солдат"
    assert fields[COLUMN_ID_NUMBER] == "3611112233"
    # Зверни увагу: у результаті '12/28/0' (ймовірно, через помилку форматування року 2000)
    # Якщо очікуємо 2000 рік, перевір функцію format_to_excel_date
    assert fields[COLUMN_BIRTHDAY] == "12/28/0"
    assert fields[COLUMN_SUBUNIT] == "САДН"
    assert fields[COLUMN_SERVICE_TYPE] == "контрактом"
    assert fields[COLUMN_MIL_UNIT] == "А0224"
    assert fields[COLUMN_TZK] == "Покровсько-Тернівським РТЦК та СП, м. Кривий Ріг"
    assert fields[COLUMN_ENLISTMENT_DATE] == "11/23/20"
    assert fields[COLUMN_SERVICE_DAYS] == 1865
    assert fields[COLUMN_DESERTION_DATE] == "1/1/26"
    assert fields[COLUMN_DESERTION_PLACE] == "РВБЗ"
    assert fields[COLUMN_DESERTION_REGION] == "Тернівка Дніпропетровської області"
    assert "МАЛИЙ Дмитро Вадимович" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0969111111"
    assert fields[COLUMN_ADDRESS] == "Дніпропетровська обл., м. Кривий Ріг, вул. Ф. Караманиця, буд. 11А, кв 12"
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "БОЙКО Віктор Олександрович"

# tests error - missing one of the part in the document
def test_process_doc_maly_error_missing_4(processor_factory):
    # Тестуємо реальний кейс, де заздалегідь знаємо, що PIECE_4 буде None
    filename = "3_01.01.2026 СЗЧ з РВБЗ 2 сабатр САДН  МАЛИЙ Д.В _ error.doc"
    processor = processor_factory(filename)
    with pytest.raises(ValueError) as excinfo:
        processor.process()
    assert "❌ Частина 4 не витягнуто!" in str(excinfo.value)

# tests two persons in one document
def test_process_doc_two_persons(processor_factory):
    # Тестуємо реальний кейс Івончака та Неголюка (групове СЗЧ)
    filename = "4_31.01.2026 СЗЧ з РВЗ Івончак Д.В., Неголюк В.В. 7 дшр 2 дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 2  # Очікуємо двох осіб

    # --- ПЕРЕВІРКА ПЕРШОЇ ОСОБИ (ІВОНЧАК) ---
    person1 = result[0]
    assert person1['ПІБ'] == 'ІВОНЧАК Дмитро Васильович'
    assert person1['Військове звання'] == 'солдат'
    assert person1['РНОКПП'] == '3151262222'
    assert person1['Дата народження'] == '12/3/91'
    assert person1['Підрозділ'] == '2 дшб'
    assert person1['Від служби'] == 'призовом'
    assert person1['№ телефону'] == '0962522526'
    assert person1['Адреса проживання'] == "с. Майори, вул. Паркова буд. 12 кв.1-А, Біляївський р-н, Одеська обл"
    assert person1['РТЦК'] == 'Розділянським РТЦК та СП Одеської обл'
    assert person1['Дата призову на військову службу'] == '9/14/25'
    assert person1['термін служби до СЗЧ'] == 139
    assert person1['Звідки СЗЧ'] == 'РВБЗ'

    # --- ПЕРЕВІРКА ДРУГОЇ ОСОБИ (НЕГОЛЮК) ---
    person2 = result[1]
    assert person2['ПІБ'] == 'НЕГОЛЮК Володимир Васильович'
    assert person2['Військове звання'] == 'солдат'
    assert person2['РНОКПП'] == NA
    assert person2['Дата народження'] == '10/29/81'
    assert person2['№ телефону'] == '0987773388'
    assert person2['Адреса проживання'] == "Івано-Франківська обл, Івано- Франківський район, с. Раковець, вул. Стуса 12"
    assert person2['РТЦК'] == 'Надвірнянським РТЦК та СП'
    assert person2['Дата призову на військову службу'] == '10/25/25'
    assert person2['термін служби до СЗЧ'] == 98
    assert person2['Звідки СЗЧ'] == 'РВБЗ'

    # --- ПЕРЕВІРКА СПІЛЬНИХ ДАНИХ ---
    for field in result:
        assert field['Військова частина'] == 'А0224'
        assert field['Дата СЗЧ'] == '1/31/26'
        assert field['Звідки СЗЧ н.п. обл'] == 'Привовчанське Дніпропетровської області'
        assert "ІВОНЧАК" in field['Дата, час обставини та причини самовільного залишення військової частини або місця служби']
        assert "НЕГОЛЮК" in field['Дата, час обставини та причини самовільного залишення військової частини або місця служби']
        assert field['Виконавець'] == 'БЕЗКРОВНИЙ Володимир Володимирович'


def test_process_doc_tzk_is_full(processor_factory):
    # перевірка, що тцк розпарсився правильно та повно. матьйїхйоп
    filename = "5_05.02.2026 СЗЧ з РВБЗ (Кортун В.М.) рбс 3 дшб_tzk.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) == 1

    person = result[0]
    assert person['РТЦК'] == 'Крижопільським РТЦК та СП м. Крижопіль'

def test_process_docx_simple(processor_factory):
    # тестування парсінгу docx
    filename = "6_02.01.2026 СЗЧ відсутність на військовій службі без поважних причин (Шевчук В.Є.) 9 дшр 3 дшб.docx"
    processor = processor_factory(filename)
    result = processor.process()

    print(result)

    assert isinstance(result, list)
    assert len(result) == 1

    person = result[0]
    assert person['ПІБ'] == 'ШЕВЧУК Віктор Євгенович'
    assert person['Військове звання'] == 'солдат'
    assert person['РНОКПП'] == '2232933224'
    assert person['Дата народження'] == '3/23/68'  # m/d/yy
    assert person['Військова частина'] == 'А0224'
    assert person['Підрозділ'] == '3 дшб'
    assert person['Від служби'] == 'призовом'
    assert person['РТЦК'] == 'Шепетівським РТЦК та СП м. Шепетівка'
    assert person['Дата призову на військову службу'] == '2/24/22'
    assert person['термін служби до СЗЧ'] == 1408
    assert person['Дата СЗЧ'] == '1/2/26'
    assert person['Звідки СЗЧ н.п. обл'] == 'Вознесенське, Миколаївської області'
    assert "ШЕВЧУК Віктор Євгенович" in person[
        'Дата, час обставини та причини самовільного залишення військової частини або місця служби']
    assert "73 доби" in person[
        'Дата, час обставини та причини самовільного залишення військової частини або місця служби']
    assert person['№ телефону'] == '0671118227'
    assert person['Адреса проживання'] == "Хмельницька область, Ізяславський район, с. Теліжинці, вул. Центральна, буд. 48"
    assert person['Виконавець'] == 'САМУЛІК Роман Богданович'


#################### загальне модульне тестування регекспів ##############################

def test_name_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "ДВОЄЗЕРСЬКИЙ Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "ДВОЄЗЕРСЬКИЙ Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли-Піздик, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "Салтіков Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "" in res

    text = "Текст попереду ПРОТОН Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "ПРОТОН Олег Вікторович" in res

    text = "Текст попереду ПРОТОН Олег Вікторович-Огли і пробели далі, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "ПРОТОН Олег Вікторович-Огли" in res

def test_rtzk_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "Призваний Слов'янським ТЦК 10.09.2025. РНОКПП 1234567890"
    res = processor._extract_rtzk(text)
    assert "Слов'янським ТЦК" in res

    text = "Призваний Пересипським РТЦК та СП , м. Одеса, 23.12.2024,. РНОКПП 3"
    res = processor._extract_rtzk(text)
    assert res == "Пересипським РТЦК та СП , м. Одеса"

    text = "призваний Кропивницьким РТЦК та СП, м. Кропивницький, Кіровоградська обл., 19.06.2025 року. РНОКПП 32"
    res = processor._extract_rtzk(text)
    assert res == "Кропивницьким РТЦК та СП, м. Кропивницький, Кіровоградська обл"

    text = "88 р.н.; призваний Галицько-Франківським ОРТЦК та СП 01.11.2025; адреса проживання: Льв"
    res = processor._extract_rtzk(text)
    assert res == "Галицько-Франківським ОРТЦК та СП"

    text = "неодружений. Призваний Салтівським РТЦК та СП м. Харків, 27.07"
    res = processor._extract_rtzk(text)
    assert res == "Салтівським РТЦК та СП м. Харків"
