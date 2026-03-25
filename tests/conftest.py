import os
import shutil
import pytest
from unittest.mock import MagicMock

from gui.services.request_context import RequestContext
from service.connection.MyDataBase import MyDataBase
from service.constants import DB_TABLE_NOTIF_DOC, DB_TABLE_SUPPORT_DOC, DB_TABLE_DBR_DOC, DB_TABLE_TASK
from service.storage.LoggerManager import LoggerManager

# Шлях до вашого порожнього шаблону
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "template.xlsx")


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
def temp_excel_file(tmp_path):
    # 1. Шлях до шаблону (переконайтеся, що він правильний відносно conftest.py)
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "template.xlsx"))

    # 2. Створюємо цільовий шлях. tmp_path вже враховує ваш --basetemp
    test_db_path = tmp_path / "test_db.xlsx"

    # ПЕРЕВІРКА: чи існує папка, куди ми копіюємо? (pytest має її створити, але на Mac краще перебдеть)
    test_db_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. Копіюємо
    shutil.copy(template_path, str(test_db_path))

    # 4. КРИТИЧНО ДЛЯ MAC: перетворюємо на абсолютний рядок
    abs_path = str(test_db_path.resolve())
    yield abs_path

    # Додамо прінт для відладки (ви побачите його, якщо запустить pytest -s)
    print(f"\n[DEBUG] Тестовий файл створено за адресою: {abs_path}")

    return abs_path


@pytest.fixture
def mock_db():
    """Створює тимчасову БД в пам'яті на основі реального schema.sql"""
    db = MyDataBase(":memory:")

    # Визначаємо шлях до schema.sql (корегуйте шлях під вашу структуру папок)
    # Припустимо, schema.sql лежить у папці service/connection/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Піднімаємось на потрібний рівень, якщо conftest.py лежить у папці tests/
    project_root = os.path.dirname(current_dir)
    schema_path = os.path.join(project_root, 'service', 'connection', 'schema.sql')

    # Читаємо та виконуємо схему
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # Використовуємо внутрішній метод вашого MyDataBase або прямий доступ до sqlite
    # Якщо MyDataBase має доступ до курсору, можна так:
    with db.connect() as conn:  # припускаю наявність такого методу
        conn.executescript(sql_script)

    update_path = os.path.join(project_root, 'service', 'connection', 'update.sql')
    if os.path.exists(update_path):
        with open(update_path, 'r', encoding='utf-8') as f:
            db.connect().executescript(f.read())

    # Додаємо тестового користувача, щоб працювали JOIN-и
    db.insert_record("users", {"id": 1, "username": "test_user", "password_hash":"asdklfjasdlfkajsdlnskjdfksjadlkfjlaksjdf", "role":"admin"})
    yield db

    try:
        db.__execute_sql__("DELETE FROM " + DB_TABLE_NOTIF_DOC)
        db.__execute_sql__("DELETE FROM " + DB_TABLE_SUPPORT_DOC)
        db.__execute_sql__("DELETE FROM " + DB_TABLE_DBR_DOC)
        db.__execute_sql__("DELETE FROM " + DB_TABLE_TASK)
        db.__execute_sql__("DELETE FROM users")
    except:
        pass
    print("\n🧹 Тестова база очищена")


@pytest.fixture
def mock_ctx():
    """Імітація контексту запиту користувача"""
    ctx = RequestContext(user_login="test_user", user_id=1, user_name="test", user_role="Admin")
    return ctx