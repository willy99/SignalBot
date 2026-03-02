# from service.connection.MyDataBase import MyDataBase
from gui.services.request_context import RequestContext

class UserService:
    def __init__(self, db):
        self.db = db

    def get_user_state(self, phone_number: str) -> str:
        """Отримує стан користувача (повертає 'START', якщо не знайдено)."""
        query = "SELECT current_state FROM user_states WHERE phone_number = ?"

        # Викликаємо метод з переданого екземпляра БД
        result = self.db.__execute_fetch__(query, (phone_number,))
        return result[0] if result else "START"

    def set_user_state(self, phone_number: str, state: str) -> int:
        """Зберігає або оновлює стан."""
        query = '''
            INSERT INTO user_states (phone_number, current_state, last_update)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET 
                current_state = excluded.current_state,
                last_update = CURRENT_TIMESTAMP
        '''
        return self.db.__execute_insert__(query, (phone_number, state))

    def reset_user(self, phone_number: str) -> int:
        """Скидає стан користувача до початкового."""
        return self.set_user_state(phone_number, "START")