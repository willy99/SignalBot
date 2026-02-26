from nicegui import ui
from gui.services.request_context import RequestContext

def render_drafts_list_page(controller, ctx: RequestContext):
    ui.label('Архів чернеток документів').classes('w-full text-center text-3xl font-bold mb-8')

    def delete_draft(draft_id, card_element):
        controller.delete_draft(ctx, draft_id)
        card_element.delete()
        ui.notify(f'Чернетку №{draft_id} видалено')

    # Отримуємо дані
    drafts = controller.get_all_drafts(ctx)

    with ui.grid(columns='12').classes('w-full gap-4'):
        if not drafts:
            ui.label('Чернеток не знайдено').classes('col-span-12 text-center text-gray-400 mt-10')

        for d in drafts:
            # Створюємо картку для кожної чернетки
            with ui.card().classes('col-span-12 md:col-span-4 lg:col-span-3 hover:shadow-lg transition-shadow') as card:
                with ui.row().classes('w-full justify-between items-start'):
                    ui.badge(f"ID: {d['id']}", color='grey')
                    ui.label(d['created_date']).classes('text-xs text-gray-500')

                ui.label(f"Номер: {d['support_number'] or '—'}").classes('font-bold text-lg')
                ui.label(f"Місто: {d['city']}").classes('text-sm')
                ui.label(f"Кількість осіб у пакеті: {len(d['payload'])}").classes('text-sm text-blue-600')

                with ui.row().classes('w-full mt-4 gap-2'):
                    # Кнопка переходу на форму редагування (передаємо ID в URL)
                    ui.button('Редагувати',
                              icon='edit',
                              on_click=lambda d_id=d['id']: ui.navigate.to(f'/doc_support/edit/{d_id}')
                              ).props('flat color="primary"').classes('flex-grow')

                    ui.button(icon='delete',
                              on_click=lambda d_id=d['id'], c=card: delete_draft(d_id, c)
                              ).props('flat color="red"')