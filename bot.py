import json

import config
from processing.MyWorkFlow import MyWorkFlow

def main():
    workflow = MyWorkFlow()
    if config.PROCESS_XLS:
        workflow.initExcelProcessor(config.DESERTER_XLSX) # one-time init

    # Створюємо підключення до Unix сокета
    try:
        workflow.client.host = config.TCP_HOST
        workflow.client.port = config.TCP_PORT
        workflow.client.connect()

        # Читаємо потік даних порядково (JSON-RPC надсилає кожен пакет в один рядок)
        file_handle = workflow.client.read()
        for line in file_handle:
            if not line.strip():
                continue

            try:
                data = json.loads(line)

                # Виводимо тільки результати парсингу повідомлень
                print('🔓 --------------------------BEGIN------------------------------------------ 🔓 ')
                result = workflow.parseSignalData(data)
                print('🔓 --------------------------END------------------------------------------ 🔓 ')
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


if __name__ == "__main__":
    main()
