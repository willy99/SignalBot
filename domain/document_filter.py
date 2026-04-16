# domain/document_filter.py
from dataclasses import dataclass
from typing import Optional
import config


@dataclass
class DocumentFilter:
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    out_number: Optional[str] = None
    status: Optional[str] = None
    last_name: Optional[str] = None

    # 💡 Пагінація
    limit: int = config.RECORDS_PER_PAGE
    offset: int = 0