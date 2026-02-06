import os
from typing import Final

# Шляхи до папок
BASE_DIR : Final = os.path.expanduser("~/work/signalBot")
DATA_DIR : Final = os.path.join(BASE_DIR, "signal-data")

# Шлях до системної папки signal-cli (де лежать вхідні файли)
SIGNAL_ATTACHMENTS_DIR : Final = os.path.expanduser("~/.local/share/signal-cli/attachments/")

# Налаштування структури папок
FOLDER_YEAR_FORMAT : Final = "%Y"         # Наприклад: 2026
FOLDER_MONTH_FORMAT : Final = "%m"        # Наприклад: 01
FOLDER_DAY_FORMAT : Final = "%Y.%m.%d"    # Наприклад: 2026.01.28
# Година, після якої дата вважається наступним днем (0-23)
DAY_ROLLOVER_HOUR : Final = 16

#DESERTER_XLSX : Final = DATA_DIR + "/" + "А0224 СЗЧ_copy.xlsm"
DESERTER_XLSX : Final = DATA_DIR + "/" + "А0224 СЗЧ 2022-2025.xlsm"
DESERTER_TAB_NAME : Final = "А0224"
PROCESS_DOC : Final = True
PROCESS_XLS : Final = True


EXCEL_DATE_FORMAT : Final = "%m/%d/%y"

# Шлях до сокета
SOCKET_PATH : Final = "/tmp/signal-bot.sock" # для мак
TCP_HOST : Final = '127.0.0.1'
TCP_PORT : Final = 1234

# Налаштування бази даних
DB_NAME : Final = os.path.join(DATA_DIR, "bot_data.db")

