from domain.support_doc import SupportDoc
from service.constants import DB_TABLE_SUPPORT_DOC
from service.docworkflow.BaseDocumentService import BaseDocumentService


class DocSupportService(BaseDocumentService[SupportDoc]):
    def __init__(self, db, ctx):
        super().__init__(db, ctx, DB_TABLE_SUPPORT_DOC, SupportDoc)
