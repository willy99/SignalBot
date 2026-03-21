# domain/document_filter.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class DocumentFilter:
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    out_number: Optional[str] = None
    status: Optional[str] = None