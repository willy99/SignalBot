from nicegui import ui, run

from gui.services.request_context import RequestContext


class AdminColumnConverterView:
    def __init__(self, person_controller, ctx:RequestContext):
        self.person_controller = person_controller
        self.ctx = ctx

    def show(self):
        """Просто малюємо інтерфейс"""
        with ui.column().classes('w-full p-8 gap-4'):
            ui.label('Конвертація колонок Excel').classes('text-2xl font-bold')

            with ui.card().classes('p-6'):
                ui.label('Ця функція виправляє типи даних (дати, РНОКПП) у вашій базі Excel.')

                # Кнопка запуску
                btn = ui.button('Запустити конвертацію', icon='auto_fix_high')

                # Обробник події
                btn.on_click(lambda: self.run_conversion(btn))

    async def run_conversion(self, button):
        button.disable()
        ui.notify('Процес запущено...', type='info')
        try:
            # Викликаємо важку задачу в окремому потоці (Executor)
            # Використовуємо auth_manager.execute, якщо він у тебе прокидає контекст
            # Або просто run.io_bound
            await run.io_bound(self.person_controller.convert_columns, self.ctx)
            ui.notify('Готово!', type='positive')
        except Exception as e:
            ui.notify(f'Помилка: {e}', type='negative')
        finally:
            button.enable()