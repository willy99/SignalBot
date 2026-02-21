import pytest
from pathlib import Path
from processing.DocProcessor import DocProcessor
from dics.deserter_xls_dic import *
from processing.parsers.MLParser import MLParser
import config
from storage.LoggerManager import LoggerManager

class MockWorkflow:
    """Заглушка для workflow, щоб збирати статистику без бота"""

    def __init__(self):
        self.log_manager = LoggerManager()
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
        return DocProcessor(workflow, str(base_path), file_name)

    return _create_processor


def test_process_doc_fedorov_simple(processor_factory):
    # Тестуємо реальний кейс Федорова (СЗЧ)
    filename = "01_25.01.2026 СЗЧ з РБпНС ББпС Федоров _доповідь.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) > 0

    fields = result[0]

    assert fields[COLUMN_NAME] == "ФЕДОРОВ Олександр Вікторович"
    assert fields[COLUMN_TITLE] == "солдат"
    assert fields[COLUMN_ID_NUMBER] == "1234567890"
    assert fields[COLUMN_BIRTHDAY] == "26.12.1989"
    assert fields[COLUMN_SUBUNIT] == "ББС"
    assert fields[COLUMN_SERVICE_TYPE] == "призивом"
    assert fields[COLUMN_MIL_UNIT] == "А0224"
    assert fields[COLUMN_TZK] == "Олександрійським РТЦК та СП в м. Олександрія, Кіровоградської обл"
    assert fields[COLUMN_TZK_REGION] == "Кіровоградська область"
    assert fields[COLUMN_ENLISTMENT_DATE] == "22.11.2025"
    assert fields[COLUMN_SERVICE_DAYS] == 64
    assert fields[COLUMN_DESERTION_DATE] == "25.01.2026"
    assert fields[COLUMN_DESERTION_PLACE] == "РВБЗ"
    assert fields[COLUMN_DESERTION_REGION] == "Шахтарське Дніпропетровської області"
    assert "ФЕДОРОВ Олександр Вікторович" in fields[COLUMN_DESERT_CONDITIONS]
    assert "самовільно залишив" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0687775544"
    assert "Кіровоградська область, Олександрійський район, м. Олександрія, вул. Дружби 22, кв. 23" in fields[COLUMN_ADDRESS]
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "МОГУТОВ Ігор Миколайович"


def test_process_doc_maly_simple(processor_factory):
    # Тестуємо реальний кейс (СЗЧ)
    filename = "02_01.01.2026 СЗЧ з РВБЗ 2 сабатр САДН  МАЛИЙ Д.В.doc"
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
    assert fields[COLUMN_BIRTHDAY] == "28.12.2000"
    assert fields[COLUMN_SUBUNIT] == "САДн"
    assert fields[COLUMN_SERVICE_TYPE] == "контрактом"
    assert fields[COLUMN_MIL_UNIT] == "А0224"
    assert fields[COLUMN_TZK] == "Покровсько-Тернівським РТЦК та СП, м. Кривий Ріг, Дніпропетровської області"
    assert fields[COLUMN_TZK_REGION] == "Дніпропетровська область"
    assert fields[COLUMN_ENLISTMENT_DATE] == "23.11.2020"
    assert fields[COLUMN_SERVICE_DAYS] == 1865
    assert fields[COLUMN_DESERTION_DATE] == "01.01.2026"
    assert fields[COLUMN_DESERTION_PLACE] == "РВБЗ"
    assert fields[COLUMN_DESERTION_REGION] == "Тернівка Дніпропетровської області"
    assert "МАЛИЙ Дмитро Вадимович" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0969111111"
    assert "Дніпропетровська обл., м. Кривий Ріг, вул. Ф. Караманиця, буд. 11А, кв 12" in fields[COLUMN_ADDRESS]
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "БОЙКО Віктор Олександрович"
    assert fields[COLUMN_DESERTION_TYPE] == 'СЗЧ'

# tests error - missing one of the part in the document
def test_process_doc_maly_error_missing_4(processor_factory):
    # Тестуємо реальний кейс, де заздалегідь знаємо, що PIECE_4 буде None
    filename = "03_01.01.2026 СЗЧ з РВБЗ 2 сабатр САДН  МАЛИЙ Д.В _ error.doc"
    processor = processor_factory(filename)
    with pytest.raises(ValueError) as excinfo:
        processor.process()
    assert "❌ Частина 4 не витягнуто!" in str(excinfo.value)

# tests two persons in one document
def test_process_doc_two_persons(processor_factory):
    # Тестуємо реальний кейс Івончака та Неголюка (групове СЗЧ)
    filename = "04_31.01.2026 СЗЧ з РВЗ Івончак Д.В., Неголюк В.В. 7 дшр 2 дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 2  # Очікуємо двох осіб

    # --- ПЕРЕВІРКА ПЕРШОЇ ОСОБИ (ІВОНЧАК) ---
    person1 = result[0]
    assert person1[COLUMN_NAME] == 'ІВОНЧАК Дмитро Васильович'
    assert person1[COLUMN_TITLE] == 'солдат'
    assert person1[COLUMN_ID_NUMBER] == '3151262222'
    assert person1[COLUMN_BIRTHDAY] == '03.12.1991'
    assert person1[COLUMN_SUBUNIT] == '2 дшб'
    assert person1[COLUMN_SERVICE_TYPE] == 'призивом'
    assert person1[COLUMN_PHONE] == '0962522526'
    assert person1[COLUMN_ADDRESS] == "с. Майори, вул. Паркова буд. 12 кв.1-А, Біляївський р-н, Одеська обл."
    assert person1[COLUMN_TZK] == 'Розділянським РТЦК та СП Одеської області'
    assert person1[COLUMN_TZK_REGION] == "Одеська область"
    assert person1[COLUMN_ENLISTMENT_DATE] == '14.09.2025'
    assert person1[COLUMN_SERVICE_DAYS] == 139
    assert person1[COLUMN_DESERTION_PLACE] == 'РВБЗ'

    # --- ПЕРЕВІРКА ДРУГОЇ ОСОБИ (НЕГОЛЮК) ---
    person2 = result[1]
    assert person2[COLUMN_NAME] == 'НЕГОЛЮК Володимир Васильович'
    assert person2[COLUMN_TITLE] == 'солдат'
    assert person2[COLUMN_ID_NUMBER] == NA
    assert person2[COLUMN_BIRTHDAY] == '29.10.1981'
    assert person2[COLUMN_PHONE] == '0987773388'
    assert "Івано-Франківська обл, Івано-Франківський район, с. Раковець, вул. Стуса 12" in person2[COLUMN_ADDRESS]
    assert person2[COLUMN_TZK] == 'Надвірнянським РТЦК та СП Івано-Франківської області'
    assert person2[COLUMN_TZK_REGION] == "Івано-Франківська область"
    assert person2[COLUMN_ENLISTMENT_DATE] == '25.10.2025'
    assert person2[COLUMN_SERVICE_DAYS] == 98
    assert person2[COLUMN_DESERTION_PLACE] == 'РВБЗ'
    assert "31.01.2026 о 16:00 під час перевірки особового складу 7 десантно-штурмової роти 2 десантно-штурмового батальйону командиром підрозділу капітаном БЕШЛЯГОЮ Р.В. було виявлено відсутність військовослужбовців солдата ІВОНЧАКА Дмитра Васильовича та солдата НЕГОЛЮКА Володимира Васильовича, які самовільно залишили район зосередження 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224 поблизу н.п. Привовчанське Дніпропетровської області" in person2[COLUMN_DESERT_CONDITIONS]
    assert "31.01.2026 року від командира 7 десантно-штурмової роти 2 десантно-штурмового батальйону надійшла доповідь про факт самовільного залишення району виконання завдання за призначенням військовослужбовця військової частини А0224 солдата ІВОНЧАКА Дмитра Васильовича та солдата НЕГОЛЮКА Володимира Васильовича (без зброї" not in person2[COLUMN_DESERT_CONDITIONS]

    # --- ПЕРЕВІРКА СПІЛЬНИХ ДАНИХ ---
    for field in result:
        assert field[COLUMN_MIL_UNIT] == 'А0224'
        assert field[COLUMN_DESERTION_DATE] == '31.01.2026'
        assert field[COLUMN_DESERTION_REGION] == 'Привовчанське Дніпропетровської області'
        assert "ІВОНЧАК" in field[COLUMN_DESERT_CONDITIONS]
        assert "НЕГОЛЮК" in field[COLUMN_DESERT_CONDITIONS]
        assert field[COLUMN_EXECUTOR] == 'БЕЗКРОВНИЙ Володимир Володимирович'

def test_process_doc_tzk_is_full(processor_factory):
    # перевірка, що тцк розпарсився правильно та повно. матьйїхйоп
    filename = "05_05.02.2026 СЗЧ з РВБЗ (Гавнов В.М.) рбс 3 дшб_tzk.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) == 1

    person = result[0]
    assert person[COLUMN_TZK] == 'Крижопільським РТЦК та СП м. Крижопіль'
    assert person[COLUMN_TZK_REGION] == "Вінницька область"

def test_process_docx_simple(processor_factory):
    # тестування парсінгу docx
    filename = "06_02.01.2026 СЗЧ відсутність на військовій службі без поважних причин (Гавнов В.Є.) 9 дшр 3 дшб.docx"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) == 1

    person = result[0]
    assert person[COLUMN_NAME] == 'ГАВНОВ Віктор Євгенович'
    assert person[COLUMN_TITLE] == 'солдат'
    assert person[COLUMN_ID_NUMBER] == '2232933224'
    assert person[COLUMN_BIRTHDAY] == '23.03.1968'  # m/d/yy
    assert person[COLUMN_MIL_UNIT] == 'А0224'
    assert person[COLUMN_SUBUNIT] == '3 дшб'
    assert person[COLUMN_SERVICE_TYPE] == 'призивом'
    assert person[COLUMN_TZK] == 'Шепетівським РТЦК та СП м. Шепетівка'
    assert person[COLUMN_ENLISTMENT_DATE] == '24.02.2022'
    assert person[COLUMN_SERVICE_DAYS] == 1408
    assert person[COLUMN_DESERTION_DATE] == '02.01.2026'
    assert person[COLUMN_DESERTION_REGION] == 'Вознесенське, Миколаївської області'
    assert "З 01.08.2025 по 17.10.2025 був на стаціонарному лікуванні в КНП “Хмільницька центральна лікарня”. 30.12.2025 прибув до пункту постійної дислокації військової частини А0224 (н.п. Вознесенське, Миколаївської області" in person[
        COLUMN_DESERT_CONDITIONS]
    assert "З 18.10.2025 по 29.12.2025 солдат ГАВНОВ Віктор Євгенович був відсутній на військовій службі, підтверджуючих документів не надав (відсутній на військовій службі 73 доби)" in person[
        COLUMN_DESERT_CONDITIONS]
    assert person[COLUMN_PHONE] == '0671118227'
    assert person[COLUMN_ADDRESS] == "Хмельницька область, Ізяславський район, с. Теліжинці, вул. Центральна, буд. 48."
    assert person[COLUMN_EXECUTOR] == 'САМУЛІК Роман Богданович'
    assert person[COLUMN_RETURN_DATE] == '30.12.2025'

def test_return_date(processor_factory):
    filename = "07_09.02.2026 повернення після СЗЧ 5 дшр 2 дшб ДУБ Є.М..doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    person = result[0]

    assert person[COLUMN_RETURN_DATE] == '09.02.2026' # todo - винно бути -08.02.2026
    assert person[COLUMN_DESERTION_DATE] == ''
    assert person[COLUMN_DESERTION_PLACE] == ''

def test_not_a_desertion_case(processor_factory):
    filename = "08_12.02.2026 Травмування  (КАША О.М.) МР.docx"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 0


def test_desertion_date_is_correct(processor_factory):
    filename = "09_15.02.2026 СЗЧ з лікування БУЙНОВ С.В. 3дшр 1дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_RETURN_DATE] is None
    assert person[COLUMN_DESERTION_DATE] == '13.02.2026'  # винно бути не 15.02.2026!



#################### загальне модульне тестування регекспів ##############################

def test_military_unit(processor_factory):
    processor = processor_factory("any.docx")
    text = "ДОПОВІДЬ про факт не прибуття до місця несення служби військовослужбовця військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України"
    res = processor._extract_mil_unit(text)
    assert res == 'А0224'

    text = "ДОПОВІДЬ про факт самовільного залишення району виконання завдання військовослужбовцями військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України"
    res = processor._extract_mil_unit(text)
    assert res == 'А0224'

    text = "ДОПОВІДЬ про факт самовільного залишення району виконання завдання за призначенням військовослужбовців зарахованих до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України "
    res = processor._extract_mil_unit(text)
    assert res == 'А7018'


def test_name_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "ГАВНОВЄЗЕРСЬКИЙ Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "ГАВНОВЄЗЕРСЬКИЙ Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли-Піздик, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "Салтіков Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "" in res

    text = "Текст попереду ПРОТОН Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = processor._extract_name(text)
    assert "ПРОТОН Олег Вікторович" in res

    text = "Текст попереду ПРОТОН Олег Вікторович-Огли і пробели далі, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_name(text)
    assert "ПРОТОН Олег Вікторович-Огли" in res

    text = "ГАВНОВ Назар-Іван Васильович солдат, військовослужбовець військової служби за призовом,  колишній гранатометник 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, "
    res = processor._extract_name(text)
    assert "ГАВНОВ Назар-Іван Васильович" in res

def test_title_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "ПУНДІК Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = processor._extract_title(text)
    assert "старший солдат" in res
    res = processor._extract_title_2(res)
    assert "солдат" in res

    text = "ПУНДІКА Олега Вікторовича, старшого солдату, військовослужбовець військової служби за призовом, "
    res = processor._extract_title(text)
    assert "старший солдат" in res

    text = "ПУНДІКУ Олегу Вікторовичу, солдату, військовослужбовець військової служби за призовом, "
    res = processor._extract_title(text)
    assert "солдат" in res

    text = "ПУНДІК Олег Вікторович, військовослужбовець військової служби за призовом, "
    res = processor._extract_title(text)
    assert "солдат" in res

    text = "БОЛВАН Руслан Олександрович, військовослужбовець військової служби за призовом, аааа. Близькі родичі: Батько: БОЛВАН Олександр Владиславович, 23.06.1965 р.н., м. Київ, тел. +380993955598; Мати: БОЛВАН Світлана Сергіївна, 05.05.1970 р.н., смт. Капітанівка, "
    res = processor._extract_title(text)
    assert "солдат" in res

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

    text = "на, неодружений. Призваний Покровським РТЦК та СП, Дніпропетровської області, 06.05.2025 року. РНОКПП 333"
    res = processor._extract_rtzk(text)
    assert res == "Покровським РТЦК та СП, Дніпропетровської області"

    text = "неодружений. Призваний Салтівським ОМТЦК та СП м. Харків, 27.07"
    res = processor._extract_rtzk(text)
    assert res == "Салтівським ОМТЦК та СП м. Харків"

    text = "року народження, українець, освіта вища, неодружений. Призваний Центральним РТЦК та СП в м. Миколаїв, Миколаївської області, 06.12.2025. РНОКПП 36"
    res = processor._extract_rtzk(text)
    assert res == "Центральним РТЦК та СП в м. Миколаїв, Миколаївської області"

    # виправлення рцтк на ртцк
    text = "БУЙКО Богдан Васильович, старший сержант, військовослужбовець військової служби за призовом, колишній гранатометник 1 десантно-штурмового відділення 1 десантно-штурмового взводу 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 14.05.1979 року народження, українець, освіта середня-спеціальна, Авіаційна школа м. Гайсин у 1997 році, одружений. Призваний Сихівським  РЦТК та СП Львівської області, 21.04.2025 року. РНОКПП 2811111118. Паспорт КА 111111. Номер мобільного телефону (067) 1111111"
    res = processor._extract_rtzk(text)
    assert res == "Сихівським РТЦК та СП Львівської області"

    text = "БУЙКО Юрій Станіславович, військовослужбовець військової служби за призовом, зарахований до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224, 31.10.1975 року народження, Українець, освіта середня, розлучений. Призваний Покровсько-Тернівським РТЦК та СП м. Кривий Ріг 24.02.2022 року. "
    res = processor._extract_rtzk(text)
    assert res == "Покровсько-Тернівським РТЦК та СП м. Кривий Ріг"

    text = "БУЙНОВ Антон Олександрович, солдат, військовослужбовець військової служби за призовом, гранатометник 1 аеромобільного відділення 1 аеромобільного взводу 3 аеромобільної роти аеромобільного батальйону військової частини А0224, 22.11.1985 року народження, українець, освіта середня, не одружений. Призваний 4 відділ Миколаївського РТЦК та СП м. Миколаїв, 27.11.2025 року. Номер мобільного телефону +380611111119."
    res = processor._extract_rtzk(text)
    assert res == "4 відділ Миколаївського РТЦК та СП м. Миколаїв"

    text = "БУЙКО Олександр Володимирович, військовослужбовець військової служби за призовом, зарахований до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224, 13.11.1983 року народження, Українець, освіта середня, цивільний шлюб. Призваний Новокодацьким РТЦК та СП м. Дніпра 06.12.2024 року. "
    res = processor._extract_rtzk(text)
    assert res == "Новокодацьким РТЦК та СП м. Дніпра"

    text = "БУЙКО Олексій Миколайович, майстер-сержант, військовослужбовець військової служби за контрактом, командир господарчого відділення самохідного артилерійського дивізіону військової частини А0224, 22.03.1982 року народження, освіта середня, одружений. Призваний Новоодеським РВК Миколаївської обл., 04.02.2013 року. РНОКПП 3003117373, номер мобільного телефону 0687849466. "
    res = processor._extract_rtzk(text)
    assert res == "Новоодеським РВК Миколаївської обл"

    text = "Призваний: Миколаївським МТЦК та СП, 02.09.2025, РНОКПП: 3344514975"
    res = processor._extract_rtzk(text)
    assert res == "Миколаївським МТЦК та СП"

    text = "Призваний 28.08.2024 року Вознесенським РТЦК та СП м. Вознесенськ Миколаївської області."
    res = processor._extract_rtzk(text)
    assert res == "Вознесенським РТЦК та СП м. Вознесенськ Миколаївської області"

    text = "розлучений. Призваний  20.05.2025, Оболонським РТЦК , 3107111114. Н"
    res = processor._extract_rtzk(text)
    assert res == "Оболонським РТЦК"


def test_rtzk_region_extraction(processor_factory):
    processor = processor_factory("any.docx")

    text = "Призваний Центральним РТЦК та СП м. Київ 06.12.2024 року. "
    res = processor._extract_rtzk_region(text)
    assert "Київська область" in res

    text = "Призваний Київським РТЦК та СП"
    res = processor._extract_rtzk_region(text)
    assert "Київська область" in res

    text = "Призваний Центральним РТЦК та СП м. Обухів, Київська обл."
    res = processor._extract_rtzk_region(text)
    assert "Київська область" in res

    text = "Призваний Новокодацьким РТЦК та СП м. Дніпра 06.12.2024 року. "
    res = processor._extract_rtzk_region(text)
    assert "Дніпропетровська область" in res

    text = "Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52"
    res = processor._extract_rtzk_region(text)
    assert "Кіровоградська область" in res

    text = "Чернівецька обл., м. Олександрія, вул. Сумська, буд. 16 кв. 52"
    res = processor._extract_rtzk_region(text)
    assert "Чернівецька область" in res

    text = "Кропивницьким РТЦК та СП, м. Кропивницький"
    res = processor._extract_rtzk_region(text)
    assert "Кіровоградська область" in res

    text = "Кропивницький МТЦК та СП."
    res = processor._extract_rtzk_region(text)
    assert "Кіровоградська область" in res

    text = "Кам’янський РТЦК та СП м. Кам’янка Дніпропетровської області"
    res = processor._extract_rtzk_region(text)
    assert "Дніпропетровська область" in res

    text = "Київський РТЦК та СП м. Одеса"
    res = processor._extract_rtzk_region(text)
    assert "Одеська область" in res

    text = "Дубинським РТЦК та СП Рівненської обл."
    res = processor._extract_rtzk_region(text)
    assert "Рівненська область" in res

    text = "Миколаївський РТЦК та СП"
    res = processor._extract_rtzk_region(text)
    assert "Миколаївська область" in res

    text = "місто Вінниця, вулиця Нагірна 21ж, квартира 21."
    res = processor._extract_rtzk_region(text)
    assert "Вінницька область" in res

def test_conscription_date(processor_factory):
    processor = processor_factory("any.docx")

    text = "БУЙНОВ Олег Леонідович, Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків. РНОКПП відомості не надано"
    res = processor._extract_conscription_date(text)
    assert res == NA

    text = "БУЙНОВ Сергій Володимирович, солдат, військовослужбовець військової служби за призовом, стрілець-номер обслуги 1 десантно-штурмового відділення 2 десантно-штурмового взводу 3 десантно-штурмової роти 1 десантно-штурмового батальйону військової частини А0224, 21.09.1981 року народження, українець, освіта фахова передвища (молодший спеціаліст), не одружений. Призваний  Вознесенським РТЦК та СП Миколаївської області, 11.11.2025. РНОКПП 2111111111. Паспорт 001111111, виданий 4831 31.08.2017. Номер мобільного телефону +380681111115"
    res = processor._extract_conscription_date(text)
    assert res == "11.11.2025"

    text = "БУЙНОВ Олег Леонідович, солдат, 23.07.1993 року народження, ВІН 010521111111111111104, ІПН 3111111110, паспорт 011111111 виданий 0510 від 01.11.2019 призваний 04.02.2026 Вінницьким ОМТЦК ти СП, закінчив Вінницький державний педагогічний університет у 2016р. вчитель фізкультури, номер мобільного телефону 0961111114. Адреса проживання військовослужбовця: м. Вінниця, вул. Покришкіна 11в. Близькі родичі: Батько НЕКЛЮДОВ Леонід Миколайович, тел. 0671111120"
    res = processor._extract_conscription_date(text)
    assert res == "04.02.2026"

    text = "БУЙНОВ Олег Леонідович, Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків, 25.10.2025 року. РНОКПП відомості не надано"
    res = processor._extract_conscription_date(text)
    assert res == "25.10.2025"




def test_address_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "телефону +38(096)-896-7925. Близькі родичі: Батьки померли. Адреса реєстрації військовослужбовця: Запорізька обл, м. Василівка, вул. Кірова буд. 25."
    res = processor._extract_address(text)
    assert res == 'Запорізька обл, м. Василівка, вул. Кірова буд. 25'

    text = "Батько: Моторко Анатолій Федорович, 1959 р.н., (063)-791-89-31. Адреса проживання військовослужбовця: Миколаївська обл, с. Федорівне, вул. Степова буд. 7."
    res = processor._extract_address(text)
    assert res == 'Миколаївська обл, с. Федорівне, вул. Степова буд. 7'

    text = "ГАВНОВ Юрій Азізович, військовослужбовець військової служби за мобілізацією, стрілець-снайпер 3 аеромобільного відділення 1 аеромобільного взводу 2 аеромобільної  роти аеромобільного батальйону, 21.08.1982 року народження, українець, освіта середня спеціальна. Призваний Олександрійським РТЦК та СП м. Кіровоградської обл., 17.12.2025 року, РНОКПП 3383322233, номер мобільного телефону 068-622-22-44. Адреса проживання військовослужбовця: Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52. Мати: ФІБЕРГ Марта Яківна, дані потребують уточнення. Дружина: ФІБЕРГ Катерина Валеріївна, тел. 067-964-02-74. А"
    res = processor._extract_address(text)
    assert res == 'Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52'

def test_phone_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "номер мобільного телефону (095) 64 73225. Адреса "
    res = processor._extract_phone(text)
    assert res == '0956473225'

    text = "номер мобільного телефону +380505184441. Близькі родичі:"
    res = processor._extract_phone(text)
    assert res == '0505184441'

def test_where_desertion_extraction(processor_factory):
    processor = processor_factory("any.docx")
    text = "30.01.2026 від тимчасово виконуючого обов’язки командира 4 аеромобільної роти аеромобільного батальйону надійшла доповідь про факт неповернення з лікування до району виконання завдання за призначенням військовослужбовця військової частини А0224 (без зброї)."
    file_name = '30.01.2026 СЗЧ з лікування ГАВНОВ Р.О. 4 аемр аемб.docx'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "05.02.2026 від командира аеромобільного батальйону надійшла доповідь про факт відсутності військовослужбовця військової частини А0224 в медичному закладі куди був спрямований на стаціонарне проходження військово-лікарської комісії з пункту тимчасового розташування підрозділу с. Вознесенське Миколаївської області."
    file_name = '05.02.2026 СЗЧ з лікування ГАВНОВ В.Є. 4 аемр аемб.docx'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "10.02.2026 року від командира 3 десантно-штурмового батальйону надійшла доповідь про факт неповернення з лікування до району виконання завдання за призначенням військовослужбовця військової частини А0224 солдата ГАВНОВА Миколи Анатолійовича. 10.02.2026року солдат ГАВНОВ Микола Анатолійович не повернувся з лікування до району виконання завдання за призначенням. Солдат ГАВНОВ Микола Анатолійович лікувався в Національному військово-медичному клінічному центрі госпіталю м. Київ з 28.01.2026 по 09.02.2026 року. На зв’язок не виходить документів, які підтверджують проходження лікування в інших медичних закладах не надав. До військової частини А0224 не повернувся. Пошук військовослужбовця в районі зосередження підрозділом в н.п. Українське Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме."
    file_name = '10.02.2026 СЗЧ неповернення з  лікування до РВБЗ (Гавнов М.А.) зрв 3 дшб(2)'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "11.02.2026 від командира 4 десантно-штурмової роти 1 десантно-штурмового батальйону надійшла доповідь про факт неповернення з лікування до військової частини військовослужбовцем військової частини А0224."
    file_name = '11.02.2026 СЗЧ неповернення 4дшр 1дшб ЩЕРБИНА А.В..docx'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "05.02.2026 від командира самохідного артилерійського дивізіону військової частини А0224 надійшла доповідь про факт неповернення після проходження військово-лікарської комісії до району виконання завдання за призначенням військовослужбовцем військової частини А0224."
    file_name = '08.02.2025 СЗЧ несвоєчасне прибуття ГАВНОВ О.Ю. 1 сабатр САДн.docx'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "13.02.2026 року солдат БУЙНОВ Станіслав Миколайович не прибув з військово-лікарської комісії до району виконання завдання за призначенням, документів що підтверджують продовження лікування в інших лікувальних закладах не надав."
    file_name = '16.02.2026 СЗЧ неповернення після проходження ВЛК (Буйнов С.М.) рв 3 дшб(2).doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "03.02.2026 старший солдат МУДІК Олександр Сергійович вибув з постійного пункту дислокації (н.п. Вознесенське Миколаївської області) військової частини А0224 (переміщення) до військової частини А5291, відповідно наказу НГШ ЗСУ №122-РС від 17.01.2026. До військової частини А5191 не прибув 04.02.2021, згідно повідомлення військової частини А5291 (акт прийому поповнення вх. №111 від 14.02.2021). До військової частини А0224 не повернувся."
    file_name = '09.02.2021 СЗЧ неприбуття (переміщення) до військової частини А5291 (Мудік О.С.) 11 дшр 3 дшб.doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'ППД'

    text = "03.02.2026 старший солдат МУДІК Олександр Сергійович вибув з постійного пункту дислокації (н.п. Вознесенське Миколаївської області) військової частини А0224 (переміщення) до військової частини А5291, відповідно наказу НГШ ЗСУ №122-РС від 17.01.2026. До військової частини А5191 не прибув 04.02.2021, згідно повідомлення військової частини А5291 (акт прийому поповнення вх. №111 від 14.02.2021). До військової частини А0224 не повернувся."
    file_name = '09.02.2021 СЗЧ неприбуття (переміщення) до військової частини А5291 (Мудік О.С.) 11 дшр 3 дшб.doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'ППД'

    text = "10.02.2026 року від командира 1 десантно-штурмового батальйону військової частини А0224 надійшла доповідь про факт повернення після самовільного залишення району виконання бойового завдання військовослужбовця військової частини А0224."
    file_name = '10.02.2026 повернення після СЗЧ з поля бою ГАВНОВ О. С. 1дшр 1дшб.doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'РВБЗ'

    text = "09.02.2026 року від ТВО командира 2 зведеної роти надійшла доповідь про факт не прибуття після відпустки за станом здоров'я до пункту постійної дислокації військовослужбовця військової частини А0224 .09.02.2026 року при перевірці наявності особового складу у місці розосередження особового складу н.п. Вознесенське Миколаївської області був відсутній солдат за призовом АЛЕКСЄЄВ Віталій Віталійович ( не прибув з відпустки за станом здоров’я) до ППД в/ч А0224 н.п. Вознесенське Миколаївської області. Пошук військовослужбовця в районі тимчасового місці перебування підрозділу поблизу с. Вознесенське Миколаївської області позитивного результату не приніс, на телефонні дзвінки не відповідає. Місцезнаходження військовослужбовця невідоме. Прошу вважати таким, що здійснив СЗЧ. "
    file_name = '09.02.2026 не прибутя з ВПХ 8 дшр 2 дшб  АЛЕКСЄЄВ В.В...doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'відпустки'

    text = "09.02.2026 року від командира 5 десантно-штурмової роти 2 десантно-штурмового батальйону надійшла доповідь про факт повернення після самовільного залишення військової частини А0224 солдата ГАВНОВА Євгенія Миколайовича. 08.02.2026 року близько 20:00 години під час перевірки наявності особового складу в районі зосередження підрозділом поблизу н.п. Бажани Дніпропетровської області було виявлено факт повернення солдата ГАВНОВА Євгенія Миколайовича, після неповернення з відпустки за станом здоров’я до району виконання завдання за призначенням 25.12.2025 року.  Решта обставин з'ясовується."
    file_name = '09.02.2026 повернення після СЗЧ 5 дшр 2 дшб ГАВНОВ Є.М.doc'
    res = processor._extract_desertion_place(text, file_name)
    assert res == 'відпустки'

def test_milsubunit_extraction(processor_factory):
    processor = processor_factory("any.docx")

    text = "ГАВНОВ Віталій Сергійович, солдат, військовослужбовець військової служби за призовом, розвідник-санітар 2 розвідувального відділення розвідувального взводу 1 десантно-штурмового батальйону військової частини А0224, 30.07.1986 року народження, українець, освіта середня . Призваний"
    file_name = '09.02.2026 СЗЧ РВБЗ ГАВНОВ А. С. РВ 1ДШБ.docx'
    res = processor.extract_military_subunit(text, file_name)
    assert res == '1 дшб'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'РВ'

    text = "ГАВНОВ Віталій Сергійович, військовослужбовець військової служби за призовом, оператор безпілотних літальних апаратів 2 відділення перехоплювачів безпілотних літальних апаратів 2 взводу перехоплювачів безпілотних літальних апаратів батареї перехоплювачів безпілотних літальних апаратів зенітного ракетного дивізіону військової частини А0224, 11.08.2001 року народження, Українець, освіта вища, "
    file_name = '09.02.2026_СЗЧ_з_району_ГАВНОВ_Бат_ПБпЛА_ЗРДн.docx'
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'ЗРДн'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'БатПБПЛА'

    text = "ГАВНОВ Леонід Генадійович, старший солдат, військовослужбовець військової служби за мобілізацією, старший навідник 2 артилерійського взводу 2 артилерійської батареї самохідного артилерійського дивізіону військової частини А0224"
    file_name = '09.02.2026_СЗЧ_з_РВБЗ_2_АБАТР_САДН__БІЖКО_Л.Г..doc'
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'САДн'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '2 арт. Батарея'

    text = "ГАВНОВ Леонід Генадійович, старший солдат, військовослужбовець військової служби за мобілізацією, старший навідник 2 артилерійського взводу 1 артилерійської батареї самохідного артилерійського дивізіону військової частини А0224"
    file_name = '09.02.2026_СЗЧ_з_РВБЗ_2_АБАТР_БІЖКО_Л.Г..doc'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT_MAPPING)
    assert res == 'САДн'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '1 арт. Батарея'

    text="оператор безпілотних літальних апаратів взводу інженерних безпілотних наземних систем інженерно – саперної роти військової частини А0224, 26.06.1987 року народження, українець,"
    file_name = ''
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'ІСР'

    text = "ДУМБА Дмитро Миколайович, солдат, військовослужбовець військової служби за призовом, оператор безпілотних літальних апаратів 6 відділення 2 взводу ударних безпілотних авіаційних комплексів роти безпілотних систем аеромобільного батальйону військової частини А022"
    file_name = '11.02.2026 СЗЧ з РВБЗ АЕМБ РБС ДУМБА Д.М.doc'
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'АЕМБ'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'РБС'

    text = "ДУМБА Іван Іванович, солдат, військовослужбовець військової служби за мобілізацією, навідник 1 аеромобільного відділення 1 аеромобільного взводу 4 аеромобільної роти аеромобільного батальйону військової частини А0224"
    file_name = "04.02.2026 СЗЧ з РВБЗ ДУМБА І.І. 4 аемр аемб.docx"
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'АЕМБ'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '4 аемр'

    text = "ДУМБА Юрій Олександрович, старший солдат, військовослужбовець військової служби за мобілізацією, водій 2 автомобільного відділення 1 автомобільного взводу підвозу боєприпасів автомобільної роти підвозу боєприпасів батальйону логістики військової частини А0224, 16.09.1979 року народження"
    file_name = ""
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'БЛ'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'Автомобільна рота підвозу боєприпасів'

    text = "ДУМБА Сергій Васильович, солдат, військовослужбовець військової служби за мобілізацією, водій 3 відділення 2 автомобільного взводу автомобільної роти батальйону логістики військової частини А0224, дата народження: 07.11.1979"
    file_name = ""
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'БЛ'
    res = processor.extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'Автомобільна рота'

    text = "ДУМБА Дмитро Андрійович, солдат, за призовом під час мобілізації, водій-електрик БУ, 07.09.1997р.н."
    file_name = ""
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'БУ'

    text = "ДУМБА Олександр Миколайович, сержант, військовослужбовець військової служби за мобілізацією, водій автомобільного відділення взводу забезпечення батальйону управління військової частини А0224, 05.02.1995 року народження"
    file_name = ""
    res = processor.extract_military_subunit(text, file_name)
    assert res == 'БУ'

def test_desertion_type_extraction(processor_factory):
    processor = processor_factory("any.docx")

    text = "16.02.2026 близько 14:00 солдат БУЙНОВ Антон Олександрович, солдат БАРАНЧУК Максим Володимирович та солдат СКАЧКУК Сергій Іванович здійснили самовільне залишення району виконання бойового завдання підрозділом поблизу населеного пункту Шевченко Добропільської міської громади Покровського району Донецької області. Військовослужбовець: солдат БУЙНОВ Антон Олександрович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6811118, набої 5,45 x 39 в кількості 400 шт., граната DM52 – 2 шт.) солдат БАРАНЧУК Максим Володимирович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6811119, набої 5,45 x 45 в кількості 400 шт., граната DM52 – 2 шт.) солдат СКАЧКУК Сергій Іванович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6722224, набої 5,45 x 39 в кількості 400 шт"
    where = processor._extract_desertion_place(text)
    assert where == 'РВБЗ'
    res = processor._extract_desertion_type(text, where)
    assert res == 'СЗЧ зброя'


def test_return_sign(processor_factory):
    processor = processor_factory("any.docx")

    text = "03.06.2022 року солдат БОЛВАН Іван Васильович не повернувся з лікування до району виконання завдання за призначенням."
    assert False == processor._check_return_sign(text)

def test_desertion_sign(processor_factory):
    processor = processor_factory("any.docx")
    text = "16.02.2026 від командира аеромобільного батальйону надійшла доповідь про факт необережного поводження зі зброєю військовослужбовців військової частини А0224. Попередньо встановлено, що особовий склад підрозділів військової частини А0224 відповідно до бойового наказу командира військової частини А0224 №3/3т/БН від 15.02.2026 веде наступальні (штурмові) дій батальйонів I ешелону на глибину виконання найближчого та подальшого завдання при проведенні наступальних (штурмових) дій при виконанні заходів з національної безпеки та оборони, відсічі та стримуванні збройної агресії. Встановлено, що під час виконання бойового завдання, в районі виконання завдань за призначенням, у визначеній смузі відповідальності військової частини А0224, внаслідок необережного поводження зі зброєю отримав поранення військовослужбовець військової частини А0224: Солдат за призовом БУЙНОВ Олександр Олексійович, номер обслуги мінометного відділення взводу вогневої підтримки 1 аеромобільної роти аеромобільного батальйону військової частини А0224, діагноз: “Вогнепальне кульове(15.02.2026) сліпе поранення медіальної поверхні нижньої третини лівої гомілки, проникаюче? в гомілково-стопний суглоб”. Військовослужбовця евакуйовано до ПХГ Петропавлівка. Військовослужбовець перебував у засобах індивідуального захисту та з особистою зброєю. Ознак алкогольного та наркотичного сп’яніння не виявлено. Решта обставин з'ясовується."
    record = {
        COLUMN_DESERT_CONDITIONS : processor._extract_desert_conditions(text),
        COLUMN_RETURN_DATE : processor._extract_return_date(text),
    }

    assert False == processor.is_desertion_case(record)

def test_ml(processor_factory):
    text = "НЕГОЛЮК Володимир Васильович, старший солдат, військовослужбовець військової служби за призовом, стрілець-помічник гранатометника 2  десантно-штурмового відділення 3 десантно-штурмового взводу 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 29.10.1981 року народження, українець, освіта вища, Національний транспортний університет м. Київ у 2010 році. Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків, 25.10.2025 року. РНОКПП відомості не надано"
    log_manager = LoggerManager()


    parser = MLParser(model_path=config.ML_MODEL_PATH, log_manager=log_manager)
    extracted = parser.parse_text(text)
    assert extracted[COLUMN_TZK] == 'Салтівським ВТТЦК та СП м. Харків'
    assert extracted[COLUMN_TITLE] == 'старший солдат'
    assert extracted[COLUMN_NAME] == 'НЕГОЛЮК Володимир Васильович'

    print("Результат розпізнавання:")
    for key, value in extracted.items():
        print(f"[{key}]: {value}")


    text = "09.02.2026 року від тимчасово виконуючого обов’язки командира батальйону безпілотних систем військової частини А0224, надійшла доповідь про факт самовільного залишення району виконання завдання за призначенням військовослужбовця військової частини А0224 (без зброї). Попередньо встановлено, що особовий склад підрозділів військової частини А0224 відповідно до бойового наказу командира військової частини А0224 №3/2т від 18.01.2026 веде наступальні (штурмові) дії батальйонів I ешелону на глибину виконання найближчого та подальшого завдання при проведенні наступальних (штурмових) дій при виконанні заходів з національної безпеки та оборони, відсічі та стримуванні збройної агресії. 09.02.2026 року під час перевірки наявності особового складу був відсутній солдат за призовом ХЛОПУК Олександр Миколайович, який самовільно залишив район виконання завдання за призначенням. Пошук військовослужбовця в районі зосередження підрозділу в н.п. Шахтарське Дніпропетровської області позитивного результату не приніс. Місце знаходження військовослужбовця невідоме. Решта обставин з'ясовується."
    extracted = parser.parse_text(text)

    print("Результат розпізнавання:")
    for key, value in extracted.items():
        print(f"[{key}]: {value}")