from abc import ABC, abstractmethod
import re
from storage.LoggerManager import LoggerManager

class BaseFileParser(ABC):
    def __init__(self, file_path, log_manager: LoggerManager):
        self.file_path = file_path
        self.logger = log_manager.get_logger()

    @abstractmethod
    def get_full_text(self):
        pass

    def extract_text_between(self, start_pattern, end_pattern, start_from_next_line=False, use_last_match=False):
        # Отримуємо текст залежно від типу парсера (Docx чи DocOld)
        raw_text = self.get_full_text()

        # Нормалізація: прибираємо зайві пробіли всередині рядків, але лишаємо \n
        full_text = "\n".join([" ".join(line.split()) for line in raw_text.splitlines()])

        # Далі ваша логіка без змін
        start_matches = list(re.finditer(start_pattern, full_text, re.IGNORECASE | re.DOTALL))
        if not start_matches:
            return None

        current_match = start_matches[-1] if use_last_match else start_matches[0]
        content_start = current_match.end()

        if start_from_next_line:
            end_of_current_line = full_text.find('\n', content_start)
            if end_of_current_line != -1:
                content_start = end_of_current_line + 1
                while content_start < len(full_text):
                    char = full_text[content_start]
                    if char.isspace():
                        content_start += 1
                    elif char == '(':
                        closing = full_text.find(')', content_start)
                        content_start = closing + 1 if closing != -1 else content_start + 1
                    else:
                        break

        end_match = re.search(end_pattern, full_text[content_start:], re.IGNORECASE | re.DOTALL)

        if end_match:
            end_pos = content_start + end_match.start()
            result = full_text[content_start:end_pos]
        else:
            result = full_text[content_start:]

        return result.strip() if result.strip() else None

    def find_paragraph(self, search_text, get_next=False):
        """
        Універсальний пошук параграфа. Працює для будь-якого формату,
        який реалізує get_full_text().
        """
        full_text = self.get_full_text()
        # Розбиваємо на рядки та чистимо порожні
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        for i, line_text in enumerate(lines):
            # Нормалізуємо для пошуку
            line_clean = self._prepare_text(line_text).lower()

            if search_text.lower() in line_clean:
                if get_next and i + 1 < len(lines):
                    return self._prepare_text(lines[i + 1])
                else:
                    return self._prepare_text(lines[i])

        return None

    # Спільний метод для всіх, бо логіка очищення однакова
    def _prepare_text(self, text):
        return " ".join(text.split())
