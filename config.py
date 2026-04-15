import os
import stat
from typing import Final
from dotenv import load_dotenv
import sys

from utils.utils import is_win, get_env_bool

load_dotenv()

def _validate_env_win() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

    if not os.path.exists(env_path):
        print("⚠️  .env файл не знайдено. Змінні оточення мають бути встановлені вручну.")
        return
    file_mode = os.stat(env_path).st_mode & 0o777
    if file_mode & 0o077:  # group або other мають хоч якийсь доступ
        print(f"🚨 SECURITY: .env має небезпечні права {oct(file_mode)}. Виправляю на 600...")
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        print("✅ Права .env виправлено: тепер тільки власник може читати файл.")

    required = {
        'UI_SECRET_KEY': 'Ключ підпису сесій (обов\'язковий для безпеки UI)',
        'NET_PASSWORD':  'Пароль до мережевого сховища',
        'EMAIL_PASSWORD': 'Пароль до SMTP (потрібен для 2FA через Email)',
    }
    missing = [f"  • {var}  ({desc})" for var, desc in required.items() if not os.getenv(var)]
    if missing:
        print("🚨 SECURITY: Відсутні обов'язкові змінні оточення:")
        for m in missing:
            print(m)
        if not os.getenv('UI_SECRET_KEY'):
            print("💀 UI_SECRET_KEY відсутній — сесії непідписані. Зупиняю запуск.")
            sys.exit(1)
        print("   Деякі функції можуть не працювати. Заповніть .env файл.")


def _validate_env_mac() -> None:
    """
    Перевіряє безпеку .env файлу при кожному старті.
    1. Автоматично виправляє права доступу якщо вони надто широкі.
    2. Попереджає про відсутні обов'язкові змінні.
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

    if not os.path.exists(env_path):
        print("⚠️  .env файл не знайдено. Змінні оточення мають бути встановлені вручну.")
        return

    # --- Перевірка прав доступу ---
    file_mode = os.stat(env_path).st_mode & 0o777
    if file_mode & 0o077:  # group або other мають хоч якийсь доступ
        print(f"🚨 SECURITY: .env має небезпечні права {oct(file_mode)}. Виправляю на 600...")
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        print("✅ Права .env виправлено: тепер тільки власник може читати файл.")

    # --- Перевірка наявності обов'язкових змінних ---
    required = {
        'UI_SECRET_KEY': 'Ключ підпису сесій (обов\'язковий для безпеки UI)',
        'NET_PASSWORD':  'Пароль до мережевого сховища',
        'EMAIL_PASSWORD': 'Пароль до SMTP (потрібен для 2FA через Email)',
    }
    missing = [f"  • {var}  ({desc})" for var, desc in required.items() if not os.getenv(var)]
    if missing:
        print("🚨 SECURITY: Відсутні обов'язкові змінні оточення:")
        for m in missing:
            print(m)
        if not os.getenv('UI_SECRET_KEY'):
            print("💀 UI_SECRET_KEY відсутній — сесії непідписані. Зупиняю запуск.")
            sys.exit(1)
        print("   Деякі функції можуть не працювати. Заповніть .env файл.")

if is_win():
    _validate_env_win()
else:
    _validate_env_mac()

PROJECT_TITLE = "A0224 Втікачі"
IS_DEV = '--dev' in sys.argv

NET_SERVER_IP = os.getenv("NET_SERVER_IP", "192.168.0.53")
NET_USERNAME = os.getenv("NET_USERNAME")
NET_PASSWORD = os.getenv("NET_PASSWORD")
UI_SECRET_KEY = os.getenv("UI_SECRET_KEY")

EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
EMAIL_SMTP_PORT = os.getenv("EMAIL_SMTP_PORT")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if IS_DEV:
    UI_PORT=8081
    UI_RELOAD=False
    DESERTER_XLSX: Final = "А0224 СЗЧ 2022-2025_copy_pasha.xlsx"
else:
    UI_PORT=8080
    UI_RELOAD=False
    DESERTER_XLSX: Final = "А0224 СЗЧ 2022-2025_1.xlsx"

SECURITY_SESSION_TIMEOUT = 60 * 60  # хвилини у секундах
SECURITY_MAX_ATTEMPTS = 5
SECURITY_LOCKOUT_DURATION_MINS = 15

# Налаштування структури папок
FOLDER_YEAR_FORMAT : Final = "%Y"         # Наприклад: 2026
FOLDER_MONTH_FORMAT : Final = "%m"        # Наприклад: 01
FOLDER_DAY_FORMAT : Final = "%d.%m.%Y"    # Наприклад: 2026.01.28
# Година, після якої дата вважається наступним днем (0-23)
DAY_ROLLOVER_HOUR : Final = 16
BACKUP_KEEP_DAYS = 30 # тримати бекапи не старіше ніж N діб

# Логірування подій
LOGGER_FILE_NAME = 'bot_log.log'
LOG_MONITORING_MAX_LINES = 1000 # tail -f

EXCEL_DATE_FORMAT : Final = "%d.%m.%Y"
UI_DATE_FORMAT : Final = "DD.MM.YYYY"

EXCEL_DATE_FORMATS_REPORT = ["%m/%d/%y", "%d.%m.%Y", "%-m/%-d/%y", "%#m/%#d/%y", "%Y-%m-%d"]
EXCEL_CHUNK_SIZE = 2000 # reading data by chunks for stability

EXCEL_LIGHT_GRAY_COLOR: Final[str] = 'EEEEEE'
EXCEL_BLUE_COLOR: Final[str] = 'bdd7ee'
EXCEL_SUPPORT_COLOR: Final[str] = 'e8fffe'

CHECK_INBOX_EVERY_SEC: Final[float] = 60.0 # перевіряти інбокс кожні ? секунд

# Основна функціональність
SIGNAL_BOT: Final = get_env_bool("SIGNAL_BOT", False)
SAVE_EXCEL_AT_CLOSE: Final = get_env_bool("SAVE_EXCEL_AT_CLOSE", False)
PROCESS_DOC: Final = get_env_bool("PROCESS_DOC", True)
PROCESS_XLS : Final = get_env_bool("PROCESS_XLS", True) # immediate process doc to excel. if false, batch can be applied later on
DAILY_BACKUPS: Final = get_env_bool("DAILY_BACKUPS", True) # do daily backups of excel db

DESERTER_TAB_NAME : Final = "А0224"
DESERTER_RESERVE_TAB_NAME : Final = "А7018"

# Шляхи до папок
if is_win():
    EXCEL_DIR: Final[str] = 'C:/exchange/projekt407'
    DOC_DIR: Final[str] = "C:/exchange/ДД"
    BACKUP_DIR: Final[str] = 'C:/exchange/projekt407/backups'
    REPORT_DIR: Final[str] = 'zvit'

    DESERTER_XLSX_FILE_PATH:Final = f"c:/exchange/projekt407/{DESERTER_XLSX}" # if using xlwings, actual one
    #ROOT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}"
    #DOCUMENT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\exchange\\ДД"
    ROOT_STORAGE_PATH: Final = fr"\\{NET_SERVER_IP}"
    DOCUMENT_STORAGE_PATH: Final = fr"\\{NET_SERVER_IP}\exchange\ДД"

    BACKUP_STORAGE_PATH: Final = fr"\\{NET_SERVER_IP}\exchange\projekt407\backups"
    INBOX_DIR_PATH: Final[str] = fr"\\{NET_SERVER_IP}\exchange\ДД\inbox"
    OUTBOX_DIR_PATH: Final[str] = fr"\\{NET_SERVER_IP}\exchange\ДД\outbox"
    CACHE_FILE_PATH: Final = fr"\\{NET_SERVER_IP}\exchange\\ДД\file_cache.json"
    CACHE_FOLDER_PATH: Final = fr"\\{NET_SERVER_IP}\exchange\ДД"
    INBOX_LOCAL_DIR_PATH = f"c:/exchange/дд/inbox"
    OUTBOX_LOCAL_DIR_PATH = f"c:/exchange/дд/outbox"
    REPORT_DAILY_DESERTION = f"c:/exchange/projekt407/project/zvit"

    TMP_DIR: Final = "C:/temp" # Створи цю папку вручну!
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR, exist_ok=True)

    # Шлях до сокета
    SOCKET_PATH : Final = "c:/temp/signal-bot.sock" # для мак
    TCP_HOST : Final = '127.0.0.1'
    TCP_PORT : Final = 1234

    # Налаштування бази даних
    DB_DIR = "C:/work/signalBot/signal-data"
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    DB_NAME = os.path.join(DB_DIR, "bot_data.db")
    # DB_NAME = os.path.join(os.path.expanduser("c:/work/signalBot/signal-data"), "bot_data.db")
    MAX_QUERY_RESULTS = 50
    RECORDS_PER_PAGE = 10

    # ML
    BASE_WORK_DIR = "C:/work/SignalBot/signal-data"

    ML_MODEL_JSON = os.path.join(BASE_WORK_DIR, "training_data.jsonl")
    ML_LOCAL_DESERTER_XLSX : Final = os.path.join(BASE_WORK_DIR, "А0224 СЗЧ 2022-2025_copy_pasha.xlsx")
    ML_MODEL_PATH = "C:/work/signalBot/service/ml/output_model/model-best"

    # Шлях до системної папки signal-cli (де лежать вхідні файли)

    # Signal Attachments (Windows версія)
    # Якщо використовуєш WSL або Docker — лишай як було.
    # Якщо чистий Windows — вкажи реальний шлях, куди signal-cli складає файли.
    SIGNAL_ATTACHMENTS_DIR : Final = "C:/work/signalBot/attachments"

else:
    EXCEL_DIR: Final[str] = '/Volumes/exchange/projekt407'
    DOC_DIR : Final[str] = "/Volumes/exchange/дд"
    BACKUP_DIR: Final[str] = '/Volumes/exchange/projekt407/backups'
    REPORT_DIR: Final[str] = '/Volumes/exchange/projekt407/project/zvit'

    DESERTER_XLSX_FILE_PATH:Final = f"{EXCEL_DIR}/{DESERTER_XLSX}" # if using xlwings, actual one
    ROOT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}"
    DOCUMENT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}"
    BACKUP_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{BACKUP_DIR}"
    INBOX_DIR_PATH: Final[str] = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\inbox"
    OUTBOX_DIR_PATH: Final[str] = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\outbox"
    CACHE_FILE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\file_cache.json"
    CACHE_FOLDER_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}"
    INBOX_LOCAL_DIR_PATH = f"{DOC_DIR}/inbox"
    OUTBOX_LOCAL_DIR_PATH = f"{DOC_DIR}/outbox"
    REPORT_DAILY_DESERTION = f"{DOC_DIR}/{REPORT_DIR}"


    # Шлях до сокета
    SOCKET_PATH : Final = "/tmp/signal-bot.sock" # для мак
    TCP_HOST : Final = '127.0.0.1'
    TCP_PORT : Final = 1234

    # Налаштування бази даних
    DB_NAME = os.path.join(os.path.expanduser("~/work/signalBot/signal-data"), "bot_data.db")
    MAX_QUERY_RESULTS = 50
    RECORDS_PER_PAGE = 10

    # ML
    ML_MODEL_JSON = os.path.join(os.path.expanduser("~/work/signalBot/signal-data"), "training_data.jsonl")
    ML_LOCAL_DESERTER_XLSX : Final =  "~/work/SignalBot/signal-data/А0224 СЗЧ 2022-2025_copy_pasha.xlsx"
    ML_MODEL_PATH = os.path.join(os.path.expanduser("~/work/signalBot/service/ml/output_model"), "model-best")

    # Шлях до системної папки signal-cli (де лежать вхідні файли)
    SIGNAL_ATTACHMENTS_DIR : Final = os.path.expanduser("~/.local/share/signal-cli/attachments/")
    TMP_DIR: Final = os.path.expanduser("~/tmp/")

