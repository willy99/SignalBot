import json
from messageparser import parse_signal_data
from database import init_db
import config
from connection.connection_client import get_client

def main():

    # Ініціалізуємо базу даних перед стартом
    init_db()

    # Створюємо підключення до Unix сокета

    try:
        client = get_client(config.TCP_HOST, config.TCP_PORT)
        print("✅ Бот підключився до Signal і слухає ефір...")

        # Читаємо потік даних порядково (JSON-RPC надсилає кожен пакет в один рядок)
        file_handle = client.makefile('r')
        for line in file_handle:
            if not line.strip():
                continue

            try:
                data = json.loads(line)

                # Виводимо тільки результати парсингу повідомлень
                result = parse_signal_data(data, client)
                if result:
                    print(result)

            except json.JSONDecodeError:
                continue

    except KeyboardInterrupt:
        print("\n🛑 Бот зупинений.")
    except Exception as e:
        print(f"❌ Помилка з'єднання: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
