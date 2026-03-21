# service/dbr_service.py
from domain.dbr_doc import DbrDoc
from service.constants import DB_TABLE_DBR_DOC
from service.docworkflow.BaseDocumentService import BaseDocumentService

class DbrService(BaseDocumentService[DbrDoc]):
    def __init__(self, db, ctx):
        super().__init__(db, ctx, DB_TABLE_DBR_DOC, DbrDoc)