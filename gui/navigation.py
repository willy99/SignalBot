from nicegui import ui, app
from gui.controllers.person_controller import PersonController
from gui.controllers.report_controller import ReportController

from gui.views.person import search_view, erdr_search_view
from gui.views.report import report_view
from pathlib import Path


def init_nicegui(workflow_obj):
    current_dir = Path(__file__).parent.absolute()
    static_dir = current_dir / 'static'
    app.add_static_files('/static', str(static_dir))

    # Створюємо контролер, передаючи йому робочий workflow
    person_ctrl = PersonController(workflow_obj)
    report_ctrl = ReportController(workflow_obj)


    # Визначаємо сторінки
    @ui.page('/')
    def index():
        search_view.search_page(person_ctrl)

    @ui.page('/erdr')
    def index():
        erdr_search_view.search_page(person_ctrl)

    @ui.page('/report')
    def reports():
        report_view.search_page(report_ctrl, person_ctrl)

    # native=False дозволяє працювати як веб-сервер
    # reload=False обов'язково, бо ми в потоці
    ui.run(port=8080, title='A0224 Корябалка', reload=False, show=False)


