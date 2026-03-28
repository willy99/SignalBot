from typing import List

import config
from dics.security_config import PERM_READ
from gui.auth_routes import refresh_session_method
from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from gui.services.auth_manager import AuthManager
from service.processing.DocumentProcessingService import DocumentProcessingService
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from service.processing.processors.ExcelReport import ExcelReporter
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
import io
from datetime import date

class ReportController:
    def __init__(self, doc_templator: DocTemplator, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.doc_templator:DocTemplator = doc_templator
        self.reporter:ExcelReporter = worklow.reporter
        self.auth_manager:AuthManager = auth_manager
        self.log_manager:LoggerManager = worklow.log_manager
        self.logger = worklow.log_manager.get_logger()

    @refresh_session_method
    def do_subunit_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_subunit_desertion_stats(search_filter)
        return results

    @refresh_session_method
    def get_general_state_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_general_state_report(search_filter)
        return results

    @refresh_session_method
    def get_yearly_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_yearly_desertion_stats()
        return results

    @refresh_session_method
    def get_daily_added_records_report(self, ctx: RequestContext, target_date: date = None):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо щоденний репорт: ' + str(target_date))
        results = self.reporter.get_daily_report(target_date)
        return results

    @refresh_session_method
    def get_daily_added_files_report(self, ctx: RequestContext, target_date: date = None, exclude_names: List[str] = None, pre_fetched_archive=None):
        return self.reporter.get_daily_returns_report(target_date, exclude_names, pre_fetched_archive)

    @refresh_session_method
    def get_daily_archive_files(self, target_date, known_names: list):
        dservice = DocumentProcessingService(self.log_manager)
        return dservice.get_daily_archive_files(target_date, known_names)

    @refresh_session_method
    def get_dupp_names_report(self, ctx: RequestContext):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_dupp_names_report()
        return results

    @refresh_session_method
    def get_error_birthday_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_inn_birthday_mismatch_report(search_filter)
        return results

    @refresh_session_method
    def get_waiting_for_erdr_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт - справи очікуючі ЄРДР: ')
        results = self.reporter.get_waiting_for_erdr_report(search_filter)
        return results

    @refresh_session_method
    def get_brief_report(self, ctx: RequestContext):
        return self.reporter.get_brief_summary()

    def is_admin(self):
        return self.auth_manager.has_access('admin_panel', PERM_READ)

    def generate_daily_report_word(self, target_date: str, raw_documents: list) -> tuple[bytes, str]:
        file_bytes, file_name = self.doc_templator.make_daily_report(target_date, raw_documents)

        try:
            client = StorageFactory.create_client(config.REPORT_DAILY_DESERTION, self.log_manager)
            with client:
                destination_path = f"{config.REPORT_DAILY_DESERTION}{client.separator}{file_name}"
                buffer = io.BytesIO(file_bytes)
                client.save_file_from_buffer(destination_path, buffer)
                self.log_manager.get_logger().info(f"✅ Звіт СЗЧ успішно збережено в архів: {destination_path}")
        except Exception as e:
            self.log_manager.get_logger().error(f"❌ Не вдалося зберегти звіт в архівну папку: {e}")
        return file_bytes, file_name
