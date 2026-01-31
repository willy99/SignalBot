import json
from states import get_response_and_move
import base64
import os
from attachment_handler import handle_attachment

# group id: MURKGlaZUtX/2i+9JQqwkxycQ0VStX5NJQCe27QKauw=

# Шлях до сокета (має збігатися з тим, що вказано в daemon)
SOCKET_PATH = "/tmp/signal-bot.sock"

ANSWERS = {
    "привіт": "Привіт! Що треба? 🤖",
    "як справи": "Сракопад жахливий! 🚀",
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
            msg = envelope["dataMessage"]
            source = envelope.get("source") or envelope.get("sourceNumber") or "Невідомий"
            source_uuid = envelope.get("sourceUuid")  # Важливо для реакцій!
            timestamp = msg.get("timestamp")
            group_info = msg.get("groupInfo")
            recipient = source
            group_id = group_info.get("groupId") if group_info else None

            message_text = msg.get("message", "")

            attachments = msg.get("attachments", [])

            # process attachments
            file_saved = False
            if len(attachments) > 0:
                for att in attachments:
                    att_id = att.get("id")
                    filename = att.get("filename")

                    print(f"📎 Отримано файл: {filename} (ID: {att_id})")
                    file_saved = handle_attachment(att_id, filename)

            elif message_text:
                response = ''
                print('Check is message in answers' + str(message_text) + ' ' + str(message_text in ANSWERS))
                if message_text.lower() in ANSWERS:
                    response = ANSWERS[message_text.lower()]
                else:
                    response = get_response_and_move(source, message_text)
                print(f"🤖 Відповідаю: {response}")
                if group_id is None:
                    send_message(client, source, response)

                # return f"📥 ВХІДНЕ від {source}: {message_text}"
            if file_saved:
                send_reaction(
                    client,
                    group_id,
                    recipient,
                    "➕",
                    source_uuid,
                    timestamp
                )
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


def download_attachment(client, attachment_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "getAttachment",
        "params": {
            "id": attachment_id
        },
        "id": 2
    }
    client.sendall((json.dumps(payload) + "\n").encode())

    # Тут складніше: треба дочекатися відповіді від сокета саме на цей ID
    # Демон поверне JSON з полем "base64": "..."


def get_attachment_content(attachment_id):
    # Шлях за замовчуванням на Mac/Linux
    base_path = os.path.expanduser("~/.local/share/signal-cli/attachments/")
    full_path = os.path.join(base_path, attachment_id)

    if os.path.exists(full_path):
        with open(full_path, 'rb') as f:
            return f.read()
    return None

def send_reaction(client, group_id, recipient_id, emoji, target_author_uuid, target_timestamp):
    print("recipient id " + recipient_id + "; target author id: " + target_author_uuid)
    if group_id is not None:
        payload = {
            "jsonrpc": "2.0",
            "method": "sendReaction",
            "params": {
                "groupId": group_id,  # Передаємо ID групи окремо
                "emoji": emoji,
                "target-author": target_author_uuid,
                "target-timestamp": target_timestamp
            },
            "id": 3
        }
    else:
        payload = {
            "jsonrpc": "2.0",
            "method": "sendReaction",
            "params": {
                "recipient": [recipient_id],
                "emoji": emoji,
                "target-author": target_author_uuid,
                "target-timestamp": target_timestamp
            },
            "id": 3
        }
    client.sendall((json.dumps(payload) + "\n").encode('utf-8'))