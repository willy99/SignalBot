from pydantic import BaseModel
from datetime import date

class DailyDashboardEntry(BaseModel):
    report_date: date
    total_awol: int
    in_search: int
    returned: int
    res_returned: int
    in_disposal: int