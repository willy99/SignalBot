import os
import multiprocessing
import argparse
import asyncio

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import json
import sys
import config

# Імпорти сервісів — після встановлення змінних оточення
from service.connection.MyDataBase import MyDataBase
from service.config.ConfigService import ConfigService
from service.processing.MyWorkFlow import MyWorkFlow
import threading
from gui.navigation import init_nicegui
import time

async def bot_worker(workflow: MyWorkFlow) -> None:
    """Фоновий потік: підключається до Signal і обробляє вхідні повідомлення."""
    if not config.SIGNAL_BOT:
        return
    retry_delay = 5  # Початкова затримка 5 секунд
    max_delay = 300  # Максимальна затримка 5 хвилин
    while True:
        try:
            print(f"🔄 Спроба підключення до Signal ({config.TCP_HOST}:{config.TCP_PORT})...")
            workflow.signalClient.host = config.TCP_HOST
            workflow.signalClient.port = config.TCP_PORT
            workflow.signalClient.connect()
            print("✅ З'єднання з Signal встановлено успішно.")
            retry_delay = 5
            file_handle = workflow.signalClient.read()
            for line in file_handle:
                if not line.strip():
                    continue
                data = json.loads(line)
                await workflow.parseSignalData(data)
        except Exception as e:
            print(f"❌ Помилка потоку бота: {e}")
        # Логіка Exponential Backoff
        print(f"⏳ Наступна спроба через {retry_delay} секунд...")
        time.sleep(retry_delay)

        # Збільшуємо затримку вдвічі для наступного разу (але не більше max_delay)
        retry_delay = min(retry_delay * 2, max_delay)


def parse_parameters() -> None:
    parser = argparse.ArgumentParser(description="Система A0224 Втікачі")
    parser.add_argument('--dev',  action='store_true', help='Режим розробки (порт 8081)')
    parser.add_argument('--prod', action='store_true', help='Бойовий режим (порт 8080)')
    args = parser.parse_args()
    config.IS_DEV = args.dev

    if config.IS_DEV:
        print('>>> 🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥    RUNNING IN DEV MODE:    🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥🖥')

def run_async_bot(workflow):
    """Ця функція запускається в окремому потоці і створює свій Event Loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker(workflow))

def main() -> None:
    parse_parameters()

    # -----------------------------------------------------------------------
    # Один спільний екземпляр БД для всього застосунку.
    # ConfigService та MyWorkFlow використовують один і той самий об'єкт —
    # жодних паралельних з'єднань на один файл.
    # -----------------------------------------------------------------------
    db = MyDataBase()

    # Синхронізуємо дефолтні налаштування та застосовуємо їх до config.py
    cfg_service = ConfigService(db)
    cfg_service.sync_defaults()
    cfg_service.apply_to_runtime()

    # Workflow також отримує готовий db, а не створює свій
    workflow = MyWorkFlow(db)

    try:
        workflow.initExcelProcessor(config.DESERTER_XLSX_FILE_PATH)
        workflow.excelProcessor.switch_to_sheet(config.DESERTER_TAB_NAME)

        print('>>> clieng bot ' + str(config.SIGNAL_BOT))
        if config.SIGNAL_BOT:
            threading.Thread(target=run_async_bot, args=(workflow,), daemon=True).start()
        else:
            print("🤖 Signal Bot вимкнено.")

        print("🌐 Запуск NiceGUI сервера...")
        init_nicegui(workflow)

    except KeyboardInterrupt:
        print("\n🛑 Програму зупинено користувачем.")
    except Exception as e:
        print(f"❌ Критична помилка: {e}")
    finally:
        print("🧹 Очищення ресурсів...")

        if hasattr(workflow, 'signalClient'):
            workflow.signalClient.close()

        if workflow.excelProcessor is not None:
            if config.SAVE_EXCEL_AT_CLOSE:
                try:
                    workflow.excelProcessor.save()
                except Exception:
                    pass
            workflow.excelProcessor.close()

        db.disconnect()
        print("✅ Програму завершено.")
        sys.exit(0)


if __name__ == "__main__":
    main()