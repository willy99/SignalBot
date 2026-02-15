from .BaseFileParser import BaseFileParser
import subprocess
import re

class DocOldParser(BaseFileParser):
    def get_full_text(self):
        # Спробуємо спочатку textutil
        text = self._try_textutil()

        # Якщо textutil повернув сміття (немає кирилиці або забагато дивних символів)
        if not text or self._is_garbage(text):
            self.logger.warning("⚠️ textutil не впорався, пробуємо antiword...")
            text = self._try_antiword()

        return text

    def _try_textutil(self):
        try:
            result = subprocess.run(
                ['textutil', '-convert', 'txt', '-stdout', self.file_path],
                capture_output=True
            )
            return result.stdout.decode('utf-8', errors='replace')
        except:
            return ""

    def _try_antiword(self):
        try:
            # antiword чудово витягує текст зі старих .doc
            result = subprocess.run(
                ['antiword', '-m', 'UTF-8', self.file_path],
                capture_output=True
            )
            return result.stdout.decode('utf-8', errors='replace')
        except Exception as e:
            self.logger.error(f"❌ antiword не встановлено або помилка: {e}")
            return ""

    def _is_garbage(self, text):
        # Якщо в тексті немає жодної української літери, а символів багато — це сміття
        # Або якщо відсоток символів типу Ÿ, È, Ω занадто високий
        cyrillic_check = re.search(r'[а-яіїєґА-ЯІЇЄҐ]', text)
        return cyrillic_check is None and len(text) > 50