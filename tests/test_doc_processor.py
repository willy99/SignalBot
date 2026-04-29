from unittest.mock import MagicMock

import pytest
from pathlib import Path

import utils.utils
from service.processing.processors.DocProcessor import DocProcessor
from dics.deserter_xls_dic import *
from service.processing.parsers.MLParser import MLParser
import config
from service.storage.LoggerManager import LoggerManager
from utils.regular_expressions import *

@pytest.fixture
def mock_logger():
    logger_manager = MagicMock(spec=LoggerManager)
    logger = MagicMock()

    # Функція, яка буде імітувати запис у консоль
    def print_to_console(msg, *args, **kwargs):
        # Додаємо колір або префікс, щоб бачити, що це саме з логера
        print(f"\n[LOG-DEBUG] {msg}")

    # Прив'язуємо функцію до методу debug (можна і до info/error)
    logger.debug.side_effect = print_to_console
    logger.info.side_effect = print_to_console
    logger.error.side_effect = print_to_console

    logger_manager.get_logger.return_value = logger
    return logger_manager


@pytest.fixture
def processor_factory(mock_logger):
    """Фабрика для створення процесора з різними файлами"""

    def _create_processor(file_name):
        # .resolve() знайде правильний шлях з урахуванням особливостей ОС
        base_path = (Path(__file__).parent / "data" / file_name).resolve()

        # Якщо файл не знайдено, ми побачимо це ДО того, як впаде docx
        if not base_path.exists() and "any.docx" != file_name:
            raise FileNotFoundError(f"Тестовий файл не знайдено: {base_path}")

        return DocProcessor(mock_logger, base_path, file_name)

    return _create_processor

def test_utils_clean_text():
    text = 'ПЛЕМ\'ЯНИК Артем Сергійович'
    clean_text = utils.utils.clean_text(text)
    assert clean_text == 'ПЛЕМ\'ЯНИК Артем Сергійович'

    text = 'ПЛЕМʼЯНИК Артем Сергійович'
    clean_text = utils.utils.clean_text(text)
    assert clean_text == 'ПЛЕМ\'ЯНИК Артем Сергійович'

    text = 'ПЛЕМ’ЯНИК Артем Сергійович'
    clean_text = utils.utils.clean_text(text)
    assert clean_text == 'ПЛЕМ\'ЯНИК Артем Сергійович'

def test_process_doc_fedorov_simple(processor_factory, mock_logger):
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
    assert fields[COLUMN_DESERTION_REGION] == "Дніпропетровська область"
    assert "ФЕДОРОВ Олександр Вікторович" in fields[COLUMN_DESERT_CONDITIONS]
    assert "самовільно залишив" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0687775544"
    assert "Кіровоградська область, Олександрійський район, м. Олександрія, вул. Дружби 22, кв. 23" in fields[COLUMN_ADDRESS]
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "МОГУТОВ Ігор Миколайович"


def test_process_doc_maly_simple(processor_factory, mock_logger):
    # Тестуємо реальний кейс (СЗЧ)
    filename = "02_01.01.2026 СЗЧ з РВБЗ 2 сабатр САДН  МАЛИЙ Д.В.doc"
    processor = processor_factory(filename)
    result = processor.process()

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
    assert fields[COLUMN_DESERTION_REGION] == "Дніпропетровська область"
    assert "МАЛИЙ Дмитро Вадимович" in fields[COLUMN_DESERT_CONDITIONS]
    assert fields[COLUMN_PHONE] == "0969111111"
    assert "Дніпропетровська обл., м. Кривий Ріг, вул. Ф. Караманиця, буд. 11А, кв 12" in fields[COLUMN_ADDRESS]
    assert fields[COLUMN_RETURN_DATE] is None
    assert fields[COLUMN_EXECUTOR] == "БОЙКО Віктор Олександрович"
    assert fields[COLUMN_DESERTION_TYPE] == DEFAULT_DESERTION_TYPE

# tests error - missing one of the part in the document
def test_process_doc_maly_error_missing_4(processor_factory, mock_logger):
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
    assert person1[COLUMN_SUBUNIT2] == '7 дшр'
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
    assert person2[COLUMN_SUBUNIT] == '3 дшб'
    assert person2[COLUMN_SUBUNIT2] == '10 дшр'

    assert "31.01.2026 о 16:00 під час перевірки особового складу 7 десантно-штурмової роти 2 десантно-штурмового батальйону командиром підрозділу капітаном БЕШЛЯГОЮ Р.В. було виявлено відсутність військовослужбовців солдата ІВОНЧАКА Дмитра Васильовича та солдата НЕГОЛЮКА Володимира Васильовича, які самовільно залишили район зосередження 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224 поблизу н.п. Привовчанське Дніпропетровської області" in person2[COLUMN_DESERT_CONDITIONS]
    assert "31.01.2026 року від командира 7 десантно-штурмової роти 2 десантно-штурмового батальйону надійшла доповідь про факт самовільного залишення району виконання завдання за призначенням військовослужбовця військової частини А0224 солдата ІВОНЧАКА Дмитра Васильовича та солдата НЕГОЛЮКА Володимира Васильовича (без зброї" not in person2[COLUMN_DESERT_CONDITIONS]

    # --- ПЕРЕВІРКА СПІЛЬНИХ ДАНИХ ---
    for field in result:
        assert field[COLUMN_MIL_UNIT] == 'А0224'
        assert field[COLUMN_DESERTION_DATE] == '31.01.2026'
        assert field[COLUMN_DESERTION_REGION] == 'Дніпропетровська область'
        assert "ІВОНЧАК" in field[COLUMN_DESERT_CONDITIONS]
        assert "НЕГОЛЮК" in field[COLUMN_DESERT_CONDITIONS]
        assert field[COLUMN_EXECUTOR] == 'БЕЗКРОВНИЙ Володимир Володимирович'

def test_process_doc_tzk_is_full(processor_factory, mock_logger):
    # перевірка, що тцк розпарсився правильно та повно. матьйїхйоп
    filename = "05_05.02.2026 СЗЧ з РВБЗ (Гавнов В.М.) рбс 3 дшб_tzk.doc"
    processor = processor_factory(filename)
    result = processor.process()

    assert isinstance(result, list)
    assert len(result) == 1

    person = result[0]
    assert person[COLUMN_TZK] == 'Крижопільським РТЦК та СП м. Крижопіль'
    assert person[COLUMN_TZK_REGION] == "Вінницька область"

def test_process_docx_simple(processor_factory, mock_logger):
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
    assert person[COLUMN_DESERTION_REGION] == 'Миколаївська область'
    assert "З 01.08.2025 по 17.10.2025 був на стаціонарному лікуванні в КНП “Хмільницька центральна лікарня”. 30.12.2025 прибув до пункту постійної дислокації військової частини А0224 (н.п. Вознесенське, Миколаївської області" in person[
        COLUMN_DESERT_CONDITIONS]
    assert "З 18.10.2025 по 29.12.2025 солдат ГАВНОВ Віктор Євгенович був відсутній на військовій службі, підтверджуючих документів не надав (відсутній на військовій службі 73 доби)" in person[
        COLUMN_DESERT_CONDITIONS]
    assert person[COLUMN_PHONE] == '0671118227'
    assert person[COLUMN_ADDRESS] == "Хмельницька область, Ізяславський район, с. Теліжинці, вул. Центральна, буд. 48."
    assert person[COLUMN_EXECUTOR] == 'САМУЛІК Роман Богданович'
    assert person[COLUMN_RETURN_DATE] == '30.12.2025'

def test_return_date(processor_factory, mock_logger):
    filename = "07_09.02.2026 повернення після СЗЧ 5 дшр 2 дшб ДУБ Є.М..doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    person = result[0]

    assert person[COLUMN_RETURN_DATE] == '09.02.2026' # todo - винно бути -08.02.2026
    assert person[COLUMN_DESERTION_DATE] == ''
    assert person[COLUMN_DESERTION_PLACE] == ''

def test_not_a_desertion_case(processor_factory, mock_logger):
    filename = "08_12.02.2026 Травмування  (КАША О.М.) МР.docx"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 0


def test_desertion_date_is_correct(processor_factory, mock_logger):
    filename = "09_15.02.2026 СЗЧ з лікування БУЙНОВ С.В. 3дшр 1дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_RETURN_DATE] is None
    assert person[COLUMN_DESERTION_DATE] == '13.02.2026'  # винно бути не 15.02.2026!


def test_402_refusal(processor_factory, mock_logger):
    filename = "10_02.03.2026 відмова ДУМБЄКОВ С.А. 8 дшр 2 дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1

    # --- ПЕРЕВІРКА ПЕРШОЇ ОСОБИ (ІВОНЧАК) ---
    person = result[0]
    assert person[COLUMN_NAME] == 'ДУМБЄКОВ Сергій Анатолійович'
    assert person[COLUMN_TITLE] == 'солдат'
    assert person[COLUMN_ID_NUMBER] == '2111111119'
    assert person[COLUMN_BIRTHDAY] == '03.02.1979'
    assert person[COLUMN_SUBUNIT] == '2 дшб'
    assert person[COLUMN_SUBUNIT2] == '8 дшр'
    assert person[COLUMN_SERVICE_TYPE] == 'призивом'
    assert person[COLUMN_PHONE] == '0951111111'
    assert person[COLUMN_ADDRESS] == "Миколаївська область м. Первомайськ, вул. Громова 11."
    assert person[COLUMN_TZK] == 'Первомайським РТЦК та СП м. Первомайськ Миколаївська область'
    assert person[COLUMN_TZK_REGION] == "Миколаївська область"
    assert person[COLUMN_ENLISTMENT_DATE] == '09.12.2025'
    assert person[COLUMN_SERVICE_DAYS] == 78
    assert person[COLUMN_DESERTION_PLACE] == 'РВБЗ'
    assert person[COLUMN_DESERTION_TYPE] == 'відмова'
    assert person[COLUMN_CC_ARTICLE] == '402'


def test_return_data_is_correct(processor_factory, mock_logger):
    filename = "11_03_03_2026_повернення_БУЙКО_Д_В_Танкова_рота.docx"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_RETURN_DATE] == '03.03.2026'
    assert person[COLUMN_DESERTION_DATE] == NA
    assert person[COLUMN_DESERTION_PLACE] == NA
    assert person[COLUMN_DESERTION_REGION] == NA

def test_return_data_is_correct_2(processor_factory, mock_logger):
    filename = "12_27_02_2026_повернення_БУЙКО_Д_В_8_дшр_2_дшб.doc"
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_NAME] == 'БУЙКО Дмитро Володимирович'
    assert person[COLUMN_RETURN_DATE] == '27.02.2026'
    assert person[COLUMN_DESERTION_DATE] == NA
    assert person[COLUMN_DESERTION_PLACE] == NA
    assert person[COLUMN_DESERTION_REGION] == NA

def test_processing_imaged_pdf_ocr(processor_factory, mock_logger):
    filename = '13_09.01.2025 СЗЧ з А2900 зап рота МУРАХОВСЬКИЙ Володимир Олегович.PDF'
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_NAME] == 'МУРАХОВСЬКИЙ Володимир Олегович'
    assert person[COLUMN_MIL_UNIT] == 'А2900'
    assert person[COLUMN_DESERTION_DATE] == '09.01.2025'
    assert person[COLUMN_ID_NUMBER] == '3212723839'
    assert person[COLUMN_PHONE] == '0667056181'
    assert person[COLUMN_BIRTHDAY] == '17.12.1987'
    assert person[COLUMN_TITLE] == 'солдат'
    assert person[COLUMN_SUBUNIT] == 'Зап рота'
    assert person[COLUMN_SERVICE_TYPE] == 'призивом'
    assert person[COLUMN_ADDRESS] == 'Одеська обл., Беляєвський р-н, с. Дослідне, вул. Каштанова, буд. 18'

def test_incorrect_headings_without_numbers(processor_factory, mock_logger):
    filename = '14_30.03.2026 СЗЧ ППД ЗАЛУЖНИЙ В. Я. ВРЕБ 1дшб.doc'
    processor = processor_factory(filename)
    result = processor.process()
    assert isinstance(result, list)
    assert len(result) == 1
    person = result[0]

    assert person[COLUMN_NAME] == 'ЗАЛУЖНИЙ Володимир Ярославович'
    assert person[COLUMN_MIL_UNIT] == 'А0224'
    assert person[COLUMN_DESERTION_DATE] == '30.03.2026'
    assert person[COLUMN_ID_NUMBER] == '3311111125'
    assert person[COLUMN_PHONE] == '0931111111'
    assert person[COLUMN_BIRTHDAY] == '03.02.1987'
    assert person[COLUMN_TITLE] == 'солдат'
    assert person[COLUMN_SUBUNIT] == '1 дшб'
    assert person[COLUMN_SERVICE_TYPE] == 'призивом'
    assert person[COLUMN_ADDRESS] == 'Одеська обл.. м. Біляївка , вул. Отамана Головатого, буд. 111.'


#################### загальне модульне тестування регекспів ##############################

def test_military_unit(processor_factory, mock_logger):
    text = "ДОПОВІДЬ про факт не прибуття до місця несення служби військовослужбовця військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України"
    res = extract_mil_unit(text)
    assert res == 'А0224'

    text = "ДОПОВІДЬ про факт самовільного залишення району виконання завдання військовослужбовцями військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України"
    res = extract_mil_unit(text)
    assert res == 'А0224'

    text = "ДОПОВІДЬ про факт самовільного залишення району виконання завдання за призначенням військовослужбовців зарахованих до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України "
    res = extract_mil_unit(text)
    assert res == 'А7018'

    text = "ДОПОВІДЬ про факт самовільного залишення району виконання завдання за призначенням військовослужбовців зарахованих до тимчасово прибулого особового складу військової частини А7019, що був відряджений до військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України "
    res = extract_mil_unit(text)
    assert res == 'А7018'

    text = "ДОПОВІДЬ про факт не прибуття після лікування до району виконання завдання за призначенням військовослужбовця батальйону резерву військової частини А7019 (7 КШР) Десантно-штурмових військ Збройних Сил України"
    res = extract_mil_unit(text)
    assert res == 'А7018'


def test_name_extraction(processor_factory, mock_logger):
    text = "ГАВНОВЄЗЕРСЬКИЙ Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "ГАВНОВЄЗЕРСЬКИЙ Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли-Піздик, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "САЛТИКОВ-ЩЕДРІН Олег Вікторович-Огли" in res

    text = "Салтіков Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "" in res

    text = "Текст попереду ПРОТОН Олег Вікторович, старший солдат, військовослужбовець військової служби за призивом, "
    res = extract_name(text)
    assert "ПРОТОН Олег Вікторович" in res

    text = "Текст попереду ПРОТОН Олег Вікторович-Огли і пробели далі, старший солдат, військовослужбовець військової служби за призовом, "
    res = extract_name(text)
    assert "ПРОТОН Олег Вікторович-Огли" in res

    text = "ГАВНОВ Назар-Іван Васильович солдат, військовослужбовець військової служби за призовом,  колишній гранатометник 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, "
    res = extract_name(text)
    assert "ГАВНОВ Назар-Іван Васильович" in res

    text = "ДУМБА Михайло В’ячиславович, солдат за призовом, військовослужбовець за мобілізацією, стрілець-снайпер 1 взводу охорони  "
    res = extract_name(text)
    assert "ДУМБА Михайло В’ячиславович" in res


def test_name_lowercase_extraction(processor_factory, mock_logger):
    text = "військовослужбовець військової частини А0224 солдат ЗАЛУЖНИЙ Олександр Сергійович, 01.05.1992 року народження самовільно залишив"
    res = extract_name_lowercased(text)
    assert res == "ЗАЛУЖНИЙ Олександр Сергійович"

    text = "3 десантно-штурмового батальйону в/ч А0224 (79-та одшбр) солдат Залужний Юрій Миколайович, 19.05.1999 р.н., РНОКПП "
    res = extract_name_lowercased(text)
    assert res == "Залужний Юрій Миколайович"

    text = "3 десантно-штурмового батальйону в/ч А0224 (79-та одшбр) солдат Залужний Мар’ян Андрійович, 01.01.1998 р.н., РНОКПП"
    res = extract_name_lowercased(text)
    assert res == "Залужний Мар’ян Андрійович"

    text = "3 десантно-штурмового батальйону в/ч А0224 (79-та одшбр) молодший сержант Залужний Віталій Михайлович, 09.05.1981 р.н., РНОКПП "
    res = extract_name_lowercased(text)
    assert res == "Залужний Віталій Михайлович"

    text = "військовослужбовець військової служби за призовом солдат Залужний Іван Олександрович, 26.06.2000 р.н., "
    res = extract_name_lowercased(text)
    assert res == "Залужний Іван Олександрович"

    text = "авіаційних комплексів роти ударних безпілотних авіаційних комплексів військової частини А7047, прапорщик ЗАЛУЖНИЙ Олександр Валерійович, 18.10.1983 р.н.,"
    res = extract_name_lowercased(text)
    assert res == "ЗАЛУЖНИЙ Олександр Валерійович"

    text = "Дружківка Донецької області 09.07.2022 військовослужбовцями, зокрема солдатом Залужним Олександром Вікторовичем, 17.07.1977 р.н., "
    res = extract_name_lowercased(text)
    assert res == "Залужний Олександр Вікторович"

    text = "роти аеромобільного батальйону в/ч А0224 (79-та одшбр) рядовий Залужний Сергій Іванович, 18.03.1971 р.н., Р"
    res = extract_name_lowercased(text)
    assert res == "Залужний Сергій Іванович"


def test_title_extraction(processor_factory, mock_logger):
    text = "ПУНДІК Олег Вікторович, старший солдат, військовослужбовець військової служби за призовом, "
    res = extract_title(text)
    assert "старший солдат" in res
    res = extract_title_2(res)
    assert "солдат" in res

    text = "ПУНДІКА Олега Вікторовича, старшого солдату, військовослужбовець військової служби за призовом, "
    res = extract_title(text)
    assert "старший солдат" in res

    text = "ПУНДІКУ Олегу Вікторовичу, солдату, військовослужбовець військової служби за призовом, "
    res = extract_title(text)
    assert "солдат" in res

    text = "ПУНДІК Олег Вікторович, військовослужбовець військової служби за призовом, "
    res = extract_title(text)
    assert "солдат" in res

    text = "БОЛВАН Руслан Олександрович, військовослужбовець військової служби за призовом, аааа. Близькі родичі: Батько: БОЛВАН Олександр Владиславович, 23.06.1965 р.н., м. Київ, тел. +380993955598; Мати: БОЛВАН Світлана Сергіївна, 05.05.1970 р.н., смт. Капітанівка, "
    res = extract_title(text)
    assert "солдат" in res

    text = "БОЛВАН Руслан Олександрович, старший лейтенант за контрактом. Близькі родичі: Батько: БОЛВАН Олександр Владиславович, 23.06.1965 р.н., м. Київ, тел. +380993955598; Мати: БОЛВАН Світлана Сергіївна, 05.05.1970 р.н., смт. Капітанівка, "
    res = extract_title(text)
    assert "старший лейтенант" in res
    res = extract_title_2(res)
    assert "офіцер" in res

    text = "БОЛВАН Руслан Олександрович, солдат, військовослужбовець військової служби за мобілізацією, водій-електрик-моторист 1 відділення 2 взводу ударних безпілотних авіаційних комплексів роти безпілотних систем"
    res = extract_title(text)
    assert "солдат" in res

    text = "БОЛВАН Олександр Юрійович, призваний 23.01.2026 1 відділом Первомайського РТЦК та СП у Миколаївської обл. 22.08.1999 року народження, українець, освіта середня, неодружений, військовий квиток: АГ 111155, ІПН 3111111558. Адреса проживання: Миколаївська обл., с, Новогригорівка, моб. тел.: 738(068)111-25-95. Базову загальновійськову підготовку не пройшов. Близькі родичі: мати - БОЛВАН Марія Олексіївна,"
    res = extract_title(text)
    assert res == NA

    text = "БОЛВАН Владислав Вікторович, солдат, військовослужбовець військової служби за мобілізацією, кулеметник 1 десантно-штурмового відділення 1 десантно-штурмового взводу 8 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 20.01.1984 року народження, українець, середня, цивільний шлюб. Призваний Комінтернівськім РТЦК та СП, 26.06.2025 року. РНОКПП 3111116171, номер мобільного телефону +380911111130. Адреса проживання військовослужбовця: Одеська обл., Комінтерновський р-н., с.Візірка, вул. Полковника Гуляєва 222. Близькі родичі: цивільна дружина Болван Алла Георгівна 1989 р.н.;"
    res = extract_title(text)
    assert res == "солдат"

    text = "БОЛВАН Дмитро Анатолійович, майор, військовослужбовець військової служби за контрактом, старший оперативний черговий бойового управління командного пункту штабу військової частини А0224, :"
    res = extract_title(text)
    assert res == "майор"

    text = "БОЛВАН Дмитро Анатолійович, солдат, військовослужбовець військової служби за контрактом, старший оперативний черговий бойового управління командного пункту штабу військової частини А0224, Адреса проживання військовослужбовця: Одеська обл., Комінтерновський р-н., с.Візірка, вул. Капітана Гуляєва 222. Близькі родичі: цивільна дружина Болван Алла Георгівна 1989 р.н.;:"
    res = extract_title(text)
    assert res == "солдат"

    text = "БОЛВАН Іван Іванович, молодший сержант, військовослужбовець військової служби за призовом колишній головний сержант 3 аеромобільної роти аеромобільного батальйону військової частини А0224, 21.07.1986 року народження, українець, освіта середня, неодружений. Призваний 24.02.2022 Бориспільський РТЦК та СП 2 відділ Київської області "
    res = extract_title(text)
    assert res == "молодший сержант"

    text = "БОЛВАН Віталій Степанович, солдат, за мобілізацією, головний сержант командир танка 3 танкового взводу танкової роти військової частини А0224,  05.07.1979 року народження, українець, освіта середня. У ЗСУ з 11.10.2023 року,  "
    res = extract_title(text)
    assert res == "солдат"

    text = "БОЛВАН Ігор Петрович, майстер-сержант, військовослужбовець військової служби за мобілізацією,"
    res = extract_title(text)
    assert res == "майстер-сержант"

def test_service_type_extraction(processor_factory, mock_logger):
    text = "БОЛВАН Денис Миколайович, солдат, за контрактом під час мобілізації, "
    cond = "19.04.2025 солдат БОЛВАН Максим Сергійович та солдат ЗАЛУЖНИЙ Денис Миколайович не прибули до військової частини А 7363 (н.п Новохатське Донецької обл.)."
    res = extract_service_type(text, cond)
    assert res == "контрактом"

def test_rtzk_extraction(processor_factory, mock_logger):
    text = "Призваний Слов'янським ТЦК 10.09.2025. РНОКПП 1234567890"
    res = extract_rtzk(text)
    assert "Слов'янським ТЦК" in res

    text = "Призваний Пересипським РТЦК та СП , м. Одеса, 23.12.2024,. РНОКПП 3"
    res = extract_rtzk(text)
    assert res == "Пересипським РТЦК та СП , м. Одеса"

    text = "призваний Кропивницьким РТЦК та СП, м. Кропивницький, Кіровоградська обл., 19.06.2025 року. РНОКПП 32"
    res = extract_rtzk(text)
    assert res == "Кропивницьким РТЦК та СП, м. Кропивницький, Кіровоградська обл"

    text = "88 р.н.; призваний Галицько-Франківським ОРТЦК та СП 01.11.2025; адреса проживання: Льв"
    res = extract_rtzk(text)
    assert res == "Галицько-Франківським ОРТЦК та СП"

    text = "неодружений. Призваний Салтівським РТЦК та СП м. Харків, 27.07"
    res = extract_rtzk(text)
    assert res == "Салтівським РТЦК та СП м. Харків"

    text = "на, неодружений. Призваний Покровським РТЦК та СП, Дніпропетровської області, 06.05.2025 року. РНОКПП 333"
    res = extract_rtzk(text)
    assert res == "Покровським РТЦК та СП, Дніпропетровської області"

    text = "неодружений. Призваний Салтівським ОМТЦК та СП м. Харків, 27.07"
    res = extract_rtzk(text)
    assert res == "Салтівським ОМТЦК та СП м. Харків"

    text = "року народження, українець, освіта вища, неодружений. Призваний Центральним РТЦК та СП в м. Миколаїв, Миколаївської області, 06.12.2025. РНОКПП 36"
    res = extract_rtzk(text)
    assert res == "Центральним РТЦК та СП в м. Миколаїв, Миколаївської області"

    text = "БУЙКО Юрій Станіславович, військовослужбовець військової служби за призовом, зарахований до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224, 31.10.1975 року народження, Українець, освіта середня, розлучений. Призваний Покровсько-Тернівським РТЦК та СП м. Кривий Ріг 24.02.2022 року. "
    res = extract_rtzk(text)
    assert res == "Покровсько-Тернівським РТЦК та СП м. Кривий Ріг"

    text = "БУЙНОВ Антон Олександрович, солдат, військовослужбовець військової служби за призовом, гранатометник 1 аеромобільного відділення 1 аеромобільного взводу 3 аеромобільної роти аеромобільного батальйону військової частини А0224, 22.11.1985 року народження, українець, освіта середня, не одружений. Призваний 4 відділ Миколаївського РТЦК та СП м. Миколаїв, 27.11.2025 року. Номер мобільного телефону +380611111119."
    res = extract_rtzk(text)
    assert res == "4 відділ Миколаївського РТЦК та СП м. Миколаїв"

    text = "БУЙКО Олександр Володимирович, військовослужбовець військової служби за призовом, зарахований до тимчасово прибулого особового складу військової частини А7018, що був відряджений до військової частини А0224, 13.11.1983 року народження, Українець, освіта середня, цивільний шлюб. Призваний Новокодацьким РТЦК та СП м. Дніпра 06.12.2024 року. "
    res = extract_rtzk(text)
    assert res == "Новокодацьким РТЦК та СП м. Дніпра"

    text = "БУЙКО Олексій Миколайович, майстер-сержант, військовослужбовець військової служби за контрактом, командир господарчого відділення самохідного артилерійського дивізіону військової частини А0224, 22.03.1982 року народження, освіта середня, одружений. Призваний Новоодеським РВК Миколаївської обл., 04.02.2013 року. РНОКПП 3003117373, номер мобільного телефону 0687849466. "
    res = extract_rtzk(text)
    assert res == "Новоодеським РВК Миколаївської обл"

    text = "Призваний: Миколаївським МТЦК та СП, 02.09.2025, РНОКПП: 3344514975"
    res = extract_rtzk(text)
    assert res == "Миколаївським МТЦК та СП"

    text = "Призваний 28.08.2024 року Вознесенським РТЦК та СП м. Вознесенськ Миколаївської області."
    res = extract_rtzk(text)
    assert res == "Вознесенським РТЦК та СП м. Вознесенськ Миколаївської області"

    text = "розлучений. Призваний  20.05.2025, Оболонським РТЦК , 3107111114. Н"
    res = extract_rtzk(text)
    assert res == "Оболонським РТЦК"

    # відсутність Призваний
    text = "БУЙНОВ Олександр Олександрович, солдат, військовослужбовець військової служби за призовом, військової частини А0224, розвідник-сапер 2 відділення взводу інженерної розвідки інженерно-саперної роти військової частини А0224, 05.07.1987 року народження, українець, освіта середня, не одружений. Салтівським РТЦК та СП Харківська область, 01.10.2025 року, РНОКПП 3111111119. Номер мобільного телефону +38063333334 "
    res = extract_rtzk(text)
    assert res == "Салтівським РТЦК та СП Харківська область"

    # виправлення рцтк на ртцк
    text = "БУЙКО Богдан Васильович, старший сержант, військовослужбовець військової служби за призовом, колишній гранатометник 1 десантно-штурмового відділення 1 десантно-штурмового взводу 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 14.05.1979 року народження, українець, освіта середня-спеціальна, Авіаційна школа м. Гайсин у 1997 році, одружений. Призваний Сихівським  РЦТК та СП Львівської області, 21.04.2025 року. РНОКПП 2811111118. Паспорт КА 111111. Номер мобільного телефону (067) 1111111"
    res = extract_rtzk(text)
    assert res == "Сихівським РТЦК та СП Львівської області"

    text = "БУЙКО Юрій Юрійович, солдат, військовослужбовець військової служби за мобілізацією, водій-електрик-моторист 1 відділення взводу розвідки та корегування роти безпілотних систем 1 десантно-штурмового батальйону військової частини А0224, зарахований до списків військової частини А0224 23.08.2025, 10.02.1986 року народження, українець, освіта середня не повна, одружений. Призваний 3-ім відділом Одеського РТЦК та СП Одеської області, 22.08.2025, РНОКПП  3111111117. Військовий квиток АГ №411111. Номер мобільного телефону +380911111114. Адреса проживання військовослужбовця: м. Одеса вул. Жуліо Кюрі буд. 11 кв. 111."
    res = extract_rtzk(text)
    assert res == "3-ім відділом Одеського РТЦК та СП Одеської області"

    text = "батальйону військової частини А0224, зарахований до списків військової частини А0224 15.06.2025, 09.03.1995 року народження, українець, освіта професійно-технічна, неодружений. Призваний 1-відділом Ізмаїльського РТЦК та СП м. Ізмаїл Одеської області, 14.06.2025 року. "
    res = extract_rtzk(text)
    assert res == "1-відділом Ізмаїльського РТЦК та СП м. Ізмаїл Одеської області"

    text = "забезпечення батареї перехоплювачів безпілотних літальних апаратів зенітного ракетного дивізіону військової частини А0224, 04.05.2000 року народження, українець, освіта середня-технічна, неодружений. Призваний Горішньоплавнінським ОМВК Полтавської області 26.08.2020. РНОКПП 3611111111. Паспорт (НЕ 711111). Номер мобільного телефону "
    res = extract_rtzk(text)
    assert res == "Горішньоплавнінським ОМВК Полтавської області"

    text = "ЗАЛУЖНИЙ Едуард Павлович, старший солдат, військовослужбовець військової служби за мобілізацією, старший майстер ремонтного взводу бронетанкової техніки ремонтної роти батальйону логістики військової частини А0224, 16.01.2001 року народження, українець, освіта середня-спеціальна, одружений. Призваний 26.02.2022 року Вінницьким ОМЦТК та СП м. Вінниця., РНОКПП №3611111112, "
    res = extract_rtzk(text)
    assert res == "Вінницьким ОМТЦК та СП м. Вінниця"

    text = "Призваний Полтавським РТЦК та СП в місті Полтава, Полтавської області, 01.07.2024. РНОКП"
    res = extract_rtzk(text)
    assert res == "Полтавським РТЦК та СП в місті Полтава, Полтавської області"

    text = "освіта вища, неодружений. Призваний Кропивницьким міським РТЦК та СП в м. Кропивницький, Кіровоградської області, з 24.08.2025. РНОКПП 3111113138."
    res = extract_rtzk(text)
    assert res == "Кропивницьким міським РТЦК та СП в м. Кропивницький, Кіровоградської області"

    text = "ЧАБАН Григорій Костянтинович, солдат, військовослужбовець військової служби за призовом, гранатометник 1 аеромобільного відділення 1 аеромобільного взводу 2 аеромобільної роти аеромобільного батальйону військової частини А0224, зарахований до списків військової частини А0224 31.01.2026, 28.12.1997 року народження, українець, освіта середня, не одружений. Призваний Вознесенським РТЦК та СП Миколаївська обл., 31.01.2026 року. РНОКПП 3579107714. Паспорт ЕР528816. Номер мобільного телефону +380662991924. Адреса проживання військовослужбовця: Миколаївська обл., м. Вознесенськ, вул. Травнева, буд 97. Близькі родичі: Брат: ЧАБАН Костянтин Костянтинович, номер мобільного телефону +380736252383."
    res = extract_rtzk(text)
    assert res == ("Вознесенським РТЦК та СП Миколаївська обл")

def test_rtzk_region_extraction(processor_factory, mock_logger):

    text = "Призваний Центральним РТЦК та СП м. Київ 06.12.2024 року. "
    res = extract_region(text)
    assert "Київська область" in res

    text = "Призваний Київським РТЦК та СП"
    res = extract_region(text)
    assert "Київська область" in res

    text = "Призваний Центральним РТЦК та СП м. Обухів, Київська обл."
    res = extract_region(text)
    assert "Київська область" in res

    text = "Призваний Новокодацьким РТЦК та СП м. Дніпра 06.12.2024 року. "
    res = extract_region(text)
    assert "Дніпропетровська область" in res

    text = "Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52"
    res = extract_region(text)
    assert "Кіровоградська область" in res

    text = "Чернівецька обл., м. Олександрія, вул. Сумська, буд. 16 кв. 52"
    res = extract_region(text)
    assert "Чернівецька область" in res

    text = "Кропивницьким РТЦК та СП, м. Кропивницький"
    res = extract_region(text)
    assert "Кіровоградська область" in res

    text = "Кропивницький МТЦК та СП."
    res = extract_region(text)
    assert "Кіровоградська область" in res

    text = "Кам’янський РТЦК та СП м. Кам’янка Дніпропетровської області"
    res = extract_region(text)
    assert "Дніпропетровська область" in res

    text = "Київський РТЦК та СП м. Одеса"
    res = extract_region(text)
    assert "Одеська область" in res

    text = "Дубинським РТЦК та СП Рівненської обл."
    res = extract_region(text)
    assert "Рівненська область" in res

    text = "Миколаївський РТЦК та СП"
    res = extract_region(text)
    assert "Миколаївська область" in res

    text = "місто Вінниця, вулиця Нагірна 21ж, квартира 21."
    res = extract_region(text)
    assert "Вінницька область" in res




def test_desertion_region_extraction(processor_factory, mock_logger):

    text = "26.02.2026 року близько 08:00 години, під час перевірки наявності особового складу був відсутній солдат БУЙКО Олександр Васильович, який самовільно залишив район тимчасового місця розосередження підрозділу військової частини А0224 під час повітряної тривоги. Пошук військовослужбовця в районі зосередження підрозділу поблизу міста Миколаєва, Миколаївської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме. Решта обставин з'ясовується. "
    res = extract_desertion_region(text)
    assert "Миколаївська область" in res

    text = "не прибув після стаціонарного лікування в КНП «Лисянська територіальна лікарня» ЛСРЧО Черкаської обл., на телефонні дзвінки не відповідає. Пошук військовослужбовця в районі тимчасового місці перебування підрозділу поблизу н.п.Вознесенське Миколаївської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме"
    res = extract_desertion_region(text)
    assert "Миколаївська область" in res

    text = "близько 20:00 години, під час звірки з медичною службою було виявлено відсутність актуальних даних про стаціонарне лікування/реабілітацію солдата БУЙКО Михайла Васильовича, до району виконання завдання військовослужбовець не повертався.  Пошук військовослужбовців в районі зосередження підрозділом в н. п. Бажани Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовців невідоме."
    res = extract_desertion_region(text)
    assert "Дніпропетровська область" in res

    text = "До моменту підтвердження або спростування факту проходження військово-лікарської комісії вважати старшого сержанта БУЙКО Андрія Олександровича таким, що самовільно перестав проходити військово-лікарську комісію та не повернувся до району зосередження 6 десантно-штурмової роти 2 десантно-штурмового батальйону поблизу населеного пункту Мар’їна Роща Дніпропетровської області. Місцезнаходження військовослужбовця невідоме, на телефонні дзвінки не відповідає"
    res = extract_desertion_region(text)
    assert "Дніпропетровська область" in res

    text = "відсутній старший солдат за призовом БУЙКО Володимир Васильович, який самовільно залишив район тимчасового місця розосередження підрозділу військової частини А0224, вважати таким що здійснив СЗЧ. Пошук військовослужбовця в районі тимчасового місці перебування підрозділу поблизу міста Миколаєва позитивного результату не приніс. М"
    res = extract_desertion_region(text)
    assert "Миколаївська область" in res

    text = "17.02.2026 близько 08:55 під час перевезення солдата за призовом БУЙКО Панаса Володимировича до КНП “ООМЦПЗ” ООР м. Одеса на перехресті вулиці Вадима Благовісного і Великої Морської під час з"
    res = extract_desertion_region(text)
    assert "Одеська область" in res

    text = "30.11.2025 з нц"
    res = extract_desertion_region(text)
    assert "Житомирська область" in res

    text = "ген Петрович вибув на лікування до КНП «Міської лікарні №4» Запорізької міської ради."
    res = extract_desertion_region(text)
    assert "Запорізька область" in res


def test_desertion_locality_extraction(processor_factory, mock_logger):

    text = "Пошук військовослужбовця в районі зосередження підрозділом в населеному пункті Хороше Дніпропетровської області позитивного результату не приніс, на телефонні дзвінки не відповідає"
    res = extract_locality(text)
    assert res == 'Хороше'

    text = "Пошук військовослужбовця в районі зосередження підрозділом в н.п. Богданівка Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме. "
    res = extract_locality(text)
    assert res == 'Богданівка'

    text = "Пошук військовослужбовця в районі зосередження підрозділом в с. Богданівка Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме."
    res = extract_locality(text)
    assert res == 'Богданівка'

    text = "18.03.2026 близько 19:30 години, під час перевірки наявності особового складу в районі зосередження підрозділом поблизу с.Дмитрівка Дніпропетровської області, було виявлено відсутність солдата БУБУ Вадима Вікторовича, який самовільно залишив район виконання завдання за призначенням. "
    res = extract_locality(text)
    assert res == 'Дмитрівка'

    text = "Пошук військовослужбовця в районі зосередження підрозділом в населеному пункті Нова Дмитрівка Дніпропетровської області позитивного результату не приніс, на телефонні дзвінки не відповідає"
    res = extract_locality(text)
    assert res == 'Нова Дмитрівка'

    text = "Пошук військовослужбовця в районі зосередження підрозділом в населеному пункті Ново-Дмитрівка Дніпропетровської області позитивного результату не приніс, на телефонні дзвінки не відповідає"
    res = extract_locality(text)
    assert res == 'Ново-Дмитрівка'

    text = "Пошук військовослужбовця в районі зосередження підрозділом поблизу села Ново-Дмитрівка Дніпропетровської області позитивного результату не приніс, на телефонні дзвінки не відповідає"
    res = extract_locality(text)
    assert res == 'Ново-Дмитрівка'

    text = "Пошук військовослужбовця в районі зосередження підрозділу поблизу населеного пункту Вербки Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме, на зв’язок не виходить."
    res = extract_locality(text)
    assert res == 'Вербки'

    text = "Пошук військовослужбовця в районі зосередження підрозділом поблизу міста Миколаєва, Миколаївської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме. Решта обставин з'ясовується."
    res = extract_locality(text)
    assert res == 'Миколаєва'

    text = "Пошук військовослужбовця в районі зосередження підрозділу поблизу м. Павлоград Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме. Решта обставин з'ясовується."
    res = extract_locality(text)
    assert res == 'Павлоград'

    text = "Пошук військовослужбовця в районі зосередження підрозділом в н.п. Мар’янівка Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме. Решта обставин з'ясовується."
    res = extract_locality(text)
    assert res == 'Мар’янівка'


def test_conscription_date(processor_factory, mock_logger):

    text = "БУЙНОВ Олег Леонідович, Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків. РНОКПП відомості не надано"
    res = extract_conscription_date(text)
    assert res == NA

    text = "БУЙНОВ Сергій Володимирович, солдат, військовослужбовець військової служби за призовом, стрілець-номер обслуги 1 десантно-штурмового відділення 2 десантно-штурмового взводу 3 десантно-штурмової роти 1 десантно-штурмового батальйону військової частини А0224, 21.09.1981 року народження, українець, освіта фахова передвища (молодший спеціаліст), не одружений. Призваний  Вознесенським РТЦК та СП Миколаївської області, 11.11.2025. РНОКПП 2111111111. Паспорт 001111111, виданий 4831 31.08.2017. Номер мобільного телефону +380681111115"
    res = extract_conscription_date(text)
    assert res == "11.11.2025"

    text = "БУЙНОВ Олег Леонідович, солдат, 23.07.1993 року народження, ВІН 010521111111111111104, ІПН 3111111110, паспорт 011111111 виданий 0510 від 01.11.2019 призваний 04.02.2026 Вінницьким ОМТЦК ти СП, закінчив Вінницький державний педагогічний університет у 2016р. вчитель фізкультури, номер мобільного телефону 0961111114. Адреса проживання військовослужбовця: м. Вінниця, вул. Покришкіна 11в. Близькі родичі: Батько НЕКЛЮДОВ Леонід Миколайович, тел. 0671111120"
    res = extract_conscription_date(text)
    assert res == "04.02.2026"

    text = "БУЙНОВ Олег Леонідович, Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків, 25.10.2025 року. РНОКПП відомості не надано"
    res = extract_conscription_date(text)
    assert res == "25.10.2025"

    # відсутність Призваний
    text = "БУЙНОВ Олександр Олександрович, солдат, військовослужбовець військової служби за призовом, військової частини А0224, розвідник-сапер 2 відділення взводу інженерної розвідки інженерно-саперної роти військової частини А0224, 05.07.1987 року народження, українець, освіта середня, не одружений. Салтівським РТЦК та СП Харківська область, 01.10.2025 року, РНОКПП 3111111119. Номер мобільного телефону +38063333334 "
    res = extract_conscription_date(text)
    assert res == "01.10.2025"


    text = "БУЙНОВ Олександр Олександрович, 1 десантно-штурмового взводу 8 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 12.07.1988 року народження, українець, Повна середня ЗОШ №1 ім. В.О.Сухомлинського, с.Павлиш, 2006, 11 класів, не одружений. Олександрійським РТЦК та СП. м. Олександрія Кіровоградська обл., 21.12.2025 року. РНОКПП 3111111114. Паспорт ЕВ111113. Номер мобільного телефону +38(099)111 11 11; +38 (050) 112 22 22."
    res = extract_conscription_date(text)
    assert res == "21.12.2025"

    text = "Військовослужбовець військової частини А0224, призваний під час мобілізації, відряджений до військової частини А2900, курсант 4 зведеної навчальної роти зведеного навчального батальйону Граніт-2 військової частини А2900 старший солдат БУЙНОВ Сергій Ігорович, 25.06.1997 року народження. Українець. Адреса проживання: Миколаївська обл. м. Новий Буг, вул. Горбачева, буд. 85. Освіта: професійно-технічна. Сімейний стан: одружений. ІН 3111111592. Військовий квиток: АГ 111184. Призваний 21.02.2026 Баштанським РТЦК т а СП м. Миколаїв. Базову загальновійськову підготовку не пройшов. Близькі родичі та члени родини: Дружина: Крилова Анна Андріївна, тел. +380911111909."
    res = extract_conscription_date(text)
    assert res == "21.02.2026"


def test_address_extraction(processor_factory, mock_logger):
    text = "телефону +38(096)-896-7925. Близькі родичі: Батьки померли. Адреса реєстрації військовослужбовця: Запорізька обл, м. Василівка, вул. Кірова буд. 25."
    res = extract_address(text)
    assert res == 'Запорізька обл, м. Василівка, вул. Кірова буд. 25'

    text = "Батько: Моторко Анатолій Федорович, 1959 р.н., (063)-791-89-31. Адреса проживання військовослужбовця: Миколаївська обл, с. Федорівне, вул. Степова буд. 7."
    res = extract_address(text)
    assert res == 'Миколаївська обл, с. Федорівне, вул. Степова буд. 7'

    text = "ГАВНОВ Юрій Азізович, військовослужбовець військової служби за мобілізацією, стрілець-снайпер 3 аеромобільного відділення 1 аеромобільного взводу 2 аеромобільної  роти аеромобільного батальйону, 21.08.1982 року народження, українець, освіта середня спеціальна. Призваний Олександрійським РТЦК та СП м. Кіровоградської обл., 17.12.2025 року, РНОКПП 3383322233, номер мобільного телефону 068-622-22-44. Адреса проживання військовослужбовця: Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52. Мати: ФІБЕРГ Марта Яківна, дані потребують уточнення. Дружина: ФІБЕРГ Катерина Валеріївна, тел. 067-964-02-74. А"
    res = extract_address(text)
    assert res == 'Кіровоградська обл., м. Олександрія, вул. Перспективна, буд. 16 кв. 52'

    text = "Самарським РТЦК та СП Дніпропетровської області 11.04.2025, освіта середня, одружений. Адреса проживання військовослужбовця: Дніпропетровська область, м. Дніпро, вул. Новокримська 7 кв 9. РНОКПП: 3311111910 Номер телефону: 0991111142 Близькі родичі: дружина ЗАЛУЖНА Оксана Володимирівна 20.11.1979, Дніпропетровська область, м. Дніпро, вул. Новокримська 1 кв 1, 0931111132"
    res = extract_address(text)
    assert res == 'Дніпропетровська область, м. Дніпро, вул. Новокримська 7 кв 9'


def test_phone_extraction(processor_factory, mock_logger):
    text = "номер мобільного телефону (095) 64 73225. Адреса "
    res = extract_phone(text)
    assert res == '0956473225'

    text = "номер мобільного телефону +380505184441. Близькі родичі:"
    res = extract_phone(text)
    assert res == '0505184441'

    text = "номер мобільного телефону +3-80-505 184441. Близькі родичі:"
    res = extract_phone(text)
    assert res == '0505184441'

    text = "моб. тел +3-80 505 184441. Близькі родичі:"
    res = extract_phone(text)
    assert res == '0505184441'

def test_where_desertion_extraction(processor_factory, mock_logger):
    text = "30.01.2026 від тимчасово виконуючого обов’язки командира 4 аеромобільної роти аеромобільного батальйону надійшла доповідь про факт неповернення з лікування до району виконання завдання за призначенням військовослужбовця військової частини А0224 (без зброї)."
    file_name = '30.01.2026 СЗЧ з лікування ГАВНОВ Р.О. 4 аемр аемб.docx'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "05.02.2026 від командира аеромобільного батальйону надійшла доповідь про факт відсутності військовослужбовця військової частини А0224 в медичному закладі куди був спрямований на стаціонарне проходження військово-лікарської комісії з пункту тимчасового розташування підрозділу с. Вознесенське Миколаївської області."
    file_name = '05.02.2026 СЗЧ з лікування ГАВНОВ В.Є. 4 аемр аемб.docx'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "10.02.2026 року від командира 3 десантно-штурмового батальйону надійшла доповідь про факт неповернення з лікування до району виконання завдання за призначенням військовослужбовця військової частини А0224 солдата ГАВНОВА Миколи Анатолійовича. 10.02.2026року солдат ГАВНОВ Микола Анатолійович не повернувся з лікування до району виконання завдання за призначенням. Солдат ГАВНОВ Микола Анатолійович лікувався в Національному військово-медичному клінічному центрі госпіталю м. Київ з 28.01.2026 по 09.02.2026 року. На зв’язок не виходить документів, які підтверджують проходження лікування в інших медичних закладах не надав. До військової частини А0224 не повернувся. Пошук військовослужбовця в районі зосередження підрозділом в н.п. Українське Дніпропетровської області позитивного результату не приніс. Місцезнаходження військовослужбовця невідоме."
    file_name = '10.02.2026 СЗЧ неповернення з  лікування до РВБЗ (Гавнов М.А.) зрв 3 дшб(2)'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "11.02.2026 від командира 4 десантно-штурмової роти 1 десантно-штурмового батальйону надійшла доповідь про факт неповернення з лікування до військової частини військовослужбовцем військової частини А0224."
    file_name = '11.02.2026 СЗЧ неповернення 4дшр 1дшб ЩЕРБИНА А.В..docx'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "05.02.2026 від командира самохідного артилерійського дивізіону військової частини А0224 надійшла доповідь про факт неповернення після проходження військово-лікарської комісії до району виконання завдання за призначенням військовослужбовцем військової частини А0224."
    file_name = '08.02.2025 СЗЧ несвоєчасне прибуття ГАВНОВ О.Ю. 1 сабатр САДн.docx'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "13.02.2026 року солдат БУЙНОВ Станіслав Миколайович не прибув з військово-лікарської комісії до району виконання завдання за призначенням, документів що підтверджують продовження лікування в інших лікувальних закладах не надав."
    file_name = '16.02.2026 СЗЧ неповернення після проходження ВЛК (Буйнов С.М.) рв 3 дшб(2).doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "03.02.2026 старший солдат МУДІК Олександр Сергійович вибув з постійного пункту дислокації (н.п. Вознесенське Миколаївської області) військової частини А0224 (переміщення) до військової частини А5291, відповідно наказу НГШ ЗСУ №122-РС від 17.01.2026. До військової частини А5191 не прибув 04.02.2021, згідно повідомлення військової частини А5291 (акт прийому поповнення вх. №111 від 14.02.2021). До військової частини А0224 не повернувся."
    file_name = '09.02.2021 СЗЧ неприбуття (переміщення) до військової частини А5291 (Мудік О.С.) 11 дшр 3 дшб.doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'ППД'

    text = "03.02.2026 старший солдат МУДІК Олександр Сергійович вибув з постійного пункту дислокації (н.п. Вознесенське Миколаївської області) військової частини А0224 (переміщення) до військової частини А5291, відповідно наказу НГШ ЗСУ №122-РС від 17.01.2026. До військової частини А5191 не прибув 04.02.2021, згідно повідомлення військової частини А5291 (акт прийому поповнення вх. №111 від 14.02.2021). До військової частини А0224 не повернувся."
    file_name = '09.02.2021 СЗЧ неприбуття (переміщення) до військової частини А5291 (Мудік О.С.) 11 дшр 3 дшб.doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'ППД'

    text = "10.02.2026 року від командира 1 десантно-штурмового батальйону військової частини А0224 надійшла доповідь про факт повернення після самовільного залишення району виконання бойового завдання військовослужбовця військової частини А0224."
    file_name = '10.02.2026 повернення після СЗЧ з поля бою ГАВНОВ О. С. 1дшр 1дшб.doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'РВБЗ'

    text = "09.02.2026 року від ТВО командира 2 зведеної роти надійшла доповідь про факт не прибуття після відпустки за станом здоров'я до пункту постійної дислокації військовослужбовця військової частини А0224 .09.02.2026 року при перевірці наявності особового складу у місці розосередження особового складу н.п. Вознесенське Миколаївської області був відсутній солдат за призовом АЛЕКСЄЄВ Віталій Віталійович ( не прибув з відпустки за станом здоров’я) до ППД в/ч А0224 н.п. Вознесенське Миколаївської області. Пошук військовослужбовця в районі тимчасового місці перебування підрозділу поблизу с. Вознесенське Миколаївської області позитивного результату не приніс, на телефонні дзвінки не відповідає. Місцезнаходження військовослужбовця невідоме. Прошу вважати таким, що здійснив СЗЧ. "
    file_name = '09.02.2026 не прибутя з ВПХ 8 дшр 2 дшб  АЛЕКСЄЄВ В.В...doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'відпустки'

    text = "09.02.2026 року від командира 5 десантно-штурмової роти 2 десантно-штурмового батальйону надійшла доповідь про факт повернення після самовільного залишення військової частини А0224 солдата ГАВНОВА Євгенія Миколайовича. 08.02.2026 року близько 20:00 години під час перевірки наявності особового складу в районі зосередження підрозділом поблизу н.п. Бажани Дніпропетровської області було виявлено факт повернення солдата ГАВНОВА Євгенія Миколайовича, після неповернення з відпустки за станом здоров’я до району виконання завдання за призначенням 25.12.2025 року.  Решта обставин з'ясовується."
    file_name = '09.02.2026 повернення після СЗЧ 5 дшр 2 дшб ГАВНОВ Є.М.doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'відпустки'

    text = "30.11.2025 року від командира 2 зведеної роти надійшла доповідь про факт не прибуття після проходження курсу БЗВП до пункту постійної дислокації військовослужбовця військової частини А0224 "
    file_name = '09.02.2026 не прибуття з БЗВП 6 дрш 2 дшб БУЙНОВ ВВ.doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'НЦ'

    text = "солдат ЗАЛУЖНИЙ Микола Ігорович не повернувся з військово-лікарської комісії до району виконання завдання за призначенням. Солдат ЗАЛУЖНИЙ Микола Ігорович 16.03.2026 року прибув до військової частини А1446 для обстеження військово-лікарською комісією. 23.04.2026 року надійшло повідомлення від військової частини А1446 про те, що 21.04.2026 року ЗАЛУЖНИЙ Микола Ігорович виключений з обстеження військово-лікарською комісією у зв'язку з ухиленням від його проходження"
    file_name = '23.04.2026 СЗЧ неповернення з ВЛК до РВБЗ (ЗАЛУЖНИЙ М.І.) рбс 3 дшб(4).doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'лікування'

    text = "під час звірки даних по особового складу було виявлено відсутність солдата ЗАЛУЖНИЙ Владислава Валерійовича, який не повернувся після відрядження до району виконання завдання за призначенням у встановлений термін"
    file_name = '23.04.2026 СЗЧ неповернення з РВБЗ (ЗАЛУЖНИЙ М.І.) рбс 3 дшб(4).doc'
    res = extract_desertion_place(text, file_name)
    assert res == 'відрядження'

def test_milsubunit_extraction(processor_factory, mock_logger):

    text = "ГАВНОВ Віталій Сергійович, солдат, військовослужбовець військової служби за призовом, розвідник-санітар 2 розвідувального відділення розвідувального взводу 1 десантно-штурмового батальйону військової частини А0224, 30.07.1986 року народження, українець, освіта середня . Призваний"
    file_name = '09.02.2026 СЗЧ РВБЗ ГАВНОВ А. С. РВ 1ДШБ.docx'
    res = extract_military_subunit(text, file_name)
    assert res == '1 дшб'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'РВ'

    text = "ГАВНОВ Віталій Сергійович, військовослужбовець військової служби за призовом, оператор безпілотних літальних апаратів 2 відділення перехоплювачів безпілотних літальних апаратів 2 взводу перехоплювачів безпілотних літальних апаратів батареї перехоплювачів безпілотних літальних апаратів зенітного ракетного дивізіону військової частини А0224, 11.08.2001 року народження, Українець, освіта вища, "
    file_name = '09.02.2026_СЗЧ_з_району_ГАВНОВ_Бат_ПБпЛА_ЗРДн.docx'
    res = extract_military_subunit(text, file_name)
    assert res == 'ЗРДн'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'БатПБПЛА'

    text = "ГАВНОВ Леонід Генадійович, старший солдат, військовослужбовець військової служби за мобілізацією, старший навідник 2 артилерійського взводу 2 артилерійської батареї самохідного артилерійського дивізіону військової частини А0224"
    file_name = '09.02.2026_СЗЧ_з_РВБЗ_2_АБАТР_САДН__БІЖКО_Л.Г..doc'
    res = extract_military_subunit(text, file_name)
    assert res == 'САДн'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '2 арт. Батарея'

    text = "ГАВНОВ Леонід Генадійович, старший солдат, військовослужбовець військової служби за мобілізацією, старший навідник 2 артилерійського взводу 1 артилерійської батареї самохідного артилерійського дивізіону військової частини А0224"
    file_name = '09.02.2026_СЗЧ_з_РВБЗ_2_АБАТР_БІЖКО_Л.Г..doc'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT_MAPPING)
    assert res == 'САДн'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '1 арт. Батарея'

    text="оператор безпілотних літальних апаратів взводу інженерних безпілотних наземних систем інженерно – саперної роти військової частини А0224, 26.06.1987 року народження, українець,"
    file_name = ''
    res = extract_military_subunit(text, file_name)
    assert res == 'ІСР'

    text = "ДУМБА Дмитро Миколайович, солдат, військовослужбовець військової служби за призовом, оператор безпілотних літальних апаратів 6 відділення 2 взводу ударних безпілотних авіаційних комплексів роти безпілотних систем аеромобільного батальйону військової частини А022"
    file_name = '11.02.2026 СЗЧ з РВБЗ АЕМБ РБС ДУМБА Д.М.doc'
    res = extract_military_subunit(text, file_name)
    assert res == 'АЕМБ'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'РБС'

    text = "ДУМБА Іван Іванович, солдат, військовослужбовець військової служби за мобілізацією, навідник 1 аеромобільного відділення 1 аеромобільного взводу 4 аеромобільної роти аеромобільного батальйону військової частини А0224"
    file_name = "04.02.2026 СЗЧ з РВБЗ ДУМБА І.І. 4 аемр аемб.docx"
    res = extract_military_subunit(text, file_name)
    assert res == 'АЕМБ'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == '4 аемр'

    text = "ДУМБА Юрій Олександрович, старший солдат, військовослужбовець військової служби за мобілізацією, водій 2 автомобільного відділення 1 автомобільного взводу підвозу боєприпасів автомобільної роти підвозу боєприпасів батальйону логістики військової частини А0224, 16.09.1979 року народження"
    file_name = ""
    res = extract_military_subunit(text, file_name)
    assert res == 'БЛ'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'Автомобільна рота підвозу боєприпасів'

    text = "ДУМБА Сергій Васильович, солдат, військовослужбовець військової служби за мобілізацією, водій 3 відділення 2 автомобільного взводу автомобільної роти батальйону логістики військової частини А0224, дата народження: 07.11.1979"
    file_name = ""
    res = extract_military_subunit(text, file_name)
    assert res == 'БЛ'
    res = extract_military_subunit(text, file_name, mapping=PATTERN_SUBUNIT2_MAPPING)
    assert res == 'Автомобільна рота'

    text = "ДУМБА Дмитро Андрійович, солдат, за призовом під час мобілізації, водій-електрик БУ, 07.09.1997р.н."
    file_name = ""
    res = extract_military_subunit(text, file_name)
    assert res == 'БУ'

    text = "ДУМБА Олександр Миколайович, сержант, військовослужбовець військової служби за мобілізацією, водій автомобільного відділення взводу забезпечення батальйону управління військової частини А0224, 05.02.1995 року народження"
    file_name = ""
    res = extract_military_subunit(text, file_name)
    assert res == 'БУ'

    text = "БУЙКО Олександр Васильович, солдат, військовослужбовець військової служби за призовом, солдат резерву запасної роти військової частини А0224, зарахований до списків військової частини А0224 22.02.2026, 29.04.1991 року народження, українець, освіта вища, одружений. Призваний Баштанським РТЦК та СП, Миколаївської області, 22.02.2026 року, РНОКПП 3111111111. Військовий квиток АГ №111115. Номер мобільного телефону +380911111110. Адреса проживання військовослужбовця: Миколаївська область, Баштанський район, с. Вільне Запоріжжя, вул. Москаленка 334."
    file_name = ""
    res = extract_military_subunit(text, file_name)
    assert res == 'Зап рота'

def test_desertion_type_extraction(processor_factory, mock_logger):

    text = "16.02.2026 близько 14:00 солдат БУЙНОВ Антон Олександрович, солдат БАРАНЧУК Максим Володимирович та солдат СКАЧКУК Сергій Іванович здійснили самовільне залишення району виконання бойового завдання підрозділом поблизу населеного пункту Шевченко Добропільської міської громади Покровського району Донецької області. Військовослужбовець: солдат БУЙНОВ Антон Олександрович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6811118, набої 5,45 x 39 в кількості 400 шт., граната DM52 – 2 шт.) солдат БАРАНЧУК Максим Володимирович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6811119, набої 5,45 x 45 в кількості 400 шт., граната DM52 – 2 шт.) солдат СКАЧКУК Сергій Іванович з особистою зброєю (5,45 x 39 мм автомат АК-74, номер зброї 6722224, набої 5,45 x 39 в кількості 400 шт"
    where = extract_desertion_place(text)
    assert where == 'РВБЗ'
    res = extract_desertion_type(text, where)
    assert res == 'СЗЧ зброя'
    cc = extract_cc_article(res)
    assert cc == '429'

    text = "22.12.2025 року близько 09:00 години солдат БУЙНОВ Дмитро Анатолійович здійснив самовільне залишення району виконання бойового завдання підрозділом поблизу населеного пункту Мирноград Донецької області. Військовослужбовець, солдат БУЙНОВ Дмитро Анатолійович з особистою зброєю (5,56 x 45 мм штурмова гвинтівка CZ Bren 2, номер зброї J103408, набої 5,56 x 45 в кількості 150 шт.) залишив позицію та убув у невідомому напрямку. "
    where = extract_desertion_place(text)
    assert where == 'РВБЗ'
    res = extract_desertion_type(text, where)
    assert res == 'СЗЧ зброя'
    cc = extract_cc_article(res)
    assert cc == '429'

    text = "28.04.2026 близько 19:30 від доповіді командира зведеного підрозділу 3 десантно-штурмового батальйону військової частини А0224 лейтенанта Косого Ігоря Валентиновича стало відомо, що старший сержант Залужний Олександр Андрійович, сержант із матеріального забезпечення 10 десантно-штурмової роти 3 десантно-штурмового батальйону військової частини А0224, який переданий в підпорядкування командира 3 батальйону морської піхоти військової частини А4765 самовільно залишив нове місце розташування підрозділу поблизу населеного пункту Шахтарське Синельниківського району Дніпропетровської області з особистою зброєю (9мм ПМ №ЛУ3335). Засоби індивідуального захисту та інвентарне майно старшого сержанта Залужного Олександра Андрійовича перебувають в розташуванні підрозділу. "
    res = extract_desertion_type(text, where)
    assert res == 'СЗЧ зброя'
    cc = extract_cc_article(res)
    assert cc == '429'

    text = "22.12.2025 року під час перевірки наявності особового складу був відсутній солдат БУЙНОВ Андрій Валентинович, який самовільно залишив район виконання завдання за призначенням. Пошук військовослужбовця в районі зосередження підрозділу в н.п. Шахтарське Дніпропетровської області позитивного результату не приніс. Місце знаходження військовослужбовця невідоме."
    where = extract_desertion_place(text)
    assert where == 'РВБЗ'
    res = extract_desertion_type(text, where)
    assert res == DEFAULT_DESERTION_TYPE
    cc = extract_cc_article(res)
    assert cc == '407'

    text = "05.04.2026 року від командира 11 десантно-штурмової роти 3 десантно-штурмового батальйону військової частини А0224 надійшла доповідь про факт неповернення з пункту постійної дислокації військової частини А0224 (н.п. Вознесенське, Миколаївської області) до району виконання завдання за призначенням військовослужбовця військової частини А0224. 05.04.2026 року близько 08:00 години, під час перевірки наявності особового складу в районі зосередження підрозділу 11 десантно-штурмової роти 3 десантно-штурмового батальйону військової частини А0224 в н.п. Вереміївка Дніпропетровської області було виявлено відсутність солдата ЗАЛУЖНОГО Романа Михайловича, який не повернувся до району зосередження підрозділу військової частини А0224. "
    where = extract_desertion_place(text)
    assert where == 'ППД'

def test_return_sign(processor_factory, mock_logger):
    processor = processor_factory("any.docx")

    text = "03.06.2022 року солдат БОЛВАН Іван Васильович не повернувся з лікування до району виконання завдання за призначенням."
    assert False == processor._check_return_sign(text)

    text = "20.03.2026 року солдат БОЛВАН Ігор Миколайович, не повернувся після відпустки за рішенням військово лікарської комісії до району виконання завдання за призначенням. 07.01.2026 року за направленням військової частини А0224 №11 вибув до військової частини А4615. З 07.01.2026 по 15.01.2026 КНП “Дніпропетровська обласна клінічна лікарня ім І.І. Мечникова”. 17.01.2026 пройшов військово лікарську комісію довідка №2026-1111-1111-4849-0 від 17.01.2026 надана відпустка на 30 діб. 17.02.2026 пройшов військово лікарську комісію довідка №2026-1111-2111-5477-7 від 17.02.2026 надана відпустка на 30 діб. Від військової частини отримав відпускний лист №257 від 19.02.2026, відпустка з 18.02.2026 по 19.03.2026, 20.03.2026 дата повернення до військової частини"
    assert False == processor._check_return_sign(text)

    text = "16.02.2026 року від командира 1 десантно-штурмового батальйону військової частини А0224 надійшла доповідь про факт повернення після самовільного залишення району виконання бойового завдання військовослужбовця військової частини А0224. 16.02.2026 року близько 18:00 години під час перевірки наявності особового складу в районі зосередження підрозділом в н.п. Вознесенське Миколаївської області було виявлено факт повернення молодшого сержанта БУЙКО Олександра Сергійовича , після самовільного залишення району виконання завдання за призначенням з 15.12.2023 рок"
    assert True == processor._check_return_sign(text)


    file_name = "21.03.2026 Повернення особистої зброї (Бамбуля С.І перебуває в СЗЧ) рв 3 дшб(2).doc"
    is_return_doc = bool(re.search(PATTERN_RETURN_SIGN_IN_FILE, file_name))
    assert False == is_return_doc

    file_name = "20.03.2026 СЗЧ неповернення з лікування (Бамбуля ВО.) рбс 3 дшб.doc"
    is_return_doc = bool(re.search(PATTERN_RETURN_SIGN_IN_FILE, file_name))
    assert False == is_return_doc

    file_name = "18.03.2026 повернення після СЗЧ Бамбуля Д. Є. 1 дшр 1 дшб.docx"
    is_return_doc = bool(re.search(PATTERN_RETURN_SIGN_IN_FILE, file_name))
    assert True == is_return_doc

    text = "21.04.2026 року солдат БАМБУЛЯ Микола Ігорович не повернувся з військово-лікарської комісії до району виконання завдання за призначенням. Солдат БАМБУЛЯ Микола Ігорович 16.03.2026 року прибув до військової частини А1446 для обстеження військово-лікарською комісією. 23.04.2026 року надійшло повідомлення від військової частини А1446 про те, що 21.04.2026 року БАМБУЛЯ Микола Ігорович виключений з обстеження військово-лікарською комісією у зв'язку з ухиленням від його проходження. До військової частини А0224 не повернувся. Пошук військовослужбовця в районі зосередження підрозділу в н.п. Українське Дніпропетровської області позитивного результату не приніс, на телефонні дзвінки не відповідає. Місцезнаходження військовослужбовця невідоме. Решта обставин з'ясовується."
    assert False == processor._check_return_sign(text)


def test_error_sign(processor_factory, mock_logger):
    processor = processor_factory("any.docx")

    text = "ДОПОВІДЬ про факт помилково поданих даних щодо  неповернення після проходження військово-лікарської комісії військовослужбовця військової частини А0224 (Командування ДШВ) Десантно-штурмових військ Збройних Сил України"
    assert True == processor._check_error_sign(text)

    text = "ДОВІДКА-ДОПОВІДЬ про факт відміни самовільного залишення (продовження лікування в медичному закладі) солдата військової служби за призовом під час мобілізації "
    assert True == processor._check_error_sign(text)

    text = "ДОПОВІДЬ про факт помилкового повідомлення про  неповенення з лікування до району виконання завдання за призначенням військовослужбовця військової частини А0224 (7 КШР) Десантно-штурмових військ Збройних Сил України "
    assert True == processor._check_error_sign(text)

def test_desertion_sign(processor_factory, mock_logger):
    processor = processor_factory("any.docx")
    text = "16.02.2026 від командира аеромобільного батальйону надійшла доповідь про факт необережного поводження зі зброєю військовослужбовців військової частини А0224. Попередньо встановлено, що особовий склад підрозділів військової частини А0224 відповідно до бойового наказу командира військової частини А0224 №3/3т/БН від 15.02.2026 веде наступальні (штурмові) дій батальйонів I ешелону на глибину виконання найближчого та подальшого завдання при проведенні наступальних (штурмових) дій при виконанні заходів з національної безпеки та оборони, відсічі та стримуванні збройної агресії. Встановлено, що під час виконання бойового завдання, в районі виконання завдань за призначенням, у визначеній смузі відповідальності військової частини А0224, внаслідок необережного поводження зі зброєю отримав поранення військовослужбовець військової частини А0224: Солдат за призовом БУЙНОВ Олександр Олексійович, номер обслуги мінометного відділення взводу вогневої підтримки 1 аеромобільної роти аеромобільного батальйону військової частини А0224, діагноз: “Вогнепальне кульове(15.02.2026) сліпе поранення медіальної поверхні нижньої третини лівої гомілки, проникаюче? в гомілково-стопний суглоб”. Військовослужбовця евакуйовано до ПХГ Петропавлівка. Військовослужбовець перебував у засобах індивідуального захисту та з особистою зброєю. Ознак алкогольного та наркотичного сп’яніння не виявлено. Решта обставин з'ясовується."
    record = {
        COLUMN_DESERT_CONDITIONS : extract_desert_conditions(text),
        COLUMN_RETURN_DATE : extract_return_date(text),
    }

    assert False == processor.is_desertion_case(record)

def test_ml(processor_factory, mock_logger):
    text = "НЕГОЛЮК Володимир Васильович, старший солдат, військовослужбовець військової служби за призовом, стрілець-помічник гранатометника 2  десантно-штурмового відділення 3 десантно-штурмового взводу 7 десантно-штурмової роти 2 десантно-штурмового батальйону військової частини А0224, 29.10.1981 року народження, українець, освіта вища, Національний транспортний університет м. Київ у 2010 році. Одружений. неодружений. Призваний Салтівським ВТТЦК та СП м. Харків, 25.10.2025 року. РНОКПП відомості не надано"

    parser = MLParser(model_path=config.ML_MODEL_PATH, log_manager=mock_logger)
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