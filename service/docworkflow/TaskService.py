from typing import List
from domain.task import Task, Subtask
from gui.services.request_context import RequestContext
from service.connection.MyDataBase import MyDataBase
from service.constants import DB_TABLE_TASK, TASK_STATUS_IN_PROGRESS, TASK_STATUS_NEW, TASK_STATUS_COMPLETED, DB_TABLE_SUBTASK, DB_DATETIME_FORMAT, DB_DATETIME_START_FORMAT, \
    DB_DATETIME_END_FORMAT
from datetime import datetime, timedelta

class TaskService:
    def __init__(self, db: MyDataBase, ctx: RequestContext):
        self.db = db
        self.ctx = ctx

    def save_task(self, task: Task) -> int:
        current_time = datetime.now()
        task.updated_date = current_time

        task_data = task.model_dump(exclude={'id', 'subtasks'})

        for date_field in ['task_deadline', 'created_date', 'updated_date']:
            if task_data.get(date_field):
                task_data[date_field] = task_data[date_field].strftime(DB_DATETIME_FORMAT)

        if task.id is None:
            task_data['created_by'] = self.ctx.user_id
            task_data['created_date'] = current_time.strftime(DB_DATETIME_FORMAT)
            task_id = self.db.insert_record(DB_TABLE_TASK, task_data)
        else:
            task_id = task.id
            self.db.update_record(DB_TABLE_TASK, task_id, task_data)
            self.db.delete_children(DB_TABLE_SUBTASK, 'task_id', task_id)

        if task.subtasks:
            subtasks_data = []
            for st in task.subtasks:
                st_dict = st.model_dump(exclude={'id'})
                st_dict['task_id'] = task_id
                subtasks_data.append(st_dict)

            self.db.insert_records_batch(DB_TABLE_SUBTASK, subtasks_data)

        return task_id

    def get_all_tasks(self, search_filter: dict) -> List[Task]:
        query = f"SELECT * FROM {DB_TABLE_TASK} WHERE 1=1"
        params = []

        assignee_id = search_filter.get('assignee_id', 'all')
        if assignee_id == 'unassigned':
            query += " AND assignee IS NULL"
        elif assignee_id != 'all' and assignee_id is not None:
            query += " AND assignee = ?"
            params.append(assignee_id)

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
            params.append(f"{created_from} 00:00:00")

        created_to = search_filter.get('created_to')
        if created_to:
            query += " AND created_date <= ?"
            params.append(f"{created_to} 23:59:59")

        period = search_filter.get('period_filter', 'all')
        if period != 'all':
            now = datetime.now()
            now_str = now.strftime(DB_DATETIME_FORMAT)

            today_morning_str = now.strftime(DB_DATETIME_START_FORMAT)
            today_evening_str = now.strftime(DB_DATETIME_END_FORMAT)

            if period == 'today':
                minus_7_str = (now - timedelta(days=7)).strftime(DB_DATETIME_START_FORMAT)
                plus_3_str = (now + timedelta(days=3)).strftime(DB_DATETIME_END_FORMAT)

                query += f" AND ((task_status != '{TASK_STATUS_COMPLETED}' AND (task_deadline IS NULL OR (task_deadline >= ? AND task_deadline <= ?))) OR (task_status = '{TASK_STATUS_COMPLETED}' AND updated_date >= ? AND updated_date <= ?))"
                params.extend([minus_7_str, plus_3_str, today_morning_str, today_evening_str])

            elif period == 'overdue':
                query += f" AND (task_status != '{TASK_STATUS_COMPLETED}' AND task_deadline IS NOT NULL AND task_deadline < ?)"
                params.append(now_str)

            elif period == 'future':
                query += f" AND (task_status != '{TASK_STATUS_COMPLETED}' AND (task_deadline IS NULL OR task_deadline >= ?))"
                params.append(now_str)

        query += " ORDER BY updated_date DESC"
        print(query)
        print(str(params))
        rows = self.db.__execute_fetchall__(query, tuple(params))
        return [Task(**dict(r)) for r in rows]

    def get_task_by_id(self, task_id: int) -> Task:
        query = f"SELECT * FROM {DB_TABLE_TASK} WHERE id = ?"
        task_row = self.db.__execute_fetch__(query, (task_id,))

        if not task_row:
            return None

        task = Task(**dict(task_row))

        sub_query = f"SELECT * FROM {DB_TABLE_SUBTASK} WHERE task_id = ?"
        sub_rows = self.db.__execute_fetchall__(sub_query, (task_id,))

        task.subtasks = [Subtask(**dict(row)) for row in sub_rows]

        return task

    def get_task_counts_for_user(self, user_id) -> tuple[int, int]:
        try:
            now = datetime.now()
            params = []

            query = f"SELECT task_status, COUNT(*) AS count FROM {DB_TABLE_TASK} WHERE assignee = ? and task_status IN ('{TASK_STATUS_NEW}', '{TASK_STATUS_IN_PROGRESS}') "

            minus_7_str = (now - timedelta(days=7)).strftime(DB_DATETIME_START_FORMAT)
            plus_3_str = (now + timedelta(days=3)).strftime(DB_DATETIME_END_FORMAT)
            query += " AND (task_deadline IS NULL OR (task_deadline >= ? AND task_deadline <= ?))"
            query += " GROUP BY task_status "

            params.extend([user_id, minus_7_str, plus_3_str])

            rows = self.db.__execute_fetchall__(query, tuple(params))

            new_c, prog_c = 0, 0
            for r in rows:
                if r['task_status'] == TASK_STATUS_NEW:
                    new_c = r['count']
                elif r['task_status'] == TASK_STATUS_IN_PROGRESS:
                    prog_c = r['count']
            return new_c, prog_c
        except Exception:
            return 0, 0

    def delete_task(self, task_id: int):
        self.db.delete_record(DB_TABLE_TASK, task_id)

    def change_status(self, task_id: int, new_status: str) -> bool:
        data = {
            'task_status': new_status,
            'updated_date': datetime.now().strftime(DB_DATETIME_FORMAT)
        }
        self.db.update_record(DB_TABLE_TASK, task_id, data)
        return True

    def get_triggered_alarms(self, user_id: int) -> list:
        current_time = datetime.now().strftime(DB_DATETIME_FORMAT)

        query = f"SELECT id, task_subject FROM {DB_TABLE_TASK} WHERE assignee = ? AND task_status IN ('{TASK_STATUS_NEW}', '{TASK_STATUS_IN_PROGRESS}') AND task_deadline <= ?"
        rows = self.db.__execute_fetchall__(query, (user_id, current_time))

        return [{'id': r['id'], 'subject': r['task_subject']} for r in rows]