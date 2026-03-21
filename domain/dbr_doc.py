from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Any
from dics.deserter_xls_dic import *
from service.constants import DOC_STATUS_DRAFT

class DbrDoc(BaseModel):
    id: Optional[int] = None
    created_by: Optional[int] = None
    created_date: Optional[datetime] = None
    status: str = DOC_STATUS_DRAFT
    out_number: Optional[str] = ''
    out_date: Optional[str] = ''
    payload: List[Any] = Field(default_factory=list)
    deleted: Optional[int] = None