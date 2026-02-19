from nicegui import ui
from gui.controllers.person_controller import PersonController

from gui.views.person import search_view


def init_nicegui(workflow_obj):
    """Ця функція запускає сервер NiceGUI"""

    # Створюємо контролер, передаючи йому робочий workflow
    person_ctrl = PersonController(workflow_obj)

    # Визначаємо сторінки
    @ui.page('/')
    def index():
        search_view.search_page(person_ctrl)

    @ui.page('/reports')
    def reports():
        # report_page()
        print('stub')

    # native=False дозволяє працювати як веб-сервер
    # reload=False обов'язково, бо ми в потоці
    ui.run(port=8080, title='A0224 Корябалка', reload=False, show=False)

