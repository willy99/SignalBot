import os
import shutil
import pytest
from unittest.mock import MagicMock
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