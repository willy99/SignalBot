from dataclasses import dataclass
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class RequestContext:
    user_login: str
    user_name: str
    user_id: int
    user_role: str
    ip_address: str = "unknown"
    last_activity: float = field(default_factory=time.time)
    session_token: str = field(default_factory=str)

    @property
    def last_activity_str(self) -> str:
        return datetime.fromtimestamp(self.last_activity).strftime('%H:%M:%S')

    def update_activity(self):
        """Зручний метод для оновлення часу в потоці"""
        self.last_activity = time.time()
        d = datetime.fromtimestamp(self.last_activity).strftime('%H:%M:%S')
        print('>>> updating session to ' + str(d))