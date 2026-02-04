import os

# Шляхи до папок
BASE_DIR = os.path.expanduser("~/work/signalBot")
DATA_DIR = os.path.join(BASE_DIR, "signal-data")

# Шлях до системної папки signal-cli (де лежать вхідні файли)
SIGNAL_ATTACHMENTS_DIR = os.path.expanduser("~/.local/share/signal-cli/attachments/")

# Налаштування структури папок
FOLDER_YEAR_FORMAT = "%Y"         # Наприклад: 2026
FOLDER_MONTH_FORMAT = "%m"        # Наприклад: 01
FOLDER_DAY_FORMAT = "%Y.%m.%d"    # Наприклад: 2026.01.28
# Година, після якої дата вважається наступним днем (0-23)
DAY_ROLLOVER_HOUR = 16


# Шлях до сокета
SOCKET_PATH = "/tmp/signal-bot.sock" # для мак
TCP_HOST = '127.0.0.1'
TCP_PORT = 1234

# Налаштування бази даних
DB_NAME = os.path.join(DATA_DIR, "bot_data.db")

#DESERTER_XLSX = DATA_DIR + "/" + "А0224 СЗЧ_copy.xlsm"
DESERTER_XLSX = DATA_DIR + "/" + "А0224 СЗЧ 2022-2025.xlsm"
DESERTER_TAB_NAME = "А0224"
PROCESS_DOC = True
PROCESS_XLS = True


EXCEL_DATE_FORMAT = "%m/%d/%y"
