from domain.notif_doc import NotifDoc
from service.constants import DB_TABLE_NOTIF_DOC
from service.docworkflow.BaseDocumentService import BaseDocumentService

class NotifService(BaseDocumentService[NotifDoc]):
    def __init__(self, db, ctx):
        super().__init__(db, ctx, DB_TABLE_NOTIF_DOC, NotifDoc)