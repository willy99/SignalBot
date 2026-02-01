import socket

def get_client(host="127.0.0.1", port=1234):
    # Для TCP використовується AF_INET замість AF_UNIX
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        address = (host, port)
        client.connect(address)
        return client
    except Exception as e:
        print(f"❌ Не вдалося підключитися до {address}: {e}")
        raise