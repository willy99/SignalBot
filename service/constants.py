from typing import List, Dict, Any, Optional, Final

DB_DATETIME_FORMAT: Final[str] = '%Y-%m-%d %H:%M:%S'
DB_DATETIME_START_FORMAT: Final[str] = '%Y-%m-%d 00:00:00'
DB_DATETIME_END_FORMAT: Final[str] = '%Y-%m-%d 23:59:59'

DB_DATE_FORMAT: Final[str] = '%Y-%m-%d'

DB_TABLE_SUPPORT_DOC: Final[str] = 'support_docs'
DB_TABLE_DBR_DOC: Final[str] = 'dbr_docs'
DB_TABLE_NOTIF_DOC: Final[str] = 'notif_docs'
DB_TABLE_TASK: Final[str] = 'task'
DB_TABLE_SUBTASK: Final[str] = 'subtask'

DOC_STATUS_DRAFT: Final[str] = 'Draft'
DOC_STATUS_COMPLETED: Final[str] = 'Completed'

TASK_STATUS_NEW: Final[str] = 'NEW'
TASK_STATUS_IN_PROGRESS: Final[str] = 'IN_PROGRESS'
TASK_STATUS_COMPLETED: Final[str] = 'COMPLETED'
TASK_STATUS_CANCELED: Final[str] = 'CANCELED'

MONTHS = ['', 'Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень',
              'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']
