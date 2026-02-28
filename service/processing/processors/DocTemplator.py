import io
from pathlib import Path
from docxtpl import DocxTemplate
from datetime import datetime

class DocTemplator:
    def __init__(self, templates_dir: Path):

        self.templates_dir = Path(templates_dir)
        self.templates = {
            'Миколаїв': self.templates_dir / 'Мико.docx',
            'Дніпро': self.templates_dir / 'Дніпро.docx',
            'Донецьк': self.templates_dir / 'Донецьк.docx'
        }

    @staticmethod
    def format_name(full_name: str) -> str:
        words = full_name.strip().split()
        if not words: return ""
        words[0] = words[0].upper()
        for i in range(1, len(words)):
            words[i] = words[i].capitalize()
        return " ".join(words)

    @staticmethod
    def format_pages(num) -> str:
        if num is None or num == "": return "0"
        try:
            n = int(num)
        except ValueError:
            return str(num)
        if n == 0: return "0"

        last_digit = n % 10
        last_two_digits = n % 100
        if 11 <= last_two_digits <= 19:
            return f"{n}-ти"
        elif last_digit == 1:
            return f"{n}-му"
        elif 2 <= last_digit <= 4:
            return f"{n}-х"
        else:
            return f"{n}-ти"

    def generate_support_logs(self, city: str, supp_number: str, supp_date: str, raw_documents: list) -> str:
        lines = [
            f"Супровід №{supp_number} від {supp_date} (м. {city})",
            "-" * 50
        ]
        for idx, raw in enumerate(raw_documents, start=1):
            name = self.format_name(raw.get('name', ''))
            lines.append(f"{idx}. {name}")
        return "\n".join(lines)

    def generate_support_batch(self, city: str, supp_number: str, supp_date: str, raw_documents: list) -> tuple[bytes, str]:
        if city not in self.templates:
            raise FileNotFoundError(f"Шаблон для міста {city} не знайдено.")

        template_path = self.templates[city]
        doc = DocxTemplate(str(template_path))

        formatted_docs = []
        for idx, raw in enumerate(raw_documents):
            raw_other = raw.get('other')
            other_val = int(raw_other) if raw_other else 0
            other_str = self.format_pages(other_val) if other_val > 0 else "0"

            # Формуємо словник саме так, як очікує шаблон Word
            formatted_doc = {
                'SUPP_NUMBER': supp_number,
                'SUPP_DATE': supp_date,
                'INCREMENTAL': idx + 1,
                'NAME': self.format_name(raw.get('name_gen', '')),
                'TOTAL_PAGES': self.format_pages(raw.get('total', 0)),
                'NOTIF_PAGES': self.format_pages(raw.get('notif', 0)),
                'COM_ASSIGN_PAGES': self.format_pages(raw.get('assign', 0)),
                'COM_RESULT_PAGES': self.format_pages(raw.get('result', 0)),
                'ACT_PAGES': self.format_pages(raw.get('act', 0)),
                'EXPL_PAGES': self.format_pages(raw.get('expl', 0)),
                'CHAR_PAGES': self.format_pages(raw.get('char', 0)),
                'MED_PAGES': self.format_pages(raw.get('med', 0)),
                'CARD_PAGES': self.format_pages(raw.get('card', 0)),
                'SET_PAGES': self.format_pages(raw.get('set_docs', 0)),
                'MOVE_PAGES': self.format_pages(raw.get('move', 0)),
                'OTHER_PAGES': other_str,
            }
            formatted_docs.append(formatted_doc)

        context = {'documents': formatted_docs}
        doc.render(context)

        byte_io = io.BytesIO()
        doc.save(byte_io)
        byte_io.seek(0)

        file_name = f"Пакет_Супроводів_{city}_{len(formatted_docs)}шт.docx"
        return byte_io.getvalue(), file_name