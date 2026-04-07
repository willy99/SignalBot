import plotly.graph_objects as go
from nicegui import ui

from gui.controllers.report_controller import ReportController


def render_heatmap_page(report_ctrl: ReportController):
    ui.label('Теплова карта залишень частин').classes('text-h4 mb-4')

    with ui.card().classes('w-full p-4'):
        # Отримуємо дані
        matrix = report_ctrl.get_awol_heatmap_data()

        # Назви для осей
        weekdays = ['Пн', 'Вв', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
        days = [str(i) for i in range(1, 32)]

        fig = go.Figure(data=go.Heatmap(
            z=[row[1:] for row in matrix],
            x=[str(i) for i in range(1, 32)],
            y=weekdays,
            colorscale='YlOrRd',  # Жовтий -> Помаранчевий -> Червоний
            hoverongaps=False,
            hovertemplate='День: %{x}<br>День тижня: %{y}<br>Випадків: %{z}<extra></extra>'
        ))

        fig.update_layout(
            title='Активність СЗЧ за числами місяця та днями тижня',
            xaxis_title='Число місяця',
            yaxis_title='День тижня',
            height=400
        )

        ui.plotly(fig).classes('w-full')

    with ui.expansion('Як користуватися цією аналітикою?', icon='help_outline').classes('w-full bg-blue-50'):
        ui.markdown('''
            📊 Інструкція: Як читати Теплову карту СЗЧ\n
            Цей графік дозволяє побачити приховані закономірності поведінки особового складу, поєднуючи календарні дати та дні тижня.\n\n
            
            1. Що зображено на осях?\n
            Горизонтальна вісь (X): Числа місяця (від 1 до 31). \nЦе допомагає виявити прив'язку до фінансових подій (виплати) або сталих дат (кінець/початок місяця).\n
            Вертикальна вісь (Y): Дні тижня (від Пн до Нд). \nЦе допомагає виявити прив'язку до службового розпорядку (вихідні, шикування, перевірки).\n\n
            
            2. Колірна індикація (Температура)\n
            Колір кожної клітинки залежить від кількості зафіксованих СЗЧ у цей конкретний день:\n
            ⬜ Світло-жовтий: Спокійний день (0 або мінімум залишень).\n
            🟧 Помаранчевий: Середня інтенсивність.\n
            🟥 Темно-червоний: "Гаряча точка" (аномально велика кількість випадків).\n
        ''')