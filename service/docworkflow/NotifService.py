import json
from datetime import datetime
from typing import List, Optional, Any
from domain.notif_doc import NotifDoc
from service.constants import DB_TABLE_NOTIF_DOC, DOC_STATUS_COMPLETED, DB_DATETIME_FORMAT


class NotifService:
    def __init__(self, db, ctx):
        self.db = db
        self.ctx = ctx
        self.table_name = DB_TABLE_NOTIF_DOC

    def get_all_docs(self, created_by: Optional[int] = None) -> List[NotifDoc]:
        query = f"SELECT * FROM {self.table_name}"
        params = []

        if created_by:
            query += " WHERE created_by = ?"
            params.append(created_by)

        query += " ORDER BY created_date DESC"

        rows = self.db.__execute_fetchall__(query, tuple(params))
        result = []

        for r in rows:
            r_dict = dict(r)
            r_dict['payload'] = json.loads(r_dict['payload']) if r_dict.get('payload') else []
            result.append(NotifDoc(**r_dict))

        return result

    def save_doc(self, doc: NotifDoc) -> int:
        doc_data = doc.model_dump(exclude={'id'})
        doc_data['payload'] = json.dumps(doc_data['payload'], ensure_ascii=False)

        if doc_data.get('created_date') and isinstance(doc_data['created_date'], datetime):
            doc_data['created_date'] = doc_data['created_date'].strftime(DB_DATETIME_FORMAT)

        if doc.id is None:
            doc_data['created_by'] = self.ctx.user_id
            doc_data['created_date'] = datetime.now().strftime(DB_DATETIME_FORMAT)
            return self.db.insert_record(self.table_name, doc_data)
        else:
            doc_data.pop('created_by', None)
            doc_data.pop('created_date', None)
            self.db.update_record(self.table_name, doc.id, doc_data)
            return doc.id

    def get_doc_by_id(self, doc_id: int) -> Optional[NotifDoc]:
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (doc_id,))

        if not row:
            return None

        r_dict = dict(row)
        r_dict['payload'] = json.loads(r_dict['payload']) if r_dict.get('payload') else []
        return NotifDoc(**r_dict)

    def mark_as_completed(self, doc_id: int, out_number: str, out_date: str) -> bool:
        data = {
            'status': DOC_STATUS_COMPLETED,
            'out_number': out_number,
            'out_date': out_date
        }
        self.db.update_record(self.table_name, doc_id, data)
        return True

    def delete_doc(self, doc_id: int):
        self.db.delete_record(self.table_name, doc_id)