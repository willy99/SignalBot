from dataclasses import dataclass

@dataclass
class RequestContext:
    user_login: str
    user_name: str
    user_id: int
    user_role: str
    ip_address: str = "unknown"