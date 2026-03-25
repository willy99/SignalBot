from dataclasses import dataclass
from typing import Optional, Union, Final, List

from dics.deserter_xls_dic import MIL_UNITS

# options for topic search
YES: Final[str] = 'Yes'
NO: Final[str] = 'No'

@dataclass
class PersonSearchFilter:
    mil_unit: Optional[str] = MIL_UNITS[0]
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

    # for dbr, support topic search
    empty_kpp:[str] = None #Yes/No
    review_statuses: Optional[list] = None

    desertion_region:[str] = None

    include_402:[str] = None
    main_units: List[str] = None