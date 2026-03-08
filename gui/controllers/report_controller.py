from typing import List

from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from datetime import date
from gui.services.auth_manager import AuthManager
from service.processing.MyWorkFlow import MyWorkFlow


class ReportController:
    def __init__(self, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.reporter = worklow.reporter
        self.auth_manager = auth_manager
        self.log_manager = worklow.log_manager
        self.logger = worklow.log_manager.get_logger()

    def do_subunit_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_subunit_desertion_stats(search_filter)
        return results

    def get_yearly_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_yearly_desertion_stats()
        return results

    def get_daily_added_records_report(self, ctx: RequestContext, target_date: date = None):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо щоденний репорт: ' + str(target_date))
        results = self.reporter.get_daily_report(target_date)
        return results

    def get_daily_added_files_report(self, ctx: RequestContext, target_date: date = None, exclude_names: List[str] = None):
        return self.reporter.get_daily_returns_report(target_date, exclude_names)

    def get_dupp_names_report(self, ctx: RequestContext):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_dupp_names_report()
        return results

    def get_waiting_for_erdr_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт - справи очікуючі ЄРДР: ')
        results = self.reporter.get_waiting_for_erdr_report(search_filter)
        return results

    def is_admin(self):
        return self.auth_manager.has_access('admin_panel', 'read')
