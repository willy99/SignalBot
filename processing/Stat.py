import os

class Stat:

    def __init__(self):
        self.messagesProcessed = 0
        self.attachmentWordProcessed = 0
        self.attachmentPDFProcessed = 0
        self.errors = 0
        self.doc_names = []
        self.error_doc_names = {}

    def add_error(self, doc_path, error):
        doc_errors = self.error_doc_names.get(doc_path)
        if not doc_errors:
            doc_errors = []
        doc_errors.append(error)
        self.error_doc_names[doc_path] = doc_errors

    def get_report(self):
        return (
            "📊 * Статистика роботи бота *\n"
            "━━━━━━━━━━━━━━━\n"
            f"📩 Оброблено повідомлень: {self.messagesProcessed}\n"
            f"📝 Документів Word (DOCX): {self.attachmentWordProcessed}\n"
            f"📄 Файлів PDF: {self.attachmentPDFProcessed}\n"
            f"❌ Помилок під час обробки: {self.errors}\n"
            "━━━━━━━━━━━━━━━\n"
        )

    def get_full_report(self):
        # 1. Формуємо блок оброблених документів
        # Витягуємо тільки імена файлів за допомогою os.path.basename
        processed_files = "\n".join([f"✅ {os.path.basename(f)}" for f in self.doc_names])

        if not processed_files:
            processed_files = "Список порожній"

        # 2. Формуємо блок помилок
        errors_list = []
        for file_path, errors in self.error_doc_names.items():
            file_name = os.path.basename(file_path)
            errors_list.append(f"❌ {file_name}:")
            # Якщо помилки — це список, додаємо кожну з відступом
            if isinstance(errors, list):
                for err in errors:
                    errors_list.append(f"   • {err}")
            else:
                errors_list.append(f"   • {errors}")

        errors_block = "\n".join(errors_list) if errors_list else "✔️"

        return (
            "📊 *ЗВІТ ОБРОБКИ ДОКУМЕНТІВ*\n"
            "━━━━━━━━━━━━━━━\n"
            "* 📝 Оброблені файли:*\n"
            f"{processed_files}\n"
            "━━━━━━━━━━━━━━━\n"
            "*Попередження в час обробки:*\n"
            f"{errors_block}\n"
            "━━━━━━━━━━━━━━━"
        )