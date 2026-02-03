class Stat:

    def __init__(self):
        self.messagesProcessed = 0
        self.attachmentWordProcessed = 0
        self.attachmentPDFProcessed = 0
        self.errors = 0

    def get_report(self):
        return (
            "📊 *Статистика роботи бота*\n"
            "━━━━━━━━━━━━━━━\n"
            f"📩 Оброблено повідомлень: {self.messagesProcessed}\n"
            f"📝 Документів Word (DOCX): {self.attachmentWordProcessed}\n"
            f"📄 Файлів PDF: {self.attachmentPDFProcessed}\n"
            f"❌ Помилок під час обробки: {self.errors}\n"
            "━━━━━━━━━━━━━━━\n"
        )