from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class PersonSearchFilter:
    query: Optional[str] = None
    o_ass_num: Optional[str] = None
    title: Optional[str] = None
    title2: Optional[str] = None
    service_type: Optional[str] = None

    # Дати СЗЧ
    des_year: Optional[Union[str, list]] = None
    des_date_from: Optional[str] = None
    des_date_to: Optional[str] = None

    # Дата внесення (Рік)
    ins_year: Optional[Union[str, list]] = None