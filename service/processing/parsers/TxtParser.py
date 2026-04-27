from .BaseFileParser import BaseFileParser
import os
import regex as re

class TxtParser(BaseFileParser):
    def get_full_text(self) -> str:
        if not os.path.exists(self.file_path):
            self.logger.error(f"❌ Файл не знайдено: {self.file_path}")
            return ""

        # Спробуємо спочатку стандартне кодування UTF-8
        text = self._try_read('utf-8')

        # Якщо UTF-8 не прочитався або повернув сміття, пробуємо Windows-1251
        if not text or self._is_garbage(text):
            self.logger.warning(f"⚠️ UTF-8 не впорався з {os.path.basename(self.file_path)}, пробуємо cp1251...")
            text = self._try_read('cp1251')

        return text

    def _try_read(self, encoding: str) -> str:
        try:
            with open(self.file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            # Це кодування не підходить
            return ""
        except Exception as e:
            self.logger.error(f"❌ Помилка читання TXT файлу ({encoding}): {e}")
            return ""

    def _is_garbage(self, text: str) -> bool:
        # Якщо в тексті немає жодної української чи кириличної літери, а символів багато — це збите кодування
        cyrillic_check = re.search(r'[а-яіїєґА-ЯІЇЄҐ]', text)
        return cyrillic_check is None and len(text) > 50