from pathlib import Path
from .parsers.ParserFactory import ParserFactory
import config
from utils.utils import format_to_excel_date, get_file_name, clean_text
import dics.deserter_xls_dic as col
from dics.deserter_xls_dic import *
from datetime import datetime
import re
from typing import Final

class DocProcessor:

    __PIECE_HEADER : Final = 'header'
    __PIECE_1 : Final  = 'piece 1'
    __PIECE_2 : Final  = 'piece 2'
    __PIECE_3 : Final  = 'piece 3'
    __PIECE_4 : Final  = 'piece 4'

    def __init__(self, workflow, file_path):
        self.file_path = file_path
        self.workflow = workflow
        self.response = {
            'insertionDate' :None,
        }
        self.extension = Path(self.file_path).suffix
        self.engine = ParserFactory.get_parser(file_path)

    def process(self):
        print(f"--- Обробка тексту... {self.extension}")
        doc_pieces = {}

        # Отримуємо основні блоки
        doc_pieces[self.__PIECE_HEADER] = self.engine.extract_text_between(PATTERN_PIECE_HEADER_START, PATTERN_PIECE_HEADER_END, True)
        doc_pieces[self.__PIECE_1] = self.engine.extract_text_between(PATTERN_PIECE_1_START, PATTERN_PIECE_1_END, True)
        doc_pieces[self.__PIECE_4] = self.engine.extract_text_between(PATTERN_PIECE_4_START, PATTERN_PIECE_4_END, True)

        #print('>>>header :' + str(doc_pieces[self.PIECE_HEADER]))
        #print('>>>1 :' + str(doc_pieces[self.PIECE_1]))
        #print('>>>4 :' + str(doc_pieces[self.PIECE_4]))

        raw_piece_3 = self.engine.extract_text_between(PATTERN_PIECE_3_START, PATTERN_PIECE_3_END, True) or ""
        persons = self.cut_into_person(raw_piece_3)
        all_final_records = []
        for person_text in persons:
            individual_pieces = doc_pieces.copy()
            individual_pieces[self.__PIECE_3] = person_text

            processed_data = self.process_fields(individual_pieces)

            if isinstance(processed_data, list):
                all_final_records.extend(processed_data)
            else:
                all_final_records.append(processed_data)

        self.workflow.stats.attachmentWordProcessed += 1
        self.workflow.stats.doc_names.append(self.file_path)

        print(f"--- ✔️ Обробка закінчено. Знайдено осіб: {len(all_final_records)}")
        return all_final_records

    def process_fields(self, text_pieces):
        self.validatePieces(text_pieces)

        result = []

        fields = {
            col.COLUMN_INSERT_DATE: format_to_excel_date(datetime.now()),
            col.COLUMN_MIL_UNIT: DEFAULT_MIL_UNIT,
        }

        text = text_pieces[self.__PIECE_HEADER]
        if text is not None:
            fields[col.COLUMN_MIL_UNIT] = self._extract_mil_unit(text)

        text = text_pieces[self.__PIECE_1]
        if text is not None:
            fields[col.COLUMN_DESERTION_DATE] = self._extract_desertion_date(text)
            fields[col.COLUMN_DESERTION_REGION] = self._extract_desertion_region(clean_text(text))
            fields[col.COLUMN_DESERT_CONDITIONS] = self._extract_desert_conditions(text)
            fields[col.COLUMN_DESERTION_PLACE] = self._extract_desertion_place(clean_text(text), get_file_name(self.file_path))
            fields[col.COLUMN_RETURN_DATE] = self._extract_return_date(text)

        text = text_pieces[self.__PIECE_3]
        if text is not None:
            fields[col.COLUMN_NAME] = self._extract_name(text)
            fields[col.COLUMN_ID_NUMBER] = self._extract_id_number(text)
            fields[col.COLUMN_TZK] = self._extract_rtzk(clean_text(text))
            fields[col.COLUMN_PHONE] = self._extract_phone(text)
            fields[col.COLUMN_BIRTHDAY] = self._extract_birthday(text)
            fields[col.COLUMN_TITLE] = self._extract_title(text)
            fields[col.COLUMN_SERVICE_TYPE] = self._extract_service_type(text)
            fields[col.COLUMN_ADDRESS] = self._extract_address(clean_text(text))
            fields[col.COLUMN_BIO] = self._extract_bio(clean_text(text), fields[col.COLUMN_NAME])
            fields[col.COLUMN_ENLISTMENT_DATE] = self._extract_conscription_date(text)
            fields[col.COLUMN_SUBUNIT] = self._extract_military_subunit(text, get_file_name(self.file_path))

        fields[col.COLUMN_SERVICE_DAYS] = self._calculate_service_days(fields[col.COLUMN_ENLISTMENT_DATE], fields[col.COLUMN_DESERTION_DATE])

        text = text_pieces[self.__PIECE_4]
        fields[col.COLUMN_EXECUTOR] = self._extract_name(text)
        result.append(fields)
        return result


    def validatePieces(self, doc_pieces):
        if doc_pieces[self.__PIECE_HEADER] is None:
            raise ValueError(f"❌ Частина з довідкою не витягнуто")
        if doc_pieces[self.__PIECE_1] is None:
            raise ValueError(f"❌ Частина 1 не витягнуто!")
        if doc_pieces[self.__PIECE_3] is None:
            raise ValueError(f"❌ Частина 3 не витягнуто!")
        if doc_pieces[self.__PIECE_4] is None:
            raise ValueError(f"❌ Частина 4 не витягнуто!")


    def cut_into_person(self, doc_piece_3):
        if not doc_piece_3:
            return []

        matches = list(re.finditer(STRICT_NAME_PATTERN, doc_piece_3, re.MULTILINE))

        if not matches:
            return [doc_piece_3.strip()]

        persons = []
        for i in range(len(matches)):
            start_idx = matches[i].start()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(doc_piece_3)

            person_data = doc_piece_3[start_idx:end_idx].strip()

            if len(person_data) > 20:
                persons.append(person_data)
                print('... 🏃‍♂️ПЕРСОНА: ' + self._extract_name(person_data))

        return persons


    def _extract_mil_unit(self, text):
        pattern = r'\b[А-ЯA-Z]\d{4}\b'
        match = re.search(pattern, text)
        if match:
            return match.group(0).upper()
        return NA

    def _extract_bio(self, text, full_name):
        if not full_name or full_name == NA:
            return text
        start_index = text.find(full_name)
        if start_index != -1:
            return text[start_index:].strip()

        return text

    def _extract_name(self, text):
        match = re.search(NAME_PATTERN, text)
        if match:
            return f"{match.group(1)} {match.group(3)} {match.group(4)}".strip()
        return NA

    def _extract_title(self, text):
        pattern = r'\b(' + '|'.join(TITLES) + r')\b'

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).lower()
        return NA

    def _extract_service_type(self, text):
        mapping = {
            r'приз[ио]вом|мобілізаці': "призовом",
            r'контрактом': "контрактом"
        }
        for pattern, result in mapping.items():
            if re.search(pattern, text, re.IGNORECASE):
                return result
        return NA

    def _extract_id_number(self, text):
        marker_pattern = r'(?i)(?:РНОКПП|ІПН|І\.П\.Н\.|РНОК\s*ПП)'

        marker_match = re.search(marker_pattern, text)

        if marker_match:
            after_marker = text[marker_match.end():marker_match.end() + 30]
            if re.search(r'(?i)(відсутн|не надано|немає|відомості)', after_marker):
                return NA
            digits_match = re.search(r'(\d{10})\b', after_marker)
            if digits_match:
                return digits_match.group(1)
        standalone_digits = re.findall(r'\b([1-9]\d{9})\b', text)

        return standalone_digits[0] if standalone_digits else NA

    def _extract_phone(self, text):
        pattern = r'(?i)(?:номер|(?:ефон(у)?)|тел\.)[\s\w.:+]*?(\+?\s?3?8?[\s(-]*0\d{2}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2})\b'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            raw_phone = match.group(2)
            digits = re.sub(r'\D', '', raw_phone)
            if len(digits) >= 10:
                return digits[-10:]
        return NA

    def _extract_conscription_date(self, text):
        """
        Витягує дату призову. Підтримує формати: 01.01.2025 та 01.01.25.
        """
        # Патерн для дати: ДД.ММ.РРРР або ДД.ММ.РР
        # \d{2} - день, \d{2} - місяць, (\d{4}|\d{2}) - рік (4 або 2 цифри)
        date_pattern = r'(\d{2}\.\d{2}\.(?:\d{4}|\d{2}))'

        # 1. Знаходимо РНОКПП/ІПН, щоб знати, де зупинити пошук
        id_match = re.search(r'(?:РНОКПП|ІПН)', text, re.IGNORECASE)
        if not id_match:
            return NA

        pos_id = id_match.start()
        # Беремо зону пошуку ПЕРЕД РНОКПП (близько 150 символів)
        lookback_area = text[max(0, pos_id - 150):pos_id]

        # 2. Шукаємо всі дати в цій зоні
        dates = re.findall(date_pattern, lookback_area)

        if dates:
            # Беремо останню дату (найближчу до РНОКПП)
            found_date = dates[-1]
            return format_to_excel_date(found_date)

        return NA

    def _extract_birthday(self, text):
        pattern = r'(\d{2}\.\d{2}\.\d{4})\s*(?:року\s+народження|р\.н\.|народження)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            date_str = match.group(1).strip()
            return format_to_excel_date(date_str)

        backup_pattern = r'\b(\d{2}\.\d{2}\.\d{4})\b'
        all_dates = re.findall(backup_pattern, text)
        if all_dates:
            return format_to_excel_date(all_dates[0])

        return NA

    def _extract_address(self, text):
        marker = "Адреса проживання"
        match_marker = re.search(re.escape(marker), text, re.IGNORECASE)
        if not match_marker:
            return NA

        address_part = text[match_marker.end():].strip()
        address_part = re.sub(r'^(?:\s*військовослужбовця)?\s*:?\s*', '', address_part, flags=re.IGNORECASE)
        pattern = r'^((?:(?!Близькі родичі|;|\n).)+)'
        match = re.search(pattern, address_part, re.IGNORECASE | re.DOTALL)
        if match:
            address = match.group(1).strip()
            return " ".join(address.split()).strip(':;,. ')

        return NA

    def _extract_rtzk(self, text):
        pattern = r'(?i)((?:[А-ЯҐЄІЇ-][^.,!?\s]*\s+){1,5}?(?:О?РТЦК|ТЦК|МТЦК)(?:\s*(?:та|&)?\s*СП)?(?:\s?,?\s+м\.\s+[А-ЯІЇЄа-яіїє\-\']+,?(?:\s+[А-ЯІЇЄа-яіїє\-\']+)*|\s+[А-ЯІЇЄа-яіїє\']+\s+обл\.?)?)'

        match = re.search(pattern, text)
        if match:
            res = match.group(1).strip()
            res = re.sub(r'\s*,?\s*\d{2}\.\d{2}\.\d{2,4}.*$', '', res)

            trash_patterns = [
                r'(?i)призваний\s+',
                r'(?i)призвана\s+',
                r'(?i)яким\s+',
                r'(?i)на\s+військову\s+службу\s+',
                r'(?i)за\s+призовом\s+',
                r'(?i)під\s+час\s+мобілізації\s+',
                r'(?i)з\s+\d{2}\.\d{2}\.\d{2,4}',
            ]

            for p in trash_patterns:
                res = re.sub(p, '', res)
            final_res = " ".join(res.split()).strip(':;,. ')
            final_res = re.sub(r'(?i)^(на військову службу|призваний)\s+', '', final_res)

            return final_res if final_res else NA

        return NA

    def _extract_desertion_date(self, text):
        pattern = r'(\d{2}\.\d{2}\.\d{4})(?=\s+року\s+(?:під час перевірки|був відсутній|самовільно залишив))'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return format_to_excel_date(match.group(1))
        fallback = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        if fallback:
            return format_to_excel_date(fallback.group(1))

        return NA

    def _extract_desert_conditions(self, text):
        paragraphs = [p.strip() for p in re.split(r'[\r\n]{2,}', text) if p.strip()]
        check_markers = ["під час перевірки", "під час шикування", "перевірці наявності"]
        absence_markers = ["відсутн", "виявлено відсутність", "не було в наявності", "не повернувся", "не прибуття", "неповернення"]

        for para in paragraphs:
            clean_para = " ".join(para.split()).lower()
            has_check = any(marker in clean_para for marker in check_markers)
            has_absence = any(marker in clean_para for marker in absence_markers)

            if has_check or has_absence:
                return " ".join(para.split())

        return NA

    def _extract_return_date(self, text):
        if "був присутній" not in text.lower():
            return None
        pattern = r'(\d{2}\.\d{2}\.\d{4})(?=\s+року\s+був\s+присутній)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return format_to_excel_date(match.group(1))

        fallback_with_presence = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        if fallback_with_presence:
            return format_to_excel_date(fallback_with_presence.group(1))

        return None

    def _extract_desertion_region(self, text):
        pattern = r'(?i)(?:н\.п\.|с\.|м\.|село|місто|селище|смт)\s+([А-ЯҐЄІЇ][^.;]*?(?:області|обл\.))'

        match = re.search(pattern, text, re.DOTALL)
        if match:
            full_address = " ".join(match.group(1).split())
            return full_address.strip().rstrip('.')

        backup_pattern = r'(?i)([А-Я][а-яіЇє]*?\s+район[у|а]\s+[А-Я][а-яіЇє]*?\s+області)'
        backup_match = re.search(backup_pattern, text)
        if backup_match:
            return " ".join(backup_match.group(1).split())

        return NA

    def _calculate_service_days(self, conscription_date_str, desertion_date_str):
        if conscription_date_str == NA or desertion_date_str == NA:
            return 0
        try:
            def parse_date(d_str):
                return datetime.strptime(d_str, config.EXCEL_DATE_FORMAT)

            dt_start = parse_date(conscription_date_str)
            dt_end = parse_date(desertion_date_str)

            delta = dt_end - dt_start
            days = delta.days

            if days < 0 or days > 4000:
                print(f"[УВАГА] Нелогічна кількість днів служби: {days}. Перевірте дати.")
                return 0

            return days

        except Exception as e:
            print(f"Помилка розрахунку днів: {e}")
            return 0

    def _extract_military_subunit(self, text, file_name=None):
        short_values = set()
        for val in SUBUNIT_MAPPING.values():
            clean_val = val.replace(r'\1', '').strip()
            if clean_val:
                short_values.add(clean_val)

        # ЕТАП 1: Перевірка назви файлу (тепер з IGNORECASE)
        if file_name:
            sorted_shorts = sorted(short_values, key=len, reverse=True)

            for short_val in sorted_shorts:
                pattern = rf'(?:^|[\s_])(\d*[\s_]*)?{re.escape(short_val)}(?=[\s_]|$)'

                match = re.search(pattern, file_name, re.IGNORECASE)

                if match:
                    res = match.group(0).strip()
                    return re.sub(rf'(\d+)\s*({re.escape(short_val)})', r'\1 \2', res, flags=re.IGNORECASE).replace('_','')

        # ЕТАП 2: Пошук у тексті через мапінг (якщо в файлі не знайдено)
        found_subunits = []
        for pattern, abbreviation in SUBUNIT_MAPPING.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if r'\1' in abbreviation:
                    digit = match.group(1) if match.group(1) else ""
                    res = abbreviation.replace(r'\1', digit).strip()
                else:
                    res = abbreviation
                found_subunits.append(res)

        return found_subunits[-1] if found_subunits else NA

    def _extract_desertion_place(self, text, file_name=None):
        short_values = list(set(DESERTION_PLACE_MAPPING.values()))

        if file_name:
            for val in short_values:
                if re.search(rf'\b{re.escape(val)}\b', file_name, re.IGNORECASE):
                    return val

        for pattern, short_name in DESERTION_PLACE_MAPPING.items():
            if re.search(pattern, text, re.IGNORECASE):
                return short_name

        return NA

    def check_for_errors(self, data_for_excel):
        result = True
        if not data_for_excel:
            return False

        for data_dict in data_for_excel:
            for col_name, value in data_dict.items():
                if value == NA:
                    error = 'КОЛОНКА ' + col_name + ' ПОРОЖНЯ!'
                    print('------ ⚠️ ' + error)
                    self.workflow.stats.add_error(self.file_path, error)
                    result = False
        return result
