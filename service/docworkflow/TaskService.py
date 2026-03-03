from typing import List
from domain.task import *
from gui.services.request_context import RequestContext
from service.connection.MyDataBase import MyDataBase
from service.constants import DB_TABLE_TASK, TASK_STATUS_IN_PROGRESS, TASK_STATUS_NEW, TASK_STATUS_COMPLETED
from datetime import datetime, timedelta

class TaskService:
    def __init__(self, db: MyDataBase, ctx: RequestContext):
        self.db = db
        self.ctx = ctx

    def save_task(self, task: Task) -> int:
        """Зберігає нову або оновлює існуючу задачу."""

        # Перетворюємо Pydantic модель у словник, виключаючи системні поля, які ми контролюємо самі
        data_to_save = task.model_dump(exclude={'id', 'created_date', 'updated_date'}, exclude_none=True)
        if task.task_deadline:
            data_to_save['task_deadline'] = task.task_deadline.strftime('%Y-%m-%d %H:%M:%S')
        else:
            data_to_save['task_deadline'] = None

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if task.id:
            # ОНОВЛЕННЯ ІСНУЮЧОЇ ЗАДАЧІ
            data_to_save['updated_date'] = current_time
            self.db.update_record(DB_TABLE_TASK, task.id, data_to_save)
            return task.id
        else:
            # СТВОРЕННЯ НОВОЇ ЗАДАЧІ
            data_to_save['created_by'] = self.ctx.user_id  # Примусово ставимо автора з контексту
            data_to_save['task_status'] = TASK_STATUS_NEW
            data_to_save['created_date'] = current_time
            data_to_save['updated_date'] = current_time
            return self.db.insert_record(DB_TABLE_TASK, data_to_save)

    def get_all_tasks(self, search_filter: dict) -> List[Task]:
        """
        Отримує всі задачі, динамічно будуючи SQL-запит на основі словника фільтрів з UI.
        """
        query = f"""
            SELECT id, created_by, assignee, task_status, task_type, 
                   task_subject, task_details, task_deadline, created_date, updated_date 
            FROM {DB_TABLE_TASK} 
            WHERE 1=1
        """
        params = []

        # 1. Фільтр по виконавцю (assignee)
        assignee_id = search_filter.get('assignee_id', 'all')
        if assignee_id == 'unassigned':
            query += " AND assignee IS NULL"
        elif assignee_id != 'all' and assignee_id is not None:
            query += " AND assignee = ?"
            params.append(assignee_id)

        # Автор (якщо передано, наприклад, для перегляду "задач, які я створив")
        #if created_by:
        #    query += " AND created_by = ?"
        #    params.append(created_by)

        # 3. Фільтр по типу задачі
        task_type = search_filter.get('task_type_filter', 'all')
        if task_type != 'all' and task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type)

        # 4. Фільтр по даті створення (Рік, З, До)
        created_year = search_filter.get('created_year')
        if created_year:
            # У SQLite дати зберігаються як рядки 'YYYY-MM-DD ...'
            query += " AND created_date LIKE ?"
            params.append(f"{created_year}-%")

        created_from = search_filter.get('created_from')
        if created_from:
            query += " AND created_date >= ?"
            params.append(f"{created_from} 00:00:00")  # Початок доби

        created_to = search_filter.get('created_to')
        if created_to:
            query += " AND created_date <= ?"
            params.append(f"{created_to} 23:59:59")  # Кінець доби

        # 5. Тематичний період (дедлайни)
        period = search_filter.get('period_filter', 'all')
        if period != 'all':
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')

            # Логічно: якщо ми шукаємо "прострочені" чи "на сьогодні",
            # нас цікавлять тільки АКТИВНІ задачі. Завершені ми відкидаємо.
            query += f" AND task_status != '{TASK_STATUS_COMPLETED}'"

            if period == 'overdue':
                # 🔥 Прострочені: є дедлайн і він у минулому
                query += " AND task_deadline IS NOT NULL AND task_deadline < ?"
                params.append(now_str)

            elif period == 'today':
                # ⚡ На сьогодні: від -7 днів до +3 днів, АБО безстрокові
                minus_7_str = (now - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
                plus_3_str = (now + timedelta(days=3)).strftime('%Y-%m-%d 23:59:59')
                query += " AND (task_deadline IS NULL OR (task_deadline >= ? AND task_deadline <= ?))"
                params.extend([minus_7_str, plus_3_str])

            elif period == 'future':
                # 📅 Майбутні: дедлайн більший за зараз, АБО безстрокові
                query += " AND (task_deadline IS NULL OR task_deadline >= ?)"
                params.append(now_str)

        # Сортуємо: найсвіжіші зміни — зверху
        query += " ORDER BY updated_date DESC"

        # Виконуємо запит
        rows = self.db.__execute_fetchall__(query, tuple(params))
        return [self._map_row_to_task(r) for r in rows]

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Отримує конкретну задачу за ID."""
        query = f"SELECT id, created_by, assignee, task_status, task_type, task_subject, task_details, task_deadline, created_date, updated_date FROM {DB_TABLE_TASK} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (task_id,))

        if row:
            return self._map_row_to_task(row)
        return None

    def get_task_counts_for_user(self, user_id) -> tuple[int, int]:
        try:
            query = f"SELECT task_status, COUNT(*) FROM {DB_TABLE_TASK} WHERE assignee = ? and task_status IN ('{TASK_STATUS_NEW}', '{TASK_STATUS_IN_PROGRESS}') GROUP BY task_status"
            rows = self.db.__execute_fetchall__(query, (user_id,))
            new_c, prog_c = 0, 0
            for r in rows:
                if r[0] == 'NEW':
                    new_c = r[1]
                elif r[0] == 'IN_PROGRESS':
                    prog_c = r[1]
            return new_c, prog_c
        except Exception:
            return 0, 0

    def delete_task(self, task_id: int):
        """Видаляє задачу."""
        self.db.delete_record(DB_TABLE_TASK, task_id)

    def change_status(self, task_id: int, new_status: str) -> bool:
        """Швидка зміна статусу (наприклад, для Drag&Drop на канбан-дошці)."""
        data = {
            'task_status': new_status,
            'updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.db.update_record(DB_TABLE_TASK, task_id, data)
        return True

    def _map_row_to_task(self, r: tuple) -> Task:
        """Допоміжний метод для перетворення сирого рядка з БД у Pydantic модель."""

        # Функція для безпечного парсингу дат з рядка
        def parse_date(date_str):
            if not date_str: return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None

        return Task(
            id=r[0],
            created_by=r[1],
            assignee=r[2],
            task_status=r[3],
            task_type=r[4],
            task_subject=r[5],
            task_details=r[6],
            task_deadline=parse_date(r[7]),
            created_date=parse_date(r[8]),
            updated_date=parse_date(r[9])
        )

    def get_triggered_alarms(self, user_id: int) -> list:
        """Повертає ID та Теми задач, дедлайн яких ЩОЙНО настав або вже минув"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = f"""
            SELECT id, task_subject 
            FROM {DB_TABLE_TASK} 
            WHERE assignee = ? 
              AND task_status IN ('{TASK_STATUS_NEW}', '{TASK_STATUS_IN_PROGRESS}') 
              AND task_deadline <= ?
        """
        rows = self.db.__execute_fetchall__(query, (user_id, current_time))
        return [{'id': r[0], 'subject': r[1]} for r in rows]