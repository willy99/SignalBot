from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime

@dataclass
class User:
    id: int
    username: str
    role: str
    full_name: str
    is_active: bool = True

    # --- БЕЗПЕКА ТА СЕСІЇ ---
    # Поточний токен, що зберігається в БД для порівняння з Cookies
    session_token: Optional[str] = None
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_ip: Optional[str] = None
    permissions: Dict[str, Dict[str, bool]] = field(default_factory=dict)

    email: Optional[str] = None
    phone: Optional[str] = None
    pending_contact: Optional[str] = None  # Куди хочемо прив'язати (email або phone)
    pending_type: Optional[str] = None  # 'email' або 'signal'
    verification_code: Optional[str] = None  # Код, що чекає перевірки
    verification_expiry: Optional[datetime] = None
    use_2fa: bool = False
    force_password_change: bool = False  # Примусова зміна при першому вході
    signal_last_activity: Optional[datetime] = None

    def has_permission(self, module: str, action: str) -> bool:
        module_perms = self.permissions.get(module, {})
        return module_perms.get(action, False)

    @property
    def is_locked(self) -> bool:
        """Зручна перевірка: чи заблокований юзер прямо зараз"""
        if self.lockout_until and self.lockout_until > datetime.now():
            return True
        return False