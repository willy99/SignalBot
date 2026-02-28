import json
from typing import List, Dict, Any, Optional, Final
from service.connection.MyDataBase import DB_TABLE_SUPPORT_DOC
from service.connection.MyDataBase import MyDataBase
from gui.services.request_context import RequestContext
SUPPORT_DOC_STATUS_DRAFT: Final[str] = 'Draft'
SUPPORT_DOC_STATUS_COMPLETED: Final[str] = 'Completed'

class DocSupportService:
    def __init__(self, db:MyDataBase, ctx: RequestContext):
        self.db = db
        self.ctx = ctx

    def save_support_doc(self, city: str, support_number: str, support_date, buffer_data: list,
                   support_doc_id: Optional[int] = None) -> int:
        payload_json = json.dumps(buffer_data, ensure_ascii=False)

        data_to_save = {
            'city': city,
            'support_number': support_number,
            'support_date': support_date,
            'payload': payload_json
        }

        if support_doc_id:
            # ОНОВЛЕННЯ ІСНУЮЧОЇ ЧЕРНЕТКИ
            self.db.update_record(DB_TABLE_SUPPORT_DOC, support_doc_id, data_to_save)
            return support_doc_id
        else:
            # СТВОРЕННЯ НОВОЇ ЧЕРНЕТКИ
            data_to_save['created_by'] = self.ctx.user_id
            data_to_save['status'] = SUPPORT_DOC_STATUS_DRAFT  # Початковий статус
            return self.db.insert_record(DB_TABLE_SUPPORT_DOC, data_to_save)

    def get_all_support_docs(self, created_by: Optional[int] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT id, created_by, created_date, status, city, support_number, support_date, payload 
            FROM """ + DB_TABLE_SUPPORT_DOC
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
                'city': r[4],
                'support_number': r[5],
                'support_date': r[6],
                'payload': json.loads(r[7]) if r[7] else []
            })

        return drafts

    def get_support_doc_by_id(self, support_doc_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT id, created_by, created_date, status, city, support_number, support_date, payload 
            FROM """ + DB_TABLE_SUPPORT_DOC + """ WHERE id = ?
        """
        r = self.db.__execute_fetch__(query, (support_doc_id,))

        if r:
            return {
                'id': r[0],
                'created_by': r[1],
                'created_date': r[2],
                'status': r[3],
                'city': r[4],
                'support_number': r[5],
                'support_date': r[6],
                'payload': json.loads(r[7]) if r[7] else []
            }
        return None

    def delete_support_doc(self, support_doc_id: int):
        self.db.delete_record(DB_TABLE_SUPPORT_DOC, support_doc_id)

    def mark_as_completed(self, support_doc_id: int) -> bool:
        self.db.update_record(DB_TABLE_SUPPORT_DOC, support_doc_id, {'status': SUPPORT_DOC_STATUS_COMPLETED})
        return True