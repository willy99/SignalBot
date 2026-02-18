import json

import config
from processing.MyWorkFlow import MyWorkFlow

import threading
from pynput import keyboard
from gui.GUIHelper import GUIHelper


def listen_hotkeys(workflow_obj):
    """Функція для фонового прослуховування клавіш"""
    helper = GUIHelper()
    # Важливо: використовуємо lambda, щоб функція не викликалася сама при старті
    hotkeys = {
        '<cmd>+<shift>+9': lambda: helper.open_editor_from_excel(workflow_obj),
        '<ctrl>+<shift>+9': lambda: helper.open_editor_from_excel(workflow_obj)
    }

    print("⌨️  Слухаю комбінацію Cmd+Shift+9...")
    with keyboard.GlobalHotKeys(hotkeys) as h:
        h.join()

def main():
    workflow = MyWorkFlow()
    # if config.PROCESS_XLS:
    workflow.initExcelProcessor(config.DESERTER_XLSX_FILE_PATH) # one-time init

    hotkey_thread = threading.Thread(
        target=listen_hotkeys,
        args=(workflow,),  # Передаємо об'єкт як аргумент
        daemon=True
    )
    hotkey_thread.start()

    try:
        workflow.client.host = config.TCP_HOST
        workflow.client.port = config.TCP_PORT
        workflow.client.connect()

        file_handle = workflow.client.read()
        for line in file_handle:
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                result = workflow.parseSignalData(data)
                if result:
                    print(result)

            except json.JSONDecodeError:
                continue

    except KeyboardInterrupt:
        print("\n🛑 Бот зупинений.")
    except Exception as e:
        print(f"❌ Помилка з'єднання: {e}")
    finally:
        workflow.client.close()
        workflow.excelProcessor.close()


if __name__ == "__main__":
    main()
