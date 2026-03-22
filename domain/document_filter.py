# domain/document_filter.py
from dataclasses import dataclass
from typing import Optional

from config import RECORDS_PER_PAGE


@dataclass
class DocumentFilter:
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    out_number: Optional[str] = None
    status: Optional[str] = None

    # 💡 Пагінація
    limit: int = RECORDS_PER_PAGE
    offset: int = 0