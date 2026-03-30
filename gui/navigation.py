from nicegui import ui, app

from dics.security_config import PERM_READ, PERM_EDIT, MODULE_SEARCH, MODULE_ADMIN, MODULE_REPORT_UNITS, MODULE_REPORT_GENERAL, MODULE_DOC_DBR, MODULE_DOC_SUPPORT, \
    MODULE_DOC_NOTIF, MODULE_TASK
from gui.components import AppMenu
from gui.controllers.person_controller import PersonController
from gui.controllers.report_controller import ReportController
from gui.controllers.support_controller import SupportController
from gui.controllers.dbr_controller import DbrController
from gui.controllers.notif_controller import NotifController
from gui.controllers.task_controller import TaskController
from gui.controllers.inbox_controller import InboxController
from gui.controllers.config_controller import ConfigController
from gui.controllers.user_controller import UserController

from gui.views.person import search_view
from gui.views.person import batch_search_view
from gui.views.home_view import render_home_page
from gui.views.documentation import support_doc_standart_view, support_doc_detailed_view, notif_doc_list_view, notif_doc_edit_view, support_doc_list_view, dbr_doc_list_view, dbr_doc_edit_view
from gui.views.report import subunits_report_view
from gui.views.report import yearly_report_view
from gui.views.report import dups_report_view
from gui.views.report import error_birthday_report_view
from gui.views.report import waiting_for_erdr_report_view
from gui.views.report.logs_view import render_logs_page
from gui.views.report import daily_report_view
from gui.views.report import general_state_report
from gui.views.inbox import inbox_triage_view
from gui.views.task import task_list_view, task_edit_view
from gui.views.calendar import calendar_view
from gui.views.admin.admin_permissions_view import render_permissions_page
from gui.views.admin.admin_users_view import render_users_page
from gui.views.admin.admin_settings_view import render_settings_page
from gui.views import in_progress_view
from gui.views.admin.admin_index_files import render_indexing_page
from gui.views.admin.user_setting_form import render_user_settings_2fa, render_profile_settings
from gui.auth_routes import create_login_page, require_access
from gui.views.documentation.file_search_view import render_file_search_page
from pathlib import Path
from service.processing.processors.DocTemplator import DocTemplator
from gui.services.auth_manager import AuthManager
import os
import config
from service.storage.FileCacher import FileCacheManager

def init_nicegui(workflow_obj):
    current_dir = Path(__file__).parent.absolute()
    static_dir = current_dir / 'static'
    templates_form = current_dir / '../resources/templates'
    file_manager = FileCacheManager(config.CACHE_FILE_PATH, log_manager=workflow_obj.log_manager)

    app.add_static_files('/static', str(static_dir))
    app.add_static_files('/templates', str(templates_form))
    support_templates_dir = current_dir / '../resources/templates'
    doc_templator = DocTemplator(support_templates_dir)
    auth_manager = AuthManager(workflow_obj)

    support_ctrl = SupportController(doc_templator, workflow_obj, auth_manager)
    person_ctrl = PersonController(workflow_obj, auth_manager)
    report_ctrl = ReportController(doc_templator, workflow_obj, auth_manager)
    task_ctrl = TaskController(workflow_obj, auth_manager)
    dbr_ctrl = DbrController(workflow_obj, auth_manager)
    inbox_ctrl = InboxController(workflow_obj, auth_manager)
    notif_ctrl = NotifController(doc_templator, workflow_obj, auth_manager)
    config_ctrl = ConfigController(workflow_obj, auth_manager)
    user_ctrl = UserController(workflow_obj, auth_manager)

    app_menu = AppMenu(auth_manager, task_ctrl, inbox_ctrl, person_ctrl)

    create_login_page(auth_manager, user_ctrl, workflow_obj.log_manager)

    @ui.page('/')
    @ui.page('/home')
    def index():
        render_home_page(auth_manager)

    # Визначаємо сторінки
    @ui.page('/search')
    @require_access(auth_manager, MODULE_SEARCH, PERM_READ)  # Наприклад, головна - це пошук
    def search():
        app_menu.render(auth_manager)
        search_view.search_page(person_ctrl, auth_manager)

    @ui.page('/batch_search')
    @require_access(auth_manager, MODULE_SEARCH, PERM_READ)  # Наприклад, головна - це пошук
    def batch_search():
        app_menu.render(auth_manager)
        batch_search_view.render_bulk_search_page(person_ctrl, auth_manager)



    @ui.page('/report_units')
    @require_access(auth_manager, MODULE_REPORT_UNITS, PERM_READ)
    def report_units():
        app_menu.render(auth_manager)
        subunits_report_view.search_page(report_ctrl, person_ctrl, auth_manager)

    @ui.page('/report_yearly')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_yearly():
        app_menu.render(auth_manager)
        yearly_report_view.render_yearly_report_page(report_ctrl, auth_manager)

    @ui.page('/report_general_state')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_yearly():
        app_menu.render(auth_manager)
        general_state_report.render_place_report_page(report_ctrl, person_ctrl, auth_manager)

    @ui.page('/report_name_dups')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_name_dups():
        app_menu.render(auth_manager)
        dups_report_view.render_duplicates_report_page(report_ctrl, auth_manager)

    @ui.page('/report_error_birthday')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_error_birthday():
        app_menu.render(auth_manager)
        error_birthday_report_view.render_inn_mismatch_page(report_ctrl, person_ctrl, auth_manager)


    @ui.page('/report_waiting_erdr')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_waiting_for_erdr_report_view():
        app_menu.render(auth_manager)
        waiting_for_erdr_report_view.render_dbr_details_report_page(report_ctrl, person_ctrl, auth_manager)

    @ui.page('/report_daily')
    @require_access(auth_manager, MODULE_REPORT_GENERAL, PERM_READ)
    def report_daily():
        app_menu.render(auth_manager)
        daily_report_view.render_daily_report_page(report_ctrl, task_ctrl, person_ctrl, auth_manager)

    @ui.page('/doc_dbr')
    @require_access(auth_manager, MODULE_DOC_DBR, PERM_READ)
    def doc_dbr_list():
        app_menu.render(auth_manager)
        dbr_doc_list_view.render_dbr_drafts_list_page(dbr_ctrl, auth_manager)

    @ui.page('/doc_dbr/create')
    @ui.page('/doc_dbr/edit/{draft_id}')
    @require_access(auth_manager, MODULE_DOC_DBR, PERM_READ)
    def doc_dbr_edit(draft_id: int = None):
        app_menu.render(auth_manager)
        dbr_doc_edit_view.render_dbr_page(dbr_ctrl, person_ctrl, file_manager, auth_manager, draft_id)


    @ui.page('/doc_support')
    @require_access(auth_manager, MODULE_DOC_SUPPORT, PERM_READ)
    def support_doc_list():
        app_menu.render(auth_manager)
        support_doc_list_view.render_drafts_list_page(support_ctrl, auth_manager)

    @ui.page('/doc_support/d_create')
    @ui.page('/doc_support/d_edit/{draft_id}')
    @require_access(auth_manager, MODULE_DOC_SUPPORT, PERM_READ)
    def support_doc_edit(draft_id: int = None):
        app_menu.render(auth_manager)
        support_doc_detailed_view.render_document_page(support_ctrl, person_ctrl, file_manager, auth_manager, draft_id)

    @ui.page('/doc_support/s_create')
    @ui.page('/doc_support/s_edit/{draft_id}')
    @require_access(auth_manager, MODULE_DOC_SUPPORT, PERM_READ)
    def support_doc_edit(draft_id: int = None):
        app_menu.render(auth_manager)
        support_doc_standart_view.render_support_standard_page(support_ctrl, person_ctrl, file_manager, auth_manager, draft_id)

    @ui.page('/doc_notif')
    @require_access(auth_manager, MODULE_DOC_NOTIF, PERM_READ)
    def notif_doc_list():
        app_menu.render(auth_manager)
        notif_doc_list_view.render_notif_drafts_list_page(notif_ctrl, auth_manager)

    @ui.page('/doc_notif/create')
    @ui.page('/doc_notif/edit/{draft_id}')
    @require_access(auth_manager, MODULE_DOC_NOTIF, PERM_READ)
    def notif_doc_edit(draft_id: int = None):
        app_menu.render(auth_manager)
        notif_doc_edit_view.render_notif_page(notif_ctrl, person_ctrl, auth_manager, draft_id)


    @ui.page('/tasks')
    @require_access(auth_manager, MODULE_TASK, PERM_READ)
    def task_list():
        app_menu.render(auth_manager)
        task_list_view.render_task_list_page(task_ctrl, auth_manager)

    @ui.page('/tasks/today')
    @require_access(auth_manager, MODULE_TASK, PERM_READ)
    def task_list():
        app_menu.render(auth_manager)
        task_list_view.render_tasks_today(task_ctrl, auth_manager)

    @ui.page('/tasks/all')
    @require_access(auth_manager, MODULE_TASK, PERM_READ)
    def task_list():
        app_menu.render(auth_manager)
        task_list_view.render_tasks_all(task_ctrl, auth_manager)


    @ui.page('/tasks/edit/{task_id}')
    @require_access(auth_manager, MODULE_TASK, PERM_EDIT)
    def edit_task_page(task_id: str = 'new'):
        actual_id = None if task_id == 'new' else int(task_id)
        app_menu.render(auth_manager)
        task_edit_view.render_task_edit_page(task_ctrl, auth_manager, actual_id)

    @ui.page('/inbox')
    @require_access(auth_manager, MODULE_TASK, PERM_READ)
    def inbox_page():
        ctx = auth_manager.get_current_context()
        app_menu.render(auth_manager)
        inbox_triage_view.render_inbox_page(inbox_ctrl, task_ctrl, person_ctrl, auth_manager)

    @ui.page('/calendar')
    @require_access(auth_manager, MODULE_TASK, PERM_READ)
    def calendar_general():
        ctx = auth_manager.get_current_context()
        app_menu.render(auth_manager)
        calendar_view.render_calendar_page(task_ctrl, ctx)


    # Доступ ТІЛЬКИ для адмінів!

    @ui.page('/admin/settings')
    @require_access(auth_manager, MODULE_ADMIN, PERM_EDIT)
    def settings_doc():
        app_menu.render(auth_manager)
        render_settings_page(config_ctrl, auth_manager)

    @ui.page('/logs')
    @require_access(auth_manager, MODULE_ADMIN, PERM_READ)
    def system_logs():
        app_menu.render(auth_manager)
        log_dir = "logs"
        log_file = os.path.join(log_dir, config.LOGGER_FILE_NAME)
        render_logs_page(log_file)

    @ui.page('/admin/permissions')
    @require_access(auth_manager, MODULE_ADMIN, PERM_EDIT)
    def admin_permissions_route():
        app_menu.render(auth_manager)
        render_permissions_page(auth_manager)

    @ui.page('/admin/users')
    @require_access(auth_manager, MODULE_ADMIN, PERM_EDIT)  # Доступ ТІЛЬКИ для адмінів!
    def admin_users_route():
        app_menu.render(auth_manager)
        render_users_page(auth_manager)

    @ui.page('/admin/file_index')
    @require_access(auth_manager, MODULE_ADMIN, PERM_EDIT)
    async def admin_file_index():
        app_menu.render(auth_manager)
        await render_indexing_page(file_manager, auth_manager)

    @ui.page('/user_settings_2fa')
    @require_access(auth_manager,MODULE_SEARCH, PERM_READ)
    async def user_settings_2fa():
        app_menu.render(auth_manager)
        render_user_settings_2fa(user_ctrl, auth_manager)

    @ui.page('/user_settings')
    @require_access(auth_manager,MODULE_SEARCH, PERM_READ)
    async def user_settings():
        app_menu.render(auth_manager)
        render_profile_settings(user_ctrl, auth_manager)

    @ui.page('/doc_files')
    @require_access(auth_manager, MODULE_SEARCH, PERM_READ)
    def file_search_route():
        app_menu.render(auth_manager)
        render_file_search_page(file_manager, auth_manager)


    # native=False дозволяє працювати як веб-сервер
    # reload=False обов'язково, бо ми в потоці
    ui.run(port=config.UI_PORT, title='A0224 Втікачі', reload=config.UI_RELOAD, show=False, storage_secret=config.UI_SECRET_KEY)

