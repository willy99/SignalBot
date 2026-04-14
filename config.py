import os
import stat
from typing import Final
from dotenv import load_dotenv
import sys

load_dotenv()


def _validate_env() -> None:
    """
    Адаптована перевірка для Windows.
    """
    # Використовуємо pathlib для надійності шляхів
    from pathlib import Path
    env_path = Path(__file__).parent / '.env'

    if not env_path.exists():
        print("⚠️  .env файл не знайдено. Переконайтеся, що він лежить у корені проекту.")
        return

    # --- Перевірка прав доступу (Windows compatible) ---
    if os.name == 'posix':  # Тільки для Linux/Mac
        file_mode = env_path.stat().st_mode & 0o777
        if file_mode & 0o077:
            try:
                os.chmod(str(env_path), 0o600)
                print("✅ Права .env виправлено на 600.")
            except Exception as e:
                print(f"⚠️ Не вдалося змінити права доступу: {e}")
    else:
        # На Windows ми просто перевіряємо, чи файл не порожній
        if env_path.stat().st_size == 0:
            print("🚨 SECURITY: .env файл порожній!")

    # --- Перевірка обов'язкових змінних ---
    required = {
        'UI_SECRET_KEY': 'Ключ підпису сесій',
        'NET_PASSWORD': 'Пароль до мережі',
    }

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print("🚨 SECURITY: Відсутні критичні змінні в .env:")
        for m in missing:
            print(f"  • {m} ({required[m]})")

        if 'UI_SECRET_KEY' in missing:
            print("💀 UI_SECRET_KEY відсутній. Запуск неможливий.")
            # На Windows sys.exit(1) працює добре
            sys.exit(1)


_validate_env()
PROJECT_TITLE = "A0224 Втікачі"
IS_DEV = '--dev' in sys.argv

NET_SERVER_IP = os.getenv("NET_SERVER_IP", "127.0.0.1")
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

# Основна функціональність
PROCESS_DOC : Final = True   # copy doc file from signal to date-folder
PROCESS_XLS : Final = True # immediate process doc to excel. if false, batch can be applied later on
DAILY_BACKUPS: Final = True # do daily backups of excel db
SIGNAL_BOT: Final = False # connect to signal and process attachments
SAVE_EXCEL_AT_CLOSE = False # по закриттю зберігати всі зміни в ексельчику


# Шляхи до папок
EXCEL_DIR: Final[str] = 'C:/exchange/projekt407'
DOC_DIR : Final[str] = "C:/exchange/ДД"
BACKUP_DIR: Final[str] = 'C:/exchange/projekt407/backups'
REPORT_DIR: Final[str] = 'zvit'

DESERTER_TAB_NAME : Final = "А0224"
DESERTER_RESERVE_TAB_NAME : Final = "А7018"

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


SECURITY_SESSION_TIMEOUT = 60 * 60  # хвилини у секундах
SECURITY_MAX_ATTEMPTS = 5
SECURITY_LOCKOUT_DURATION_MINS = 15
