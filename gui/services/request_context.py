from dataclasses import dataclass

@dataclass
class RequestContext:
    user_name: str
    user_role: str
    ip_address: str = "unknown"