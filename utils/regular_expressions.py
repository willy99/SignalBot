from dics.deserter_xls_dic import *
import re

def extract_locality(conditions: str) -> str:
    if not conditions or conditions == NA:
        return NA
    match = re.search(PATTERN_LOCALITY, conditions)
    if match:
        return match.group(1)
    return NA

