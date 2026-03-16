import io
from pathlib import Path
from docxtpl import DocxTemplate
import os

class DocTemplator:
    def __init__(self, templates_dir: Path):

        self.templates_dir = Path(templates_dir)
        self.support_detailed_dir = os.path.join(self.templates_dir, 'support-form-detailed')
        self.support_standart_dir = os.path.join(self.templates_dir, 'support-form-standart')
        self.notif_dir = os.path.join(self.templates_dir, 'notif-form')

        self.templates_detailed = {
            'Миколаїв': self.support_detailed_dir + '/Мико.docx',
            'Дніпро': self.support_detailed_dir + '/Дніпро.docx',
            'Донецьк': self.support_detailed_dir + '/Донецьк.docx'
        }
        self.templates_standart = {
            'Миколаїв': self.support_standart_dir + '/Мико.docx',
            'Дніпро': self.support_standart_dir + '/Дніпро.docx',
            'Донецьк': self.support_standart_dir + '/Донецьк.docx'
        }
        self.region_templates = {
            'Миколаївська область': self.notif_dir + '/Мико.docx',
            'Дніпро': self.notif_dir + '/Дніпро.docx',
            'Донецьк': self.notif_dir + '/Донецьк.docx'
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

    def _format_military_name(self, full_name_gen: str) -> str:
        """
        Допоміжний метод: робить прізвище ВЕЛИКИМИ літерами,
        а ім'я та по батькові - з великої (напр. КУЛІЦИ Олега Володимировича).
        """
        if not full_name_gen:
            return ""

        parts = full_name_gen.strip().split()
        if not parts:
            return ""

        parts[0] = parts[0].upper()
        for i in range(1, len(parts)):
            parts[i] = parts[i].capitalize()

        return " ".join(parts)

    def generate_support_batch_standart(self, city: str, supp_number: str, supp_date: str, raw_documents: list) -> tuple[bytes, str]:
        if city not in self.templates_standart:
            raise FileNotFoundError(f"Шаблон для міста {city} не знайдено.")

        template_path = self.templates_standart[city]
        doc = DocxTemplate(str(template_path))

        formatted_docs = []
        for idx, raw in enumerate(raw_documents):
            if not raw:
                continue

            title_gen = raw.get('title_gen') or ''
            name_gen = raw.get('name_gen') or ''

            formatted_doc = {
                'NUMBER': raw.get('seq_num'),
                'TITLE': title_gen.lower(),
                'NAME': self._format_military_name(name_gen),
                'TOTAL_PAGES': raw.get('total', 0)
            }
            formatted_docs.append(formatted_doc)

        context = {
            'SUPP_DATE': supp_date,
            'SUPP_NUMBER': supp_number,
            'CITY': city,
            'documents': formatted_docs
        }

        doc.render(context)

        byte_io = io.BytesIO()
        doc.save(byte_io)
        byte_io.seek(0)

        file_name = f"Пакет_Супроводів_{city}_{len(formatted_docs)}шт.docx"
        return byte_io.getvalue(), file_name

    def generate_support_batch_detailed(self, city: str, supp_number: str, supp_date: str, raw_documents: list) -> tuple[bytes, str]:
        if city not in self.templates_detailed:
            raise FileNotFoundError(f"Шаблон для міста {city} не знайдено.")

        template_path = self.templates_detailed[city]
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
                'INCREMENTAL': raw.get('seq_num', 0),
                'TITLE': raw.get('title_gen', ''),
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


    def generate_notif_batch(self, region: str, notif_number: str, notif_date: str, raw_documents: list) -> tuple[bytes, str]:
        if region not in self.region_templates:
            print('>>> шаблон не знайдено ' + str(region))
            raise FileNotFoundError(f"Шаблон для регіону {region} не знайдено.")

        template_path = self.region_templates[region]
        doc = DocxTemplate(str(template_path))

        formatted_docs = []
        for idx, raw in enumerate(raw_documents):
            # Формуємо словник саме так, як очікує шаблон Word
            formatted_doc = {
                'NOTIF_NUMBER': notif_number,
                'NOTIF_DATE': notif_date,
                'INCREMENTAL': raw.get('seq_num', 0),
                'NOTIF_CONDITIONS': raw.get('desertion_conditions', ''),
            }
            formatted_docs.append(formatted_doc)

        context = {'documents': formatted_docs}
        doc.render(context)

        byte_io = io.BytesIO()
        doc.save(byte_io)
        byte_io.seek(0)

        file_name = f"Пакет_Повідомлень_{region}_{len(formatted_docs)}шт.docx"
        return byte_io.getvalue(), file_name