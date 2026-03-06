import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import json
import sys
import config
from config import DESERTER_TAB_NAME
from service.processing.MyWorkFlow import MyWorkFlow
import threading
from pynput import keyboard
import webbrowser
from gui.navigation import init_nicegui

def open_browser():
    """Просто відкриває вже запущений сервер у браузері"""
    print("🚀 Відкриваю браузер...")
    webbrowser.open("http://127.0.0.1:8080")

def listen_hotkeys():
    """Фонове прослуховування клавіш для відкриття браузера"""
    hotkeys = {
        '<cmd>+<shift>+9': open_browser,
        '<ctrl>+<shift>+9': open_browser
    }
    print("⌨️  Слухаю комбінацію Cmd+Shift+9...")
    with keyboard.GlobalHotKeys(hotkeys) as h:
        h.join()


def bot_worker(workflow):
    """Окрема функція для роботи бота в потоці"""
    if not config.SIGNAL_BOT:
        return
    try:
        workflow.client.host = config.TCP_HOST
        workflow.client.port = config.TCP_PORT
        workflow.client.connect()
        file_handle = workflow.client.read()
        for line in file_handle:
            if not line.strip(): continue
            data = json.loads(line)
            workflow.parseSignalData(data)
    except Exception as e:
        print(f"❌ Помилка бота: {e}")


def main():
    workflow = MyWorkFlow()
    try:
        # Ініціалізація Excel
        workflow.initExcelProcessor(config.DESERTER_XLSX_FILE_PATH)
        workflow.excelProcessor.switch_to_sheet(DESERTER_TAB_NAME)

        # 1. Хоткеї у фоні
        # threading.Thread(target=listen_hotkeys, daemon=True).start()

        # 2. Бот у фоні (якщо увімкнений)
        if config.SIGNAL_BOT:
            threading.Thread(target=bot_worker, args=(workflow,), daemon=True).start()
        else:
            print("🤖 Signal Bot вимкнено.")

        # 3. NiceGUI в ОСНОВНОМУ потоці (це тримає програму живою)
        print("🌐 Запуск NiceGUI сервера...")
        init_nicegui(workflow)

    except KeyboardInterrupt:
        print("\n🛑 Програма зупиняється користувачем...")
    except Exception as e:
        print(f"❌ Критична помилка: {e}")
    finally:
        # ПРАВИЛЬНЕ ЗАКРИТТЯ
        print("🧹 Очищення ресурсів...")

        if hasattr(workflow, 'client'):
            workflow.client.close()

        if hasattr(workflow, 'excelProcessor'):
            if config.SAVE_EXCEL_AT_CLOSE:
                try:
                    workflow.excelProcessor.save()
                except:
                    pass
            workflow.excelProcessor.close()

        print("✅ Програма завершена.")
        sys.exit(0)

if __name__ == "__main__":
    main()
