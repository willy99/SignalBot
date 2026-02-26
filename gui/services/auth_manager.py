from werkzeug.security import generate_password_hash, check_password_hash
from nicegui import app
from gui.services.request_context import RequestContext

class AuthManager:
    def __init__(self, db):
        self.db = db
        self._init_default_admin()

    def create_user(self, username: str, password: str, role: str, full_name: str):
        if self.get_user(username):
            return False, "Користувач з таким логіном вже існує"

        pass_hash = generate_password_hash(password, method='pbkdf2:sha256')

        query = "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)"
        user_id = self.db.__execute_insert__(query, (username, pass_hash, role, full_name))

        if user_id:
            return True, "Користувача успішно створено"
        return False, "Помилка бази даних при створенні користувача"

    def authenticate(self, username: str, password: str) -> dict:
        query = "SELECT id, username, password_hash, role, full_name FROM users WHERE username = ? AND is_active = 1"
        user_row = self.db.__execute_fetch__(query, (username,))

        if user_row and check_password_hash(user_row[2], password):
            return {
                'id': user_row[0],
                'username': user_row[1],
                'role': user_row[3],
                'full_name': user_row[4]
            }
        return None

    def get_user_permissions(self, role: str) -> dict:
        query = "SELECT module_name, can_read, can_write, can_delete FROM role_permissions WHERE role = ?"
        rows = self.db.__execute_fetchall__(query, (role,))

        perms = {}
        for r in rows:
            module_name = r[0]
            perms[module_name] = {
                'read': bool(r[1]),
                'write': bool(r[2]),
                'delete': bool(r[3])
            }
        return perms

    def has_access(self, module_name: str, action: str = 'read') -> bool:
        from nicegui import app

        user_info = app.storage.user.get('user_info')
        if not user_info:
            return False

        perms = self.get_user_permissions(user_info['role'])
        module_perms = perms.get(module_name, {})

        return bool(module_perms.get(action, False))

    def get_user(self, username: str) -> dict:
        query = "SELECT id, username, role, full_name, is_active FROM users WHERE username = ?"
        row = self.db.__execute_fetch__(query, (username,))

        if row:
            return {
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'full_name': row[3],
                'is_active': row[4]
            }
        return None

    def get_all_users(self) -> list:
        """Повертає список усіх користувачів системи."""
        query = "SELECT id, username, role, full_name, is_active FROM users"
        rows = self.db.__execute_fetchall__(query)

        users = []
        for r in rows:
            users.append({
                'id': r[0],
                'username': r[1],
                'role': r[2],
                'full_name': r[3],
                'is_active': bool(r[4])
            })
        return users

    def update_user(self, user_id: int, role: str, full_name: str, is_active: bool):
        """Оновлює профіль користувача (без пароля)."""
        query = "UPDATE users SET role = ?, full_name = ?, is_active = ? WHERE id = ?"
        self.db.__execute_insert__(query, (role, full_name, int(is_active), user_id))

    def update_password(self, user_id: int, new_password: str):
        """Встановлює новий пароль для існуючого користувача."""
        pass_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        self.db.__execute_insert__(query, (pass_hash, user_id))
        
    def set_permissions(self, role: str, module_name: str, can_read: int, can_write: int, can_delete: int):

        """
        Встановлює або оновлює права доступу для конкретної ролі у модулі.
        Використовує UPSERT: якщо запис для (role, module_name) вже є, він оновиться.
        """
        query = '''
            INSERT INTO role_permissions (role, module_name, can_read, can_write, can_delete)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(role, module_name) DO UPDATE SET 
                can_read = excluded.can_read,
                can_write = excluded.can_write,
                can_delete = excluded.can_delete
        '''
        return self.db.__execute_insert__(query, (role, module_name, can_read, can_write, can_delete))

    def _init_default_admin(self):
        """Створює адміна при першому запуску, якщо БД порожня."""
        if not self.get_user('admin'):
            self.create_user('admin', 'admin123', 'admin', 'Адміністратор')

            # Надаємо максимальні права на існуючі модулі
            modules = ['search', 'erdr', 'support_doc', 'admin_panel']
            for mod in modules:
                self.set_permissions('admin', mod, can_read=1, can_write=1, can_delete=1)

            print("✅ Створено дефолтного адміністратора (Логін: admin, Пароль: admin123)")


    def get_current_context(self) -> RequestContext:
        user_info = app.storage.user.get('user_info', {})
        ctx = RequestContext(
            user_name = user_info.get('full_name') or user_info.get('username') or 'Гість',
            user_role = user_info.get('role'),
            user_id = user_info.get('id')
        )
        return ctx
