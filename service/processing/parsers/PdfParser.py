from utils.utils import is_win
from .BaseFileParser import BaseFileParser
import fitz  # PyMuPDF
import pytesseract

if is_win():
    try:
        import pythoncom
    except ImportError:
        pythoncom = None
else:
    pythoncom = None

if is_win() and pythoncom:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image


class PdfParser(BaseFileParser):
    def get_full_text(self):
        doc = fitz.open(self.file_path)
        full_text = []

        for page in doc:
            # 1. Спробуємо дістати звичайний текст
            page_text = page.get_text().strip()

            # 2. Якщо тексту немає (або це просто цифра сторінки), вмикаємо OCR
            if len(page_text) < 50:
                self.logger.info(f"Сторінка {page.number} схожа на скан. Запускаємо OCR...")
                page_text = self._ocr_page(page)

            full_text.append(page_text)

        doc.close()
        return "\n".join(full_text)

    def _ocr_page(self, page):
        try:
            # Збільшуємо роздільну здатність картинки для кращого розпізнавання (zoom 2x або 3x)
            zoom = 2  # 2 = ~144 DPI, 3 = ~216 DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Конвертуємо pixmap з fitz у формат картинки Pillow (PIL)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Запускаємо Tesseract (ukr - українська мова, можна додати eng: lang='ukr+eng')
            # config='--psm 6' каже Tesseract'у, що це єдиний блок тексту (допомагає з форматуванням)
            text = pytesseract.image_to_string(img, lang='ukr', config='--psm 6')

            return text.strip()
        except Exception as e:
            self.logger.error(f"Помилка OCR на сторінці: {e}")
            return ""