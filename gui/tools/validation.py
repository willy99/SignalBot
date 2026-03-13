from datetime import datetime
import re
from dics.deserter_xls_dic import VALID_PATTERN_DOC_NUM

def is_number(s):
    try:
        float(s) # Try converting to a float
        return True
    except ValueError:
        return False


def is_valid_doc_number(number_str: str) -> bool:
    """
    Перевіряє, чи відповідає номер супроводу формату 642/XXXX,
    де X - від 1 до 4 цифр.
    """
    if not number_str:
        return False

    return bool(re.match(VALID_PATTERN_DOC_NUM, str(number_str).strip()))