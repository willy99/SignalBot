import json
from states import get_response_and_move

# Шлях до сокета (має збігатися з тим, що вказано в daemon)
SOCKET_PATH = "/tmp/signal-bot.sock"

ANSWERS = {
    "привіт": "Привіт! Я твій автоматичний помічник 🤖",
    "як справи?": "Працюю стабільно, обробляю пакети! 🚀",
    "хто ти?": "Я Signal-бот.",
    "паляниця": "Укрзалізниця! 🇺🇦"
}

def send_message(client, recipient, message_text):
    """Відправляє повідомлення через Signal Daemon."""
    payload = {
        "jsonrpc": "2.0",
        "method": "send",
        "params": {
            "recipient": [recipient],
            "message": message_text
        },
        "id": 1
    }
    try:
        json_data = json.dumps(payload) + "\n"
        client.sendall(json_data.encode('utf-8'))
    except Exception as e:
        print(f"❌ Помилка при відправці: {e}")


def parse_signal_data(data, client):
    """Витягує текст повідомлення та номер відправника з JSON-RPC пакету."""
    try:
        params = data.get("params", {})
        envelope = params.get("envelope", {})

        print(str(data))
        # 1. Обробка вхідного повідомлення від когось іншого
        if "dataMessage" in envelope:
            source = envelope.get("source") or envelope.get("sourceNumber") or "Невідомий"
            message_text = envelope["dataMessage"].get("message", "")
            if message_text:

                response = get_response_and_move(source, message_text)
                print(f"🤖 Відповідаю: {response}")
                send_message(client, source, response)

                return f"📥 ВХІДНЕ від {source}: {message_text}"

        # 2. Обробка синхронізації (ви написали з телефону комусь)
        elif "syncMessage" in envelope:
            sync_msg = envelope["syncMessage"]
            if "sentMessage" in sync_msg:
                sent = sync_msg["sentMessage"]
                dest = sent.get("destinationNumber") or sent.get("destinationUuid") or "когось"
                text = sent.get("message", "")
                if text:
                    return f"📤 ВИ НАПИСАЛИ до {dest}: {text}"

    except Exception as e:
        return f"⚠️ Помилка парсингу: {e}"

    return None
