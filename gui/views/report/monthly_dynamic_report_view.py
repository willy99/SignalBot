import plotly.graph_objects as go
from nicegui import ui

def render_monthly_dynamics(report_ctrl):
    data = report_ctrl.get_monthly_dynamics_data()

    fig = go.Figure()

    # Стовпчики для СЗЧ
    fig.add_trace(go.Bar(
        x=data['labels'],
        y=data['awol_counts'],
        name='Кількість СЗЧ',
        marker_color='rgba(239, 68, 68, 0.7)',  # Червоний (Tailwind red-500)
    ))

    # Лінія для Повернень
    fig.add_trace(go.Scatter(
        x=data['labels'],
        y=data['ret_counts'],
        name='Повернулися',
        mode='lines+markers',
        line=dict(color='rgba(34, 197, 94, 1)', width=3),  # Зелений (Tailwind green-500)
        marker=dict(size=8)
    ))

    fig.update_layout(
        title='Динаміка СЗЧ та Повернень (Помісячно)',
        xaxis_title='Місяць',
        yaxis_title='Кількість осіб',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified',
        barmode='group'
    )

    ui.plotly(fig).classes('w-full h-96')