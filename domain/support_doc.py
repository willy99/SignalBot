from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Any, Union
from dics.deserter_xls_dic import *
from service.constants import DOC_STATUS_DRAFT

class SupportDoc(BaseModel):
    id: Optional[int] = None
    created_by: Union[int, str, None] = None
    created_date: Optional[datetime] = None
    region: Optional[str] = None
    status: str = DOC_STATUS_DRAFT
    city: Optional[str] = ''
    out_number: Optional[str] = ''
    out_date: Optional[str] = ''
    payload: List[Any] = Field(default_factory=list)
    package_type: Optional[str] = ''
