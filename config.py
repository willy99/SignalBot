import os
from typing import Final
from dotenv import load_dotenv
import sys

load_dotenv()
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
SIGNAL_BOT: Final = True # connect to signal and process attachments
SAVE_EXCEL_AT_CLOSE = False # по закриттю зберігати всі зміни в ексельчику


# Шляхи до папок
EXCEL_DIR: Final[str] = 'exchange\\projekt407'
DOC_DIR : Final[str] = "exchange\\ДД"
BACKUP_DIR: Final[str] = 'exchange\\projekt407\\backups'
REPORT_DIR: Final[str] = 'zvit'

DESERTER_TAB_NAME : Final = "А0224"
DESERTER_RESERVE_TAB_NAME : Final = "А7018"

DESERTER_XLSX_FILE_PATH:Final = f"/Volumes/exchange/projekt407/{DESERTER_XLSX}" # if using xlwings, actual one
ROOT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}"
DOCUMENT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}"
BACKUP_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{BACKUP_DIR}"
INBOX_DIR_PATH: Final[str] = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\inbox"
OUTBOX_DIR_PATH: Final[str] = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\outbox"
CACHE_FILE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}\\file_cache.json"
CACHE_FOLDER_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}"
INBOX_LOCAL_DIR_PATH = f"/Volumes/exchange/дд/inbox"
OUTBOX_LOCAL_DIR_PATH = f"/Volumes/exchange/дд/outbox"
REPORT_DAILY_DESERTION = f"/Volumes/exchange/projekt407/project/{REPORT_DIR}"

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
EXCEL_LAST_COL_NUMBER = 50 # take care of this, if number of columns is increased (now it's up to BB)

EXCEL_LIGHT_GRAY_COLOR: Final[str] = 'EEEEEE'
EXCEL_BLUE_COLOR: Final[str] = 'bdd7ee'
EXCEL_SUPPORT_COLOR: Final[str] = 'e8fffe'

CHECK_INBOX_EVERY_SEC: Final[float] = 60.0 # перевіряти інбокс кожні ? секунд

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


SECURITY_SESSION_TIMEOUT = 60 * 60  # хвилини у секундах
SECURITY_MAX_ATTEMPTS = 5
SECURITY_LOCKOUT_DURATION_MINS = 15