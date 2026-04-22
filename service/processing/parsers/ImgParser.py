from utils.utils import is_win
from .BaseFileParser import BaseFileParser
import pytesseract
from PIL import Image

# Налаштування шляху для Windows (якщо цей код буде в окремому файлі)
if is_win():
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImgParser(BaseFileParser):
    def get_full_text(self):
        """
        Відкриває графічний файл (JPG, PNG, TIFF тощо) та витягує з нього текст за допомогою OCR.
        """
        try:
            self.logger.info(f"Запускаємо OCR для зображення: {self.file_path}")

            # Відкриваємо зображення за допомогою Pillow
            # Використовуємо with, щоб файл коректно закрився після зчитування
            with Image.open(self.file_path) as img:

                # Опціонально: тут можна додати логіку попередньої обробки зображення
                # (контраст, чорно-біле), якщо якість фотографій з ЄРДР буде поганою.

                # Запускаємо Tesseract
                # lang='ukr' - українська мова
                # config='--psm 6' - припускаємо, що це єдиний однорідний блок тексту (допомагає з форматуванням)
                text = pytesseract.image_to_string(img, lang='ukr', config='--psm 6')

                return text.strip()

        except Exception as e:
            self.logger.error(f"Помилка OCR при обробці зображення {self.file_path}: {e}")
            return ""