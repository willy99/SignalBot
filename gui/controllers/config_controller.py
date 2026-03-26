from typing import List
from domain.sys_config import SysConfig
from gui.auth_routes import refresh_session, refresh_session_method
from gui.services.auth_manager import AuthManager
from service.config.ConfigService import ConfigService
from gui.services.request_context import RequestContext
from service.processing.MyWorkFlow import MyWorkFlow
from service.storage.LoggerManager import LoggerManager

class ConfigController:
    def __init__(self, workflow: MyWorkFlow, auth_manager: AuthManager):
        # self.config_service = config_service
        self.log_manager = workflow.log_manager
        self.logger = self.log_manager.get_logger()
        self.auth_manager = auth_manager
        self.cfg_service = ConfigService()

    def get_all_configs(self, ctx: RequestContext) -> List[SysConfig]:
        """Отримує всі налаштування з бази"""
        # 💡 Тут можна додати перевірку: if not ctx.is_admin: raise Exception(...)
        self.logger.debug(f"UI:{ctx.user_name}: Запит системних налаштувань.")

        return self.cfg_service.get_all()

    def update_config_value(self, ctx: RequestContext, key_name: str, new_value: str) -> bool:
        """Оновлює значення та логує цю дію"""
        self.logger.info(f"⚠️ UI:{ctx.user_name}: Змінює налаштування [{key_name}] на [{new_value}]")
        return self.cfg_service.update_value(key_name, new_value)

    def apply_configs_to_runtime(self, ctx: RequestContext):
        """Застосовує зміни в пам'ять"""
        self.logger.info(f"🔄 UI:{ctx.user_name}: Застосовує нові налаштування системи в config.py")
        self.cfg_service.apply_to_runtime()