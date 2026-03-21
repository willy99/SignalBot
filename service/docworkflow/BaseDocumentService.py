import json
from datetime import datetime
from typing import List, Optional, Type, TypeVar, Generic
from pydantic import BaseModel
from domain.document_filter import DocumentFilter
from gui.services.request_context import RequestContext
from service.connection.MyDataBase import MyDataBase
from service.constants import DOC_STATUS_COMPLETED, DB_DATETIME_FORMAT

T = TypeVar('T', bound=BaseModel)

class BaseDocumentService(Generic[T]):
    def __init__(self, db:MyDataBase, ctx: RequestContext, table_name: str, model_class: Type[T]):
        self.db = db
        self.ctx = ctx
        self.table_name = table_name
        self.model_class = model_class

    def _parse_row(self, row) -> T:
        """Допоміжний метод: перетворює рядок з БД у Pydantic-модель"""
        r_dict = dict(row)
        if r_dict.get('payload'):
            r_dict['payload'] = json.loads(r_dict['payload'])
        else:
            r_dict['payload'] = []
        # Ініціалізуємо конкретну модель (NotifDoc, DbrDoc тощо)
        return self.model_class(**r_dict)

    def get_all_docs(self, created_by: Optional[int] = None) -> List[T]:
        query = f"SELECT * FROM {self.table_name} WHERE (deleted = 0 OR deleted IS NULL)"
        params = []

        if created_by:
            query += " WHERE created_by = ?"
            params.append(created_by)

        query += " ORDER BY created_date DESC"
        rows = self.db.__execute_fetchall__(query, tuple(params))

        return [self._parse_row(r) for r in rows]

    def get_doc_by_id(self, doc_id: int) -> Optional[T]:
        query = f"SELECT * FROM {self.table_name} WHERE id = ? AND (deleted = 0 OR deleted IS NULL)"
        row = self.db.__execute_fetch__(query, (doc_id,))
        if not row:
            return None
        return self._parse_row(row)

    def save_doc(self, doc: T) -> int:
        doc_data = doc.model_dump(exclude={'id'})
        doc_data['payload'] = json.dumps(doc_data.get('payload', []), ensure_ascii=False)
        if 'deleted' in doc_data and doc_data['deleted'] is None:
            doc_data['deleted'] = 0

        if doc_data.get('created_date') and isinstance(doc_data['created_date'], datetime):
            doc_data['created_date'] = doc_data['created_date'].strftime(DB_DATETIME_FORMAT)

        if getattr(doc, 'id', None) is None:
            doc_data['created_by'] = self.ctx.user_id
            doc_data['created_date'] = datetime.now().strftime(DB_DATETIME_FORMAT)
            return self.db.insert_record(self.table_name, doc_data)
        else:
            doc_data.pop('created_by', None)
            doc_data.pop('created_date', None)
            self.db.update_record(self.table_name, doc.id, doc_data)
            return doc.id

    def mark_as_completed(self, doc_id: int, out_number: Optional[str] = None, out_date: Optional[str] = None, extra_data: dict = None) -> bool:
        data = {'status': DOC_STATUS_COMPLETED}

        if out_number is not None:
            data['out_number'] = out_number
        if out_date is not None:
            data['out_date'] = out_date

        if extra_data:
            data.update(extra_data)

        self.db.update_record(self.table_name, doc_id, data)
        return True

    def delete_doc(self, doc_id: int):
        data = {'deleted': 1}
        self.db.update_record(self.table_name, doc_id, data)
        # self.db.delete_record(self.table_name, doc_id)

    def search_docs(self, doc_filter: DocumentFilter, created_by: Optional[int] = None) -> List[T]:
        """Універсальний пошук для всіх типів пакетів"""
        query = f"SELECT * FROM {self.table_name} WHERE (deleted = 0 OR deleted IS NULL)"
        params = []

        if created_by:
            query += " AND created_by = ?"
            params.append(created_by)

        if doc_filter.status:
            query += " AND status = ?"
            params.append(doc_filter.status)

        if doc_filter.out_number:
            query += " AND out_number LIKE ?"
            params.append(f"%{doc_filter.out_number}%")

        if doc_filter.date_from:
            try:
                iso_from = datetime.strptime(doc_filter.date_from, '%d.%m.%Y').strftime('%Y-%m-%d')
                query += " AND date(created_date) >= ?"
                params.append(iso_from)
            except ValueError:
                pass

        if doc_filter.date_to:
            try:
                iso_to = datetime.strptime(doc_filter.date_to, '%d.%m.%Y').strftime('%Y-%m-%d')
                query += " AND date(created_date) <= ?"
                params.append(iso_to)
            except ValueError:
                pass

        # 💡 Точка розширення: дозволяє дочірнім класам додавати свої специфічні фільтри
        query, params = self._apply_extra_filters(query, params, doc_filter)

        query += " ORDER BY created_date DESC"
        rows = self.db.__execute_fetchall__(query, tuple(params))

        return [self._parse_row(r) for r in rows]

    def _apply_extra_filters(self, query: str, params: list, doc_filter: DocumentFilter) -> tuple[str, list]:
        """Перевизначте цей метод у дочірньому класі, якщо треба фільтрувати по специфічних полях (напр. region)"""
        return query, params

    def is_existing_num(self, out_number: str, exclude_id: Optional[int] = None) -> bool:
        """
        Перевіряє, чи вже існує такий вихідний номер у базі.
        Ігнорує видалені документи (deleted = 1) та порожні номери.
        """
        if not out_number or not str(out_number).strip():
            return False

        clean_number = str(out_number).strip()

        # Шукаємо тільки серед активних (не видалених) документів
        query = f"SELECT 1 FROM {self.table_name} WHERE out_number = ? AND (deleted = 0 OR deleted IS NULL)"
        params = [clean_number]

        # Якщо ми редагуємо існуючий документ, ігноруємо його власний ID
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)

        # Виконуємо запит (якщо знайде хоч один рядок - поверне True)
        row = self.db.__execute_fetch__(query, tuple(params))

        return bool(row)