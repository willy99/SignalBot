from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class User:
    id: int
    username: str
    role: str
    full_name: str
    is_active: bool = True
    permissions: Dict[str, Dict[str, bool]] = field(default_factory=dict)

    def has_permission(self, module: str, action: str) -> bool:
        module_perms = self.permissions.get(module, {})
        return module_perms.get(action, False)