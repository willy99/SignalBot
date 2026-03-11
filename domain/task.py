from pydantic import BaseModel, Field
from typing import Optional, Final, List
from datetime import datetime

class Subtask(BaseModel):
    title: str
    is_done: bool = False
    id: Optional[int] = None
    task_id: Optional[int] = None

class Task(BaseModel):
    id: Optional[int] = None
    task_subject: str
    task_details: Optional[str] = ''
    task_type: Optional[str] = 'Інше'
    assignee: Optional[int] = None
    task_status: str = 'NEW'
    task_deadline: Optional[datetime] = None
    created_by: Optional[int] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    subtasks: List[Subtask] = Field(default_factory=list)