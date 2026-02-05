from .BaseFileParser import BaseFileParser
import fitz

class PdfParser(BaseFileParser):

    def get_full_text(self):
        # Відкриваємо документ
        doc = fitz.open(self.file_path)
        full_text = []

        # Перебираємо кожну сторінку та витягуємо текст
        for page in doc:
            full_text.append(page.get_text())

        doc.close()  # Важливо закрити файл після читання

        # Об'єднуємо текст усіх сторінок в один рядок
        return "\n".join(full_text)