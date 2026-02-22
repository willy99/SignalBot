from nicegui import ui, app
from gui.controllers.person_controller import PersonController
from gui.controllers.report_controller import ReportController
from gui.controllers.support_controller import SupportController

from gui.views.person import search_view, erdr_search_view
from gui.views.home_view import render_home_page
from gui.views.documentation import support_doc_view, notif_doc_view
from gui.views.report import report_view
from gui.views.report.logs_view import render_logs_page
from pathlib import Path
from processing.processors.DocTemplator import DocTemplator
from config import LOGGER_FILE_NAME
from gui.services.inbox_monitor import InboxMonitor
import os

def init_nicegui(workflow_obj):
    current_dir = Path(__file__).parent.absolute()
    static_dir = current_dir / 'static'
    templates_form = current_dir / '../resources/templates'
    app.add_static_files('/static', str(static_dir))
    app.add_static_files('/templates', str(templates_form))
    support_templates_dir = current_dir / '../resources/templates/support-form'
    doc_processor = DocTemplator(support_templates_dir)

    support_ctrl = SupportController(doc_processor, workflow_obj)
    person_ctrl = PersonController(workflow_obj)
    report_ctrl = ReportController(workflow_obj)

    inbox_monitor_service = InboxMonitor(workflow_obj)


    @ui.page('/')
    def index():
        render_home_page()

    # Визначаємо сторінки
    @ui.page('/search')
    def search():
        search_view.search_page(person_ctrl)

    @ui.page('/erdr')
    def erdr():
        erdr_search_view.search_page(person_ctrl)

    @ui.page('/report')
    def reports():
        report_view.search_page(report_ctrl, person_ctrl)

    @ui.page('/support_doc')
    def support_doc():
        support_doc_view.render_document_page(support_ctrl)

    @ui.page('/notif_doc')
    def notif_doc():
        notif_doc_view.notif_view_doc()

    @ui.page('/settings')
    def settings_doc():
        notif_doc_view.notif_view_doc()  # Поки що показуємо заглушку "В розробці"

    @ui.page('/logs')
    def system_logs():
        log_dir = "logs"
        log_file = os.path.join(log_dir, LOGGER_FILE_NAME)
        render_logs_page(log_file)

    # native=False дозволяє працювати як веб-сервер
    # reload=False обов'язково, бо ми в потоці
    ui.run(port=8080, title='A0224 Корябалка', reload=False, show=False)


