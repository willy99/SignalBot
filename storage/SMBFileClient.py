import io
import smbclient
from smbclient import register_session, delete_session, open_file, makedirs
from config import NET_SERVER_IP, NET_USERNAME, NET_PASSWORD
from storage.FileStorageClient import FileStorageClient

class SMBFileClient(FileStorageClient):
    """
    Клас для управління підключенням до мережевого диска через протокол SMB.
    Забезпечує роботу з файлами та папками за допомогою UNC шляхів.
    """

    def __init__(self):
        self.server_ip = NET_SERVER_IP
        self.username = NET_USERNAME
        self.password = NET_PASSWORD
        self.is_connected = False

    def __enter__(self):
        """Реалізація контекстного менеджера для автоматичного підключення."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Реалізація контекстного менеджера для автоматичного розриву з'єднання."""
        self.disconnect()

    def connect(self):
        """Встановлює SMB-сесію з сервером."""
        try:
            register_session(self.server_ip, username=self.username, password=self.password)
            self.is_connected = True
            # print(f"✅ Сесію з {self.server_ip} встановлено.")
        except Exception as e:
            print(f"❌ Помилка підключення до SMB {self.server_ip}: {e}")
            raise

    def disconnect(self):
        """Закриває активну сесію."""
        if self.is_connected:
            try:
                delete_session(self.server_ip)
                self.is_connected = False
                # print(f"🔌 Сесію з {self.server_ip} закрито.")
            except Exception as e:
                print(f"⚠️ Помилка при закритті сесії: {e}")

    def make_dirs(self, path: str):
        """
        Створює ієрархію папок на мережевому диску.
        Аналог os.makedirs(path, exist_ok=True).

        :param path: Повний мережевий шлях (напр. r'\\192.168.1.1\Share\2026\02\08')
        """
        try:
            # smbclient.makedirs автоматично створює всі проміжні папки
            makedirs(path, exist_ok=True)
            # print(f"📁 Структуру папок перевірено/створено: {path}")
        except Exception as e:
            print(f"❌ Не вдалося створити папки на SMB: {e}")
            raise

    def get_file_buffer(self, share_path: str) -> io.BytesIO:
        """
        Зчитує файл із сервера та повертає його як об'єкт BytesIO (у пам'яті).

        :param share_path: Шлях до файлу на сервері.
        """
        try:
            with open_file(share_path, mode="rb") as f:
                return io.BytesIO(f.read())
        except Exception as e:
            print(f"❌ Не вдалося прочитати файл {share_path}: {e}")
            return None

    def save_file_from_buffer(self, share_path: str, buffer: io.BytesIO):
        """
        Записує дані з об'єкта BytesIO у файл на сервері.

        :param share_path: Шлях для збереження на сервері.
        :param buffer: Об'єкт BytesIO з даними.
        """
        try:
            buffer.seek(0)  # Скидаємо покажчик на початок перед читанням
            with open_file(share_path, mode="wb") as f:
                f.write(buffer.read())
            print(f"💾 Файл збережено на сервері: {share_path}")
        except Exception as e:
            print(f"❌ Помилка збереження файлу на SMB: {e}")
            raise

    def copy_file(self, local_source_path: str, remote_dest_path: str):
        """
        Копіює локальний файл безпосередньо на мережевий диск.
        Більш ефективно для великих вкладень, ніж використання BytesIO.
        """
        try:
            with open(local_source_path, 'rb') as local_f:
                with open_file(remote_dest_path, mode='wb') as smb_f:
                    # Читаємо та пишемо шматками, щоб не перевантажувати RAM
                    while True:
                        chunk = local_f.read(64 * 1024)  # 64KB
                        if not chunk:
                            break
                        smb_f.write(chunk)
            print(f"📡 Файл успішно скопійовано: {remote_dest_path}")
        except Exception as e:
            print(f"❌ Помилка копіювання файлу на сервер: {e}")
            raise

    # Додайте listdir в імпорт:
    # from smbclient import listdir

    def list_files(self, path: str) -> list:
        """
        Повертає список назв файлів та папок у вказаній директорії на SMB сервері.

        :param path: Повний мережевий шлях до папки.
        """
        try:
            return smbclient.listdir(path)
        except Exception as e:
            print(f"❌ Помилка отримання списку файлів з SMB ({path}): {e}")
            return []

    def close(self):
        """Явне закриття сесії (якщо не використовується 'with')."""
        self.disconnect()