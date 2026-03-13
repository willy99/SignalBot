import json
from datetime import datetime
from typing import List, Optional
from service.constants import DB_TABLE_SUPPORT_DOC, DOC_STATUS_COMPLETED, DB_DATETIME_FORMAT
from service.connection.MyDataBase import MyDataBase
from gui.services.request_context import RequestContext
from domain.support_doc import SupportDoc

class DocSupportService:
    def __init__(self, db: MyDataBase, ctx: RequestContext):
        self.db = db
        self.ctx = ctx
        self.table_name = DB_TABLE_SUPPORT_DOC

    def save_support_doc(self, doc: SupportDoc) -> int:
        doc_data = doc.model_dump(exclude={'id'})
        doc_data['payload'] = json.dumps(doc_data['payload'], ensure_ascii=False)

        if doc_data.get('created_date') and isinstance(doc_data['created_date'], datetime):
            doc_data['created_date'] = doc_data['created_date'].strftime(DB_DATETIME_FORMAT)

        if doc.id is None:
            doc_data['created_by'] = self.ctx.user_id
            doc_data['created_date'] = datetime.now().strftime(DB_DATETIME_FORMAT)
            return self.db.insert_record(self.table_name, doc_data)
        else:
            self.db.update_record(self.table_name, doc.id, doc_data)
            return doc.id

    def get_all_support_docs(self, created_by: Optional[int] = None) -> List[SupportDoc]:
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
            result.append(SupportDoc(**r_dict))

        return result

    def get_support_doc_by_id(self, support_doc_id: int) -> Optional[SupportDoc]:
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        row = self.db.__execute_fetch__(query, (support_doc_id,))

        if not row:
            return None

        r_dict = dict(row)
        r_dict['payload'] = json.loads(r_dict['payload']) if r_dict.get('payload') else []
        return SupportDoc(**r_dict)

    def delete_support_doc(self, support_doc_id: int):
        self.db.delete_record(self.table_name, support_doc_id)

    def mark_as_completed(self, support_doc_id: int) -> bool:
        self.db.update_record(self.table_name, support_doc_id, {'status': DOC_STATUS_COMPLETED})
        return True