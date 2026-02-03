from docx import Document
import textract
import fitz
from pathlib import Path
from utils.utils import clean_text


class DocProcessor:
    def __init__(self, workflow, file_path):
        self.file_path = file_path
        self.workflow = workflow

    def process_doc(self):
        extension = Path(self.file_path).suffix
        print("Пошук тексту..." + extension)

        if extension.lower() == '.doc':
            print(self.find_next_paragraph_doc(self.file_path, 'стислі демографічні дані'))
            self.workflow.stats.attachmentWordProcessed += 1
        elif extension.lower() == '.docx':
            print(self.find_next_paragraph_docx(self.file_path, 'стислі демографічні дані'))
            self.workflow.stats.attachmentWordProcessed += 1
        elif extension.lower() == '.pdf':
            print(self.find_next_paragraph_pdf(self.file_path, '3. Прізвище, ім’я,'))
            self.workflow.stats.attachmentPDFProcessed += 1
        print("...Пошук закінчено")



    def find_next_paragraph_doc(self, file_path, search_text):
        print('>>> doc')
        # textract витягує текст з .doc через antiword
        byte_content = textract.process(file_path)
        text = byte_content.decode('utf-8')

        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        for i, para in enumerate(paragraphs):
            para = clean_text(para).lower()
            if search_text.lower() in para:
                if i + 1 < len(paragraphs):
                    return clean_text(paragraphs[i + 1])
        return "Не знайдено"

    def find_next_paragraph_docx(self, file_path, search_text):
        print('>>> docx')
        doc = Document(file_path)
        for i, para in enumerate(doc.paragraphs):
            if search_text.lower() in clean_text(para.text.lower()):
                # Перевіряємо, чи є наступний абзац
                if i + 1 < len(doc.paragraphs):
                    return clean_text(doc.paragraphs[i+1].text)
                return "Це був останній абзац."
        return "Текст не знайдено."


    def find_next_paragraph_pdf(self, file_path, search_text):
        print('>>> pdf')
        doc = fitz.open(file_path)

        for page in doc:
            # Отримуємо блоки тексту. Кожен блок зазвичай є абзацом.
            blocks = page.get_text("blocks")
            for i, b in enumerate(blocks):
                block_text = b[4]  # 4-й елемент кортежу — це сам текст
                print('>>> block : ' + clean_text(block_text))
                if search_text.lower() in clean_text(block_text.lower()):
                    if i + 1 < len(blocks):
                        return clean_text(blocks[i + 1][4])
                    return "Знайдено в останньому блоці сторінки."

        return "Текст не знайдено."

