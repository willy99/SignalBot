from gui.services.request_context import RequestContext

class ReportController:
    def __init__(self, worklow, auth_manager):
        self.reporter = worklow.reporter
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def do_subunit_desertion_report(self, ctx: RequestContext, year):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(year))
        results = self.reporter.get_subunit_desertion_stats(year)
        return results

    def get_dupp_names_report(self, ctx: RequestContext):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_dupp_names_report()
        return results
