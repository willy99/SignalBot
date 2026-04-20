import socket
import json

class SignalClient:
    def __init__(self, host="127.0.0.1", port=1234):
        self.host = host
        self.port = port
        self.client = None
        self._id_counter = 1

    def connect(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((self.host, self.port))
            print(f"✅ Підключено до Signal Daemon на {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Помилка підключення: {e}")
            raise

    def _send_rpc(self, method, params):
        """Універсальний метод для відправки JSON-RPC запитів."""

        if self.client is None:
            print(f"Перепідключення клієнту")
            try:
                self.connect()
            except Exception as e:
                print("Помилка з'єднання")
                return

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._id_counter
        }
        self._id_counter += 1

        try:
            json_data = json.dumps(payload) + "\n"
            self.client.sendall(json_data.encode('utf-8'))
        except Exception as e:
            print(f"❌ Помилка при виклику методу {method}: {e}")

    def read(self):
        """Повертає об'єкт файлу для читання вхідних повідомлень (streaming)."""
        if not self.client:
            return None
        return self.client.makefile('r', encoding='utf-8')

    def send_message(self, recipient, message_text):
        params = {
            "recipient": [recipient],
            "message": message_text
        }
        self._send_rpc("send", params)

    def send_reaction(self, group_id, recipient_id, emoji, target_author_uuid, target_timestamp):
        params = {
            "emoji": emoji,
            "target-author": target_author_uuid,
            "target-timestamp": target_timestamp
        }

        if group_id:
            params["groupId"] = group_id
        else:
            params["recipient"] = [recipient_id]

        self._send_rpc("sendReaction", params)

    def close(self):
        if self.client:
            self.client.close()
            print("🔌 З'єднання закрито.")