class SupportController:
    def __init__(self, processor, worklow):
        self.processor = processor
        self.buffer = []
        self.workflow = worklow

    def add_to_buffer(self, raw_data: dict):
        self.buffer.append(raw_data)

    def remove_from_buffer(self, index: int):
        if 0 <= index < len(self.buffer):
            self.buffer.pop(index)

    def get_buffer(self) -> list:
        return self.buffer

    def clear_buffer(self):
        self.buffer.clear()

    def generate_support_document(self, city: str, supp_number: str) -> tuple[bytes, str]:
        if not self.buffer:
            raise ValueError("Буфер порожній. Додайте хоча б один запис.")
        if not supp_number:
            raise ValueError("Будь ласка, введіть загальний номер супроводу.")

        # Викликаємо процесор для генерації
        return self.processor.generate_support_batch(city, supp_number, self.buffer)