import os
from typing import Final

# Шляхи до папок
NET_SERVER_IP = "192.168.110.64"
NET_USERNAME = "Admin"
NET_PASSWORD = "Flvbycrbq@2"
EXCEL_DIR = 'exchange\\projekt407'
DOC_DIR : Final = "exchange\\ДД"

DESERTER_XLSX: Final = "А0224 СЗЧ 2022-2025_copy_pasha.xlsx"
# DESERTER_XLSX: Final = "А0224 СЗЧ 2022-2025.xlsx"

DESERTER_XLSX_FILE_PATH:Final = f"\\\\{NET_SERVER_IP}\\{EXCEL_DIR}\\{DESERTER_XLSX}"
DOCUMENT_STORAGE_PATH: Final = f"\\\\{NET_SERVER_IP}\\{DOC_DIR}"

# DESERTER_XLSX : Final = DATA_DIR + "/" + "А0224 СЗЧ_copy.xlsm"
# DESERTER_XLSX : Final = NET_DIR + "/" + "А0224 СЗЧ 2022-2025.xlsm"

# Налаштування структури папок
FOLDER_YEAR_FORMAT : Final = "%Y"         # Наприклад: 2026
FOLDER_MONTH_FORMAT : Final = "%m"        # Наприклад: 01
FOLDER_DAY_FORMAT : Final = "%d.%m.%Y"    # Наприклад: 2026.01.28
# Година, після якої дата вважається наступним днем (0-23)
DAY_ROLLOVER_HOUR : Final = 16

DESERTER_TAB_NAME : Final = "А0224"
PROCESS_DOC : Final = True # copy file from signal to folder
PROCESS_XLS : Final = True # immediate process doc to excel. if false, batch can be applied later on

EXCEL_DATE_FORMAT : Final = "%d.%m.%Y"
EXCEL_DATE_FORMATS_REPORT = ["%m/%d/%y", "%d.%m.%Y", "%-m/%-d/%y", "%#m/%#d/%y", "%Y-%m-%d"]

# Шлях до сокета
SOCKET_PATH : Final = "/tmp/signal-bot.sock" # для мак
TCP_HOST : Final = '127.0.0.1'
TCP_PORT : Final = 1234

# Налаштування бази даних
DB_NAME = os.path.join(os.path.expanduser("~/work/signalBot/signal-data"), "bot_data.db")

# ML
ML_MODEL_JSON = os.path.join(os.path.expanduser("~/work/signalBot/signal-data"), "training_data.jsonl")
ML_LOCAL_DESERTER_XLSX : Final =  "~/work/SignalBot/signal-data/А0224 СЗЧ 2022-2025_copy_pasha.xlsx"
ML_MODEL_PATH = os.path.join(os.path.expanduser("~/work/signalBot/ml/output_model"), "model-best")

# Шлях до системної папки signal-cli (де лежать вхідні файли)
SIGNAL_ATTACHMENTS_DIR : Final = os.path.expanduser("~/.local/share/signal-cli/attachments/")
TMP_DIR: Final = os.path.expanduser("~/tmp/")