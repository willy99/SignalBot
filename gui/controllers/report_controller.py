from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter

class ReportController:
    def __init__(self, worklow, auth_manager):
        self.reporter = worklow.reporter
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def do_subunit_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_subunit_desertion_stats(search_filter)
        return results

    def get_yearly_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_yearly_desertion_stats()
        return results

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
