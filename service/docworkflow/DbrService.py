import json
from service.constants import DB_TABLE_DBR_DOC
from service.constants import DOC_STATUS_COMPLETED, DOC_STATUS_DRAFT
from typing import List, Dict, Any, Optional

class DbrService:
    def __init__(self, db, ctx):
        self.db = db
        self.ctx = ctx
        self.table_name = DB_TABLE_DBR_DOC

    def get_all_dbr_docs(self, created_by: Optional[int] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT id, created_by, created_date, status, out_number, out_date, payload 
            FROM """ + DB_TABLE_DBR_DOC
        params = ()

        if created_by:
            query += " WHERE created_by = ?"
            params = (created_by,)

        query += " ORDER BY created_date DESC"

        rows = self.db.__execute_fetchall__(query, params)
        drafts = []

        for r in rows:
            drafts.append({
                'id': r[0],
                'created_by': r[1],
                'created_date': r[2],  # Дата у форматі 'YYYY-MM-DD HH:MM:SS'
                'status': r[3],
                'out_number': r[4],
                'out_date': r[5],
                'payload': json.loads(r[6]) if r[6] else []
            })

        return drafts


    def save_dbr_doc(self, out_number: str, out_date: str, payload: list, dbr_doc_id: int = None) -> int:
        """Зберігає або оновлює чернетку."""
        payload_json = json.dumps(payload, ensure_ascii=False)

        if dbr_doc_id:
            # Оновлюємо існуючу чернетку
            query = f"""
                UPDATE {self.table_name}
                SET out_number = ?, out_date = ?, payload = ?, status = '{DOC_STATUS_DRAFT}'
                WHERE id = ? AND created_by = ?
            """
            self.db.__execute_insert__(query, (out_number, out_date, payload_json, dbr_doc_id, self.ctx.user_id))
            return dbr_doc_id
        else:
            # Створюємо нову чернетку
            query = f"""
                INSERT INTO {self.table_name} (created_by, out_number, out_date, payload, status)
                VALUES (?, ?, ?, ?, '{DOC_STATUS_DRAFT}')
            """
            return self.db.__execute_insert__(query, (self.ctx.user_id, out_number, out_date, payload_json))

    def get_dbr_doc_by_id(self, dbr_doc_id: int) -> dict:
        """Отримує чернетку за ID та розпаковує JSON payload."""
        query = f"SELECT id, out_number, out_date, status, payload FROM {self.table_name} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (dbr_doc_id,))

        if not row:
            return None

        try:
            payload_data = json.loads(row[4]) if row[4] else []
        except json.JSONDecodeError:
            payload_data = []

        return {
            'id': row[0],
            'out_number': row[1],
            'out_date': row[2],
            'status': row[3],
            'payload': payload_data
        }

    def mark_as_completed(self, dbr_doc_id: int, out_number: str, out_date: str) -> bool:
        return self.db.update_record(DB_TABLE_DBR_DOC, dbr_doc_id, {'status': DOC_STATUS_COMPLETED, 'out_number': out_number, 'out_date': out_date})


    def delete_dbr_doc(self, dbr_doc_id: int):
        self.db.delete_record(DB_TABLE_DBR_DOC, dbr_doc_id)
