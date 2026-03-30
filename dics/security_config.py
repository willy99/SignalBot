# todo - викинути це в базьонку
from typing import Final

AVAILABLE_ROLES:Final[list[str]] = ['admin', 'Командір', 'Офіс', 'Бджілка', 'Гість']

PERM_READ = 'read'
PERM_EDIT = 'write'
PERM_DELETE = 'delete'

MODULE_SEARCH:Final[str] = 'search'
MODULE_PERSON:Final[str] = 'person'
MODULE_TASK:Final[str] = 'task'
MODULE_DOC_SUPPORT:Final[str] = 'doc_support'
MODULE_DOC_NOTIF:Final[str] = 'doc_notif'
MODULE_DOC_DBR:Final[str] = 'doc_dbr'
MODULE_REPORT_UNITS:Final[str] = 'report_units'
MODULE_REPORT_GENERAL:Final[str] = 'report_general'
MODULE_ADMIN:Final[str] = 'admin_panel'

AVAILABLE_MODULES:Final[dict[str, str]] = {
    MODULE_SEARCH: 'Загальний доступ',
    MODULE_PERSON: 'База СЗЧ',
    MODULE_TASK: 'Менеджер задач',
    MODULE_DOC_SUPPORT: 'Документація: Супроводи',
    MODULE_DOC_NOTIF: 'Документація: Довідки',
    MODULE_DOC_DBR: 'Документація: ДБР & ЄРДР',
    MODULE_REPORT_UNITS: 'Звітність: По підрозділам',
    MODULE_REPORT_GENERAL: 'Звітність основна',
    MODULE_ADMIN: 'Адміністративна панель'
}

