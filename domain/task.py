from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Task(BaseModel):
    id: Optional[int] = None
    created_by: int
    assignee: Optional[int] = None
    task_status: str = "NEW"
    task_type: Optional[str] = ""
    task_subject: str
    task_details: Optional[str] = ""
    task_deadline: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None