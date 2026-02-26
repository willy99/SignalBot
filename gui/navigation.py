from nicegui import ui, app
from gui.controllers.person_controller import PersonController
from gui.controllers.report_controller import ReportController
from gui.controllers.support_controller import SupportController

from gui.views.person import search_view, erdr_search_view
from gui.views.home_view import render_home_page
from gui.views.documentation import support_doc_view, notif_doc_view, support_doc_list_view
from gui.views.report import subunits_report_view
from gui.views.report import dups_report_view
from gui.views.report.logs_view import render_logs_page

from gui.views.admin.admin_permissions_view import render_permissions_page
from gui.views.admin.admin_users_view import render_users_page

from gui.auth_routes import create_login_page, require_access
from gui.views.documentation.file_search_view import render_file_search_page
from pathlib import Path
from service.processing.processors.DocTemplator import DocTemplator
from config import LOGGER_FILE_NAME
from gui.services.inbox_monitor import InboxMonitor
from gui.services.auth_manager import AuthManager
import os
import config
from gui.components import menu
from service.storage.FileCacher import FileCacheManager
from service.storage.SMBFileClient import SMBFileClient

def init_nicegui(workflow_obj):
    current_dir = Path(__file__).parent.absolute()
    static_dir = current_dir / 'static'
    templates_form = current_dir / '../resources/templates'
    app.add_static_files('/static', str(static_dir))
    app.add_static_files('/templates', str(templates_form))
    support_templates_dir = current_dir / '../resources/templates/support-form'
    doc_processor = DocTemplator(support_templates_dir)
    auth_manager = AuthManager(workflow_obj.db)
    create_login_page(auth_manager, workflow_obj.log_manager)

    support_ctrl = SupportController(doc_processor, workflow_obj, auth_manager)
    person_ctrl = PersonController(workflow_obj, auth_manager)
    report_ctrl = ReportController(workflow_obj, auth_manager)

    inbox_monitor_service = InboxMonitor(workflow_obj)
    smb_client = SMBFileClient(config.DOCUMENT_STORAGE_PATH, workflow_obj.log_manager)
    file_manager = FileCacheManager(config.CACHE_FILE_PATH, log_manager=workflow_obj.log_manager)

    create_login_page(auth_manager, workflow_obj.log_manager)

    @ui.page('/')
    @require_access(auth_manager, 'search', 'read')
    def index():
        render_home_page(auth_manager)

    # Визначаємо сторінки
    @ui.page('/search')
    @require_access(auth_manager, 'search', 'read')  # Наприклад, головна - це пошук
    def search():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        search_view.search_page(person_ctrl, ctx)

    @ui.page('/erdr')
    @require_access(auth_manager, 'person', 'read')
    def erdr():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        erdr_search_view.search_page(person_ctrl, ctx)

    @ui.page('/report_units')
    @require_access(auth_manager, 'report_units', 'read')
    def report_units():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        subunits_report_view.search_page(report_ctrl, person_ctrl, ctx)

    @ui.page('/report_name_dups')
    @require_access(auth_manager, 'report_general', 'read')
    def report_units():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        dups_report_view.render_duplicates_report_page(report_ctrl, ctx)

    @ui.page('/doc_support')
    @require_access(auth_manager, 'doc_support', 'read')
    def support_doc():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        support_doc_list_view.render_drafts_list_page(support_ctrl, ctx)

    @ui.page('/doc_support/edit/{draft_id}')
    @require_access(auth_manager, 'doc_support', 'read')
    def support_doc():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        support_doc_view.render_document_page(support_ctrl, ctx)

    @ui.page('/doc_notif')
    @require_access(auth_manager, 'doc_notif', 'read')
    def notif_doc():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        notif_doc_view.notif_view_doc()

    @ui.page('/settings')
    @require_access(auth_manager, 'admin_panel', 'write')
    def settings_doc():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        notif_doc_view.notif_view_doc()  # Поки що показуємо заглушку "В розробці"

    @ui.page('/logs')
    @require_access(auth_manager, 'admin_panel', 'read')
    def system_logs():
        menu(auth_manager)
        log_dir = "logs"
        log_file = os.path.join(log_dir, LOGGER_FILE_NAME)
        render_logs_page(log_file)


    # Доступ ТІЛЬКИ для адмінів!

    @ui.page('/admin/permissions')
    @require_access(auth_manager, 'admin_panel', 'write')
    def admin_permissions_route():
        menu(auth_manager)
        render_permissions_page(auth_manager)

    @ui.page('/admin/users')
    @require_access(auth_manager, 'admin_panel', 'write')  # Доступ ТІЛЬКИ для адмінів!
    def admin_users_route():
        menu(auth_manager)
        render_users_page(auth_manager)


    @ui.page('/doc_files')
    @require_access(auth_manager, 'search', 'read')
    def file_search_route():
        ctx = auth_manager.get_current_context()
        menu(auth_manager)
        render_file_search_page(file_manager)


    # native=False дозволяє працювати як веб-сервер
    # reload=False обов'язково, бо ми в потоці
    ui.run(port=8080, title='A0224 Втікачі', reload=False, show=False, storage_secret=config.UI_SECRET_KEY)

