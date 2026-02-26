from .BaseFileParser import BaseFileParser
from docx import Document

class DocxParser(BaseFileParser):

    def get_full_text(self):
        doc = Document(self.file_path)
        # З'єднуємо параграфи через \n, щоб зберегти структуру для Regex
        return "\n".join([p.text for p in doc.paragraphs])