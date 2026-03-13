from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Any
from dics.deserter_xls_dic import *
from service.constants import DOC_STATUS_DRAFT

class SupportDoc(BaseModel):
    id: Optional[int] = None
    created_by: Optional[int] = None
    created_date: Optional[datetime] = None
    region: Optional[str] = None
    status: str = DOC_STATUS_DRAFT
    city: Optional[str] = ''
    support_number: Optional[str] = ''
    support_date: Optional[str] = ''
    payload: List[Any] = Field(default_factory=list)
