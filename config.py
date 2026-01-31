import os

# Шляхи до папок (використовуємо expanduser для коректної роботи на Mac)
BASE_DIR = os.path.expanduser("~/work/signalBot")
DATA_DIR = os.path.join(BASE_DIR, "signal-data")

# Шлях до сокета
SOCKET_PATH = "/tmp/signal-bot.sock"

# Налаштування структури папок
FOLDER_YEAR_FORMAT = "%Y"         # Наприклад: 2026
FOLDER_MONTH_FORMAT = "%m"        # Наприклад: 01
FOLDER_DAY_FORMAT = "%Y.%m.%d"    # Наприклад: 2026.01.28
# Година, після якої дата вважається наступним днем (0-23)
DAY_ROLLOVER_HOUR = 16

# Шлях до системної папки signal-cli (де лежать вхідні файли)
SIGNAL_ATTACHMENTS_DIR = os.path.expanduser("~/.local/share/signal-cli/attachments/")

# Налаштування бази даних
DB_NAME = os.path.join(BASE_DIR, "bot_data.db")

DESERTER_XLSX = DATA_DIR + "/" + "А0224 СЗЧ 2022-2025.xlsx"
PROCESS_DOC = True
PROCESS_XLS = True