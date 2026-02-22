from pathlib import Path
from processing.parsers.ParserFactory import ParserFactory
import config
from utils.utils import format_to_excel_date, get_file_name, clean_text, check_birthday_id_number
import dics.deserter_xls_dic as col
from dics.deserter_xls_dic import *
from datetime import datetime
import re
from typing import Final
from processing.parsers.MLParser import MLParser

class DocProcessor:

    __PIECE_HEADER : Final = 'header'
    __PIECE_1 : Final  = 'piece 1'
    __PIECE_2 : Final  = 'piece 2'
    __PIECE_3 : Final  = 'piece 3'
    __PIECE_4 : Final  = 'piece 4'

    def __init__(self, workflow, file_path, original_filename, insertion_date=datetime.now()):
        self.file_path = file_path
        self.original_filename = original_filename
        self.workflow = workflow
        self.insertion_date = insertion_date
        self.logger = workflow.log_manager.get_logger()
        self.response = {
            'insertionDate' :None,
        }
        if file_path:
            self.extension = Path(self.file_path).suffix
            self.engine = ParserFactory.get_parser(file_path, workflow.log_manager)
        self.ml_parser = MLParser(model_path=config.ML_MODEL_PATH, log_manager=self.workflow.log_manager)

    def process(self):
        self.logger.debug(f"--- Обробка тексту... {self.extension}")
        doc_pieces = {}

        # Отримуємо основні блоки
        doc_pieces[self.__PIECE_HEADER] = self.engine.extract_text_between(PATTERN_PIECE_HEADER_START, PATTERN_PIECE_HEADER_END, True)
        doc_pieces[self.__PIECE_1] = self.engine.extract_text_between(PATTERN_PIECE_1_START, PATTERN_PIECE_1_END, True)
        doc_pieces[self.__PIECE_4] = self.engine.extract_text_between(PATTERN_PIECE_4_START, PATTERN_PIECE_4_END, True)

        raw_piece_3 = self.engine.extract_text_between(PATTERN_PIECE_3_START, PATTERN_PIECE_3_END, True) or ""

        if doc_pieces[self.__PIECE_HEADER] is None:
            self.logger.warning('>>> ⚠️header :' + str(doc_pieces[self.__PIECE_HEADER]))
        if doc_pieces[self.__PIECE_1] is None:
            self.logger.warning('>>> ⚠️ 1 :' + str(doc_pieces[self.__PIECE_1]))
        if raw_piece_3 is None:
            self.logger.warning('>>> ⚠️ 2 :' + str(raw_piece_3))
        if doc_pieces[self.__PIECE_4] is None:
            self.logger.warning('>>> ⚠️ 4 :' + str(doc_pieces[self.__PIECE_4]))

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
        self.workflow.stats.doc_names.append(self.original_filename)

        self.logger.debug(f"--- ✔️ Обробка закінчено. Знайдено осіб: {len(all_final_records)}")
        return all_final_records

    def process_fields(self, text_pieces):
        self.validatePieces(text_pieces)

        result = []

        fields = {
            col.COLUMN_INSERT_DATE: format_to_excel_date(self.insertion_date),
            col.COLUMN_MIL_UNIT: DEFAULT_MIL_UNIT,
        }

        text = text_pieces[self.__PIECE_HEADER]
        if text is not None:
            fields[col.COLUMN_MIL_UNIT] = self._extract_mil_unit(text)

        text = text_pieces[self.__PIECE_1]

        if text is not None:
            fields[col.COLUMN_DESERT_CONDITIONS] = self._extract_desert_conditions(text)
            fields[col.COLUMN_DESERTION_REGION] = self._extract_desertion_region(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_DESERTION_DATE] = self._extract_desertion_date(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_DESERTION_PLACE] = self._extract_desertion_place(clean_text(text), get_file_name(self.original_filename))
            fields[col.COLUMN_RETURN_DATE] = self._extract_return_date(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_DESERTION_TYPE] = self._extract_desertion_type(text, fields[col.COLUMN_DESERTION_PLACE])
            if self._check_return_sign(text_pieces[self.__PIECE_1]):
                fields[col.COLUMN_RETURN_DATE] = self._extract_return_date(text) or fields[col.COLUMN_DESERTION_DATE]
                fields[col.COLUMN_DESERTION_DATE] = NA
                fields[col.COLUMN_DESERTION_REGION] = NA
                fields[col.COLUMN_DESERTION_PLACE] = NA
            self.logger.debug('--- ' + COLUMN_RETURN_DATE + ':' + str(fields[col.COLUMN_RETURN_DATE]))

        text = text_pieces[self.__PIECE_3]
        ml_extracted = self.ml_parser.parse_text(text)
        if text is not None:
            fields[col.COLUMN_NAME] = self.get_best_match(ml_extracted.get(col.COLUMN_NAME), self._extract_name(text))
            fields[col.COLUMN_ID_NUMBER] = self.get_best_match(ml_extracted.get(col.COLUMN_ID_NUMBER), self._extract_id_number(text))
            fields[col.COLUMN_TZK] = self._extract_rtzk(clean_text(text))
            fields[col.COLUMN_PHONE] = self.get_best_match(ml_extracted.get(col.COLUMN_PHONE), self._extract_phone(text))
            fields[col.COLUMN_BIRTHDAY] = self.get_best_match(ml_extracted.get(col.COLUMN_BIRTHDAY), self._extract_birthday(text))
            fields[col.COLUMN_TITLE] = self._extract_title(text)
            fields[col.COLUMN_TITLE_2] = self._extract_title_2(fields[col.COLUMN_TITLE])
            fields[col.COLUMN_SERVICE_TYPE] = self.get_best_match(ml_extracted.get(col.COLUMN_SERVICE_TYPE), self._extract_service_type(text))
            fields[col.COLUMN_ADDRESS] = self.get_best_match(ml_extracted.get(col.COLUMN_ADDRESS), self._extract_address(clean_text(text)))
            fields[col.COLUMN_TZK_REGION] = self._extract_rtzk_region(fields[col.COLUMN_TZK])
            if fields[col.COLUMN_TZK_REGION] == NA:
                fields[col.COLUMN_TZK_REGION] = self._extract_rtzk_region(fields[col.COLUMN_ADDRESS])
            fields[col.COLUMN_BIO] = self.get_best_match(ml_extracted.get(col.COLUMN_BIO), self._extract_bio(clean_text(text), fields[col.COLUMN_NAME]))
            fields[col.COLUMN_ENLISTMENT_DATE] = self.get_best_match(ml_extracted.get(col.COLUMN_ENLISTMENT_DATE), self._extract_conscription_date(text))
            fields[col.COLUMN_SUBUNIT] = self.get_best_match(ml_extracted.get(col.COLUMN_SUBUNIT), self.extract_military_subunit(text, get_file_name(self.original_filename)))
            subunit2 = self.extract_military_subunit(text_pieces[self.__PIECE_3], get_file_name(self.original_filename), mapping=PATTERN_SUBUNIT2_MAPPING)
            if subunit2 is NA:
                subunit2 = self.extract_military_subunit(text_pieces[self.__PIECE_1],get_file_name(self.original_filename), mapping=PATTERN_SUBUNIT2_MAPPING)
            fields[col.COLUMN_SUBUNIT2] = subunit2
            fields[col.COLUMN_REVIEW_STATUS] = DEFAULT_REVIEW_STATUS_FOR_EDU_CENTER if fields[col.COLUMN_DESERTION_PLACE] == 'НЦ' else DEFAULT_REVIEW_STATUS

        fields[col.COLUMN_SERVICE_DAYS] = self._calculate_service_days(fields[col.COLUMN_ENLISTMENT_DATE], fields[col.COLUMN_DESERTION_DATE])

        text = text_pieces[self.__PIECE_4]
        fields[col.COLUMN_EXECUTOR] = self._extract_name(text)

        if self.is_desertion_case(fields):
            # validate the case
            self.validate_record(fields)
            result.append(fields)
        else:
            self.logger.debug("... ▶️ НЕ ДОДАЄМО, не кейз СЗЧ!")

        return result

    def is_desertion_case(self, record):
        if record[COLUMN_DESERT_CONDITIONS] == NA and record[COLUMN_RETURN_DATE] is None:
            return False
        return True

    def validate_record(self, record):
        if not check_birthday_id_number(record[COLUMN_BIRTHDAY], record[COLUMN_ID_NUMBER]):
            self.logger.warning('------ ⚠️ Невідповідність дати народження та ІПН! ' + str(record[COLUMN_BIRTHDAY] + '/' + str(record[COLUMN_ID_NUMBER])))
            return False

        # might be exceptions here later, if critical errors

        return True

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

        matches = list(re.finditer(PATTERN_STRICT_NAME, doc_piece_3, re.MULTILINE))

        if not matches:
            return [doc_piece_3.strip()]

        persons = []
        for i in range(len(matches)):
            start_idx = matches[i].start()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(doc_piece_3)

            person_data = doc_piece_3[start_idx:end_idx].strip()

            if len(person_data) > 20:
                persons.append(person_data)
                self.logger.debug('... 🏃‍♂️ПЕРСОНА: ' + self._extract_name(person_data))

        return persons

    @staticmethod
    def _extract_mil_unit(text):
        match = re.search(PATTERN_MIL_UNIT, text)
        if match:
            return match.group(0).upper()
        return NA

    @staticmethod
    def _extract_bio(text, full_name):
        if not full_name or full_name == NA:
            return text
        start_index = text.find(full_name)
        if start_index != -1:
            return text[start_index:].strip()

        return text

    @staticmethod
    def _extract_name(text):
        match = re.search(PATTERN_NAME, text)
        if match:
            return f"{match.group(1)} {match.group(3)} {match.group(4)}".strip()
        return NA

    @staticmethod
    def _extract_title(text):
        # Проходимо по мапінгу (важливо: довгі назви мають бути вище коротких)
        for pattern, canonical_name in PATTERN_TITLE_MAPPING.items():
            if re.search(pattern, text, re.IGNORECASE):
                return canonical_name
        return NA

    @staticmethod
    def _extract_title_2(canonical_title):
        if canonical_title is None: return NA
        parts = canonical_title.split()
        return parts[-1] if parts else NA

    @staticmethod
    def _extract_service_type(text):
        for pattern, result in PATTERN_SERVICE_TYPE_MAPPING.items():
            if re.search(pattern, text, re.IGNORECASE):
                return result
        return DEFAULT_SERVICE_TYPE # default

    @staticmethod
    def _extract_id_number(text):
        marker_match = re.search(PATTERN_ID_MARKER, text)
        if marker_match:
            after_marker = text[marker_match.end():marker_match.end() + 30]
            if re.search(PATTERN_ID_ABSENCE, after_marker):
                return NA
            digits_match = re.search(PATTERN_ID_DIGITS, after_marker)
            if digits_match:
                return digits_match.group(1)
        standalone_digits = re.findall(PATTERN_ID_STANDALONE, text)
        return standalone_digits[0] if standalone_digits else NA

    @staticmethod
    def _extract_phone(text):
        match = re.search(PATTERN_PHONE, text, re.IGNORECASE)

        if match:
            raw_phone = match.group(2)
            digits = re.sub(r'\D', '', raw_phone)
            if len(digits) >= 10:
                return digits[-10:]
        return NA

    @staticmethod
    def _extract_conscription_date(text):

        start_match = re.search(PATTERN_RTZK_CALLED, text)

        lookback_area = text[start_match.start():-1]
        # 2. Шукаємо всі дати в цій зоні
        dates = re.findall(PATTERN_DATE, lookback_area)
        if dates:
            found_date = dates[0]
            return format_to_excel_date(found_date)

        return NA

    @staticmethod
    def _extract_birthday(text):
        match = re.search(PATTERN_BIRTHDAY, text, re.IGNORECASE)

        if match:
            date_str = match.group(1).strip()
            return format_to_excel_date(date_str)

        backup_pattern = PATTERN_BIRTHDAY_FALLBACK
        all_dates = re.findall(backup_pattern, text)
        if all_dates:
            return format_to_excel_date(all_dates[0])

        return NA

    @staticmethod
    def _extract_address(text):
        match_marker = re.search(PATTERN_ADDRESS_MARKER, text, re.IGNORECASE)
        if not match_marker:
            return NA

        address_part = text[match_marker.end():].strip()
        address_part = re.sub(PATTERN_ADDRESS_CLEANUP_PREFIX, '', address_part, flags=re.IGNORECASE)
        match = re.search(PATTERN_ADDRESS_CONTENT, address_part, re.IGNORECASE | re.DOTALL)
        if match:
            address = match.group(1).strip()
            return " ".join(address.split()).strip(PATTERN_CLEANUP_POINTS)

        return NA

    @staticmethod
    def _extract_rtzk(text: str) -> str:
        match = re.search(PATTERN_RTZK, text)
        if not match:
            return NA

        res = match.group(1).strip()
        print('res = ' + res)
        for p in PATTERN_RTZK_TRASH:
            res = re.sub(p, '', res)

        res = res.rstrip('., ')

        res = re.sub(r'(?i)ЦТК', 'ТЦК', res)
        res = " ".join(res.split())

        return res

    @staticmethod
    def _extract_rtzk_region(tck_text: str) -> str:
        if not tck_text or tck_text == NA:
            return NA
        for pattern, region_name in PATTERN_REGION:
            if re.search(pattern, tck_text):
                return region_name
        return NA

    @staticmethod
    def _extract_desertion_date(text):
        match = re.search(PATTERN_DESERTION_DATE, text, re.IGNORECASE)

        if match:
            return format_to_excel_date(match.group(1))
        fallback = re.search(PATTERN_DATE, text)
        if fallback:
            return format_to_excel_date(fallback.group(1))

        return NA

    @staticmethod
    def _extract_desert_conditions(text):
        paragraphs = [p.strip() for p in re.split(PATTERN_PARAGRAPH_SPLIT, text) if p.strip()]

        for para in paragraphs:
            clean_para = " ".join(para.split()).lower()
            has_check = any(marker in clean_para for marker in PATTERN_DESERT_CHECK_MARKERS)
            has_absence = any(marker in clean_para for marker in PATTERN_DESERT_ABSENCE_MARKERS)
            if has_check or has_absence:

                # взяти тільки необхідну частину а не весь гарбедж
                marker = PATTERN_DESERTION_CONDITIONS_ACTUAL_PART_AFTER
                if marker in para:
                    parts = para.split(marker, 1)
                    actual_text = parts[1].strip()
                    return actual_text
                return " ".join(para.split())

        return NA

    @staticmethod
    def _extract_return_date(text):
        clean_txt = re.sub(r'\s+', ' ', text).lower()
        if not any(marker in clean_txt for marker in PATTERN_RETURN_MARKERS):
            return None
        match = re.search(PATTERN_RETURN_DATE, text, re.IGNORECASE)
        if match:
            return format_to_excel_date(match.group(1))

        fallback_with_presence = re.search(PATTERN_DATE, text)
        if fallback_with_presence:
            return format_to_excel_date(fallback_with_presence.group(1))

        return None

    @staticmethod
    def _extract_desertion_region(text):
        match = re.search(PATTERN_DESERTION_REGION_MAIN, text, re.DOTALL)
        if match:
            full_address = " ".join(match.group(1).split())
            return full_address.strip().rstrip('.')

        backup_match = re.search(PATTERN_DESERTION_REGION_BACKUP, text)
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
                self.logger.error(f"--- ⚠️ Нелогічна кількість днів служби: {days}. Перевірте дати.")
                return 0

            return days

        except Exception as e:
            self.logger.warning(f"--- ⚠️ Помилка розрахунку днів: {e}")
            return 0

    def extract_military_subunit(self, text, file_name=None, mapping=PATTERN_SUBUNIT_MAPPING):
        short_values = set()
        for val in mapping.values():
            clean_val = val.replace(r'\1', '').strip()
            if clean_val:
                short_values.add(clean_val)

        # ЕТАП 1: Перевірка назви файлу (тепер з IGNORECASE)
        if file_name:
            # Сортуємо від найдовших до найкоротших, щоб спочатку ловити специфічні назви
            sorted_shorts = sorted(short_values, key=len, reverse=True)

            for short_val in sorted_shorts:
                # Паттерн шукає без урахування регістру (re.IGNORECASE)
                pattern = rf'(?:^|[\s_])(\d*[\s_]*)?{re.escape(short_val)}(?=[\s_]|$)'
                match = re.search(pattern, file_name, re.IGNORECASE)

                if match:
                    # Отримуємо цифри перед назвою (наприклад, "3" з "3 САДН")
                    # match.group(1) містить цифри та пробіли/підкреслення перед назвою
                    prefix = match.group(1) or ""
                    digits = re.sub(r'\D', '', prefix)  # Залишаємо тільки цифри

                    # Формуємо результат: цифри + пробіл + значення з мапінгу (short_val)
                    if digits:
                        return f"{digits} {short_val}"
                    return short_val

        # ЕТАП 2: Пошук у тексті через мапінг (якщо в файлі не знайдено)
        found_subunits = []
        for pattern, abbreviation in mapping.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if r'\1' in abbreviation:
                    digit = match.group(1) if match.group(1) else ""
                    res = abbreviation.replace(r'\1', digit).strip()
                else:
                    res = abbreviation
                found_subunits.append(res)
                return res

        return NA

    @staticmethod
    def _extract_desertion_place(text, file_name=None):
        sorted_patterns = sorted(
            PATTERN_DESERTION_PLACE_MAPPING.items(),
            key=lambda item: len(item[1]),
            reverse=True
        )
        if file_name:
            for pattern, mapping_value in sorted_patterns:
                if re.search(mapping_value, file_name, re.IGNORECASE):
                    return mapping_value

        for pattern, short_name in sorted_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return short_name
        return NA

    @staticmethod
    def _extract_desertion_type(text, desertion_where):
        des_type = 'СЗЧ'
        for pattern, short_name in PATTERN_DESERTION_TYPE_MAPPING.items():
            if re.search(pattern, text, re.IGNORECASE):
                return short_name
        if desertion_where == 'НЦ':
            des_type = 'СЗЧ з А2900'
        return des_type

    def check_for_errors(self, data_for_excel):
        result = True
        if not data_for_excel:
            return False

        for data_dict in data_for_excel:
            for col_name, value in data_dict.items():
                if value == NA:
                    error = 'КОЛОНКА ' + col_name + ' ПОРОЖНЯ!'
                    self.logger.warning('------ ⚠️ ' + error)
                    self.workflow.stats.add_error(self.original_filename, error)
                    result = False
        return result

    def _check_return_sign(self, text):
        for pattern in PATTERN_RETURN_SIGN:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug('--- ✌️ ВИЯВЛЕНО ПОВЕРНЕННЯ! УРА')
                return True
        return False

    def get_best_match(self, ml_val, regex_val):
        ml_str = str(ml_val or "").strip()
        regex_str = str(regex_val or "").strip()
        return ml_str if len(ml_str) >= len(regex_str) else regex_str