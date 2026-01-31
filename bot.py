import socket
import json
import os
import sys
from messageparser import parse_signal_data
from database import init_db
import config

def main():
    if not os.path.exists(config.SOCKET_PATH):
        print(f"❌ Помилка: Сокет {config.SOCKET_PATH} не знайдено.")
        print("Спочатку запустіть демон: signal-cli -u ВашНомер daemon --socket /tmp/signal-bot.sock")
        sys.exit(1)

    # Ініціалізуємо базу даних перед стартом
    init_db()

    # Створюємо підключення до Unix сокета
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        client.connect(config.SOCKET_PATH)
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
