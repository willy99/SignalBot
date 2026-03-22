from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Any, Union
from dics.deserter_xls_dic import *
from service.constants import DOC_STATUS_DRAFT

class NotifDoc(BaseModel):
    id: Optional[int] = None
    created_by: Union[int, str, None] = None
    created_date: Optional[datetime] = None
    status: str = DOC_STATUS_DRAFT
    out_number: Optional[str] = ''
    out_date: Optional[str] = ''
    region: Optional[str] = ''
    payload: List[Any] = Field(default_factory=list)
    deleted: Optional[int] = None