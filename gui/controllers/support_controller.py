from gui.services.request_context import RequestContext

class SupportController:
    def __init__(self, processor, worklow, auth_manager):
        self.processor = processor
        self.workflow = worklow
        self.auth_manager = auth_manager
        self.logger = worklow.log_manager.get_logger()

    def generate_support_document(self, ctx: RequestContext, city: str, supp_number: str, buffer_data: list) -> tuple[bytes, str]:
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо супровід: ' + str(city) + ', number:' + supp_number + ':' + str(buffer_data))

        if not buffer_data:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not supp_number:
            raise ValueError("Будь ласка, введіть загальний номер супроводу.")

        # Викликаємо процесор для генерації
        return self.processor.generate_support_batch(city, supp_number, buffer_data)

    def search_persons(self, ctx, query: str):
        return [
            {'name': 'Петренко Петро Петрович', 'id_number': '1234567890'},
            {'name': 'Петренко Іван Іванович', 'id_number': '0987654321'},
        ]