from domain.task import *
from gui.services.request_context import RequestContext
from service.connection.MyDataBase import MyDataBase
from service.constants import DB_TABLE_TASK, TASK_STATUS_IN_PROGRESS, TASK_STATUS_NEW, TASK_STATUS_COMPLETED, DB_TABLE_SUBTASK
from datetime import datetime, timedelta

class TaskService:
    def __init__(self, db: MyDataBase, ctx: RequestContext):
        self.db = db
        self.ctx = ctx

    def save_task(self, task: Task) -> int:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        task_data = {
            'task_subject': task.task_subject,
            'task_details': task.task_details,
            'task_type': task.task_type,
            'assignee': task.assignee,
            'task_status': task.task_status,
            'task_deadline': task.task_deadline,
            'updated_date': current_time
        }

        if task.id is None:
            task_data['created_by'] = self.ctx.user_id
            task_data['created_date'] = current_time
            task_id = self.db.insert_record(DB_TABLE_TASK, task_data)

        else:
            task_id = task.id
            self.db.update_record(DB_TABLE_TASK, task_id, task_data)

            self.db.delete_children(DB_TABLE_SUBTASK, 'task_id', task_id)

        if task.subtasks:
            subtasks_data = [
                {
                    'task_id': task_id,
                    'title': st.title,
                    'is_done': 1 if st.is_done else 0
                }
                for st in task.subtasks
            ]
            self.db.insert_records_batch(DB_TABLE_SUBTASK, subtasks_data)

        return task_id

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

        task_type = search_filter.get('task_type_filter', 'all')
        if task_type != 'all' and task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type)

        created_year = search_filter.get('created_year')
        if created_year:
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

        period = search_filter.get('period_filter', 'all')
        if period != 'all':
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')

            today_morning_str = now.strftime('%Y-%m-%d 00:00:00')
            today_evening_str = now.strftime('%Y-%m-%d 23:59:59')

            if period == 'today':
                # ⚡ На сьогодні:
                # (Активні задачі: без дедлайну АБО з дедлайном від -7 до +3 днів)
                # АБО
                # (Завершені задачі: оновлені саме сьогодні)
                minus_7_str = (now - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
                plus_3_str = (now + timedelta(days=3)).strftime('%Y-%m-%d 23:59:59')

                query += f""" AND (
                    (task_status != '{TASK_STATUS_COMPLETED}' AND (task_deadline IS NULL OR (task_deadline >= ? AND task_deadline <= ?)))
                    OR 
                    (task_status = '{TASK_STATUS_COMPLETED}' AND updated_date >= ? AND updated_date <= ?)
                )"""
                params.extend([minus_7_str, plus_3_str, today_morning_str, today_evening_str])

            elif period == 'overdue':
                # 🔥 Прострочені: тільки активні, де є дедлайн і він у минулому
                query += f" AND (task_status != '{TASK_STATUS_COMPLETED}' AND task_deadline IS NOT NULL AND task_deadline < ?)"
                params.append(now_str)

            elif period == 'future':
                # 📅 Майбутні: тільки активні, дедлайн більший за зараз АБО безстрокові
                query += f" AND (task_status != '{TASK_STATUS_COMPLETED}' AND (task_deadline IS NULL OR task_deadline >= ?))"
                params.append(now_str)

        query += " ORDER BY updated_date DESC"

        rows = self.db.__execute_fetchall__(query, tuple(params))
        return [self._map_row_to_task(r) for r in rows]

    def get_task_by_id(self, task_id: int) -> Task:
        query = "SELECT * FROM task WHERE id = ?"
        task_row = self.db.__execute_fetch__(query, (task_id,))

        if not task_row:
            return None

        task = self._map_row_to_task(task_row)

        sub_query = "SELECT id, task_id, title, is_done FROM subtask WHERE task_id = ?"
        sub_rows = self.db.__execute_fetchall__(sub_query, (task_id,))

        task.subtasks = [
            Subtask(
                id=row['id'],
                task_id=row['task_id'],
                title=row['title'],
                is_done=bool(row['is_done'])
            ) for row in sub_rows
        ]

        return task

    def get_task_counts_for_user(self, user_id) -> tuple[int, int]:
        try:
            now = datetime.now()
            params = []
            query = f"SELECT task_status, COUNT(*) FROM {DB_TABLE_TASK} WHERE assignee = ? and task_status IN ('{TASK_STATUS_NEW}', '{TASK_STATUS_IN_PROGRESS}') "

            minus_7_str = (now - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
            plus_3_str = (now + timedelta(days=3)).strftime('%Y-%m-%d 23:59:59')
            query += " AND (task_deadline IS NULL OR (task_deadline >= ? AND task_deadline <= ?))"
            query += " GROUP BY task_status "

            params.extend([user_id, minus_7_str, plus_3_str])

            rows = self.db.__execute_fetchall__(query, tuple(params))

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

    def _map_row_to_task(self, task_row: tuple) -> Task:
        """Допоміжний метод для перетворення сирого рядка з БД у Pydantic модель."""

        def parse_date(date_str):
            if not date_str: return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None

        task = Task(
            id=task_row['id'],
            task_subject=task_row['task_subject'],
            task_details=task_row['task_details'],
            task_type=task_row['task_type'],
            assignee=task_row['assignee'],
            task_status=task_row['task_status'],
            task_deadline=parse_date(task_row['task_deadline']),
            created_by = task_row['created_by'],
            created_date=parse_date(task_row['created_date']),
            updated_date=parse_date(task_row['updated_date']),
            subtasks=[]
        )

        return task

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