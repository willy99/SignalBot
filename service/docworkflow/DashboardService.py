from datetime import date
import logging

from service.connection.MyDataBase import MyDataBase
from service.constants import DB_TABLE_DASHBOARD


class DashboardService:
    def __init__(self, db: MyDataBase):
        """
        db_engine має підтримувати метод execute(sql, params)
        де params — це кортеж (tuple) або список.
        """
        self.db = db
        self.logger = logging.getLogger("DashboardService")

    def save_daily_stats(self, stats: dict, target_date: date = None):
        """
        Зберігає або оновлює статистику через UPSERT.
        Використовуємо стандартні плейсхолдери '?' для SQLite.
        """
        if target_date is None:
            target_date = date.today()

        # Порядок аргументів має суворо збігатися з порядком у SQL запиті
        sql_date = target_date.isoformat()

        # VALUES (?, ?, ?, ?, ?, ?)
        # ON CONFLICT(report_date) DO UPDATE SET ...
        query = f"""
            INSERT INTO {DB_TABLE_DASHBOARD} (
                report_date, total_awol, in_search, returned, res_returned, in_disposal, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(report_date) DO UPDATE SET
                total_awol = excluded.total_awol,
                in_search = excluded.in_search,
                returned = excluded.returned,
                res_returned = excluded.res_returned,
                in_disposal = excluded.in_disposal,
                updated_at = datetime('now')
        """

        params = (
            sql_date,
            stats.get('total_awol', 0),
            stats.get('in_search', 0),
            stats.get('returned', 0),
            stats.get('res_returned', 0),
            stats.get('in_disposal', 0)
        )

        try:
            self.db.__execute_query__(query, params)
            return True
        except Exception as e:
            self.logger.error(f"SQL Error in save_daily_stats: {e}")
            return False

    def get_latest_stats(self):
        """Отримання останнього запису"""
        query = f"SELECT * FROM {DB_TABLE_DASHBOARD} ORDER BY report_date DESC LIMIT 1"
        return self.db.__execute_fetch__(query)

    def get_history(self, days: int = 30):
        """
        Отримання історії за період.
        Параметр офсету також передаємо безпечно.
        """
        # SQLite дозволяє використовувати вирази в параметрах,
        # але краще передати готовий рядок офсету
        query = f"""
            SELECT * FROM {DB_TABLE_DASHBOARD} 
            WHERE report_date >= date('now', ?)
            ORDER BY report_date ASC
        """
        offset = f"-{days} days"
        return self.db.__execute_fetchall__(query, (offset,))