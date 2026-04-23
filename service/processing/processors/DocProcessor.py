from pathlib import Path
from service.processing.parsers.ParserFactory import ParserFactory
import config
from service.storage.LoggerManager import LoggerManager
from utils.utils import get_file_name, clean_text, check_birthday_id_number, calculate_days_between
import dics.deserter_xls_dic as col
from service.processing.parsers.MLParser import MLParser
from utils.regular_expressions import *

class DocProcessor:

    __PIECE_HEADER : Final = 'header'
    __PIECE_1 : Final  = 'piece 1'
    __PIECE_2 : Final  = 'piece 2'
    __PIECE_3 : Final  = 'piece 3'
    __PIECE_4 : Final  = 'piece 4'

    def __init__(self, log_manager: LoggerManager, file_path, original_filename, insertion_date=datetime.now(), use_ml=True):
        self.file_path = file_path
        self.original_filename = original_filename
        self.logger = log_manager.get_logger()
        self.log_manager = log_manager
        if file_path:
            self.extension = Path(self.file_path).suffix
            self.engine = ParserFactory.get_parser(file_path, self.log_manager)
        self.ml_parser = MLParser(model_path=config.ML_MODEL_PATH, log_manager=self.log_manager, use_ml=use_ml)

    def process(self):
        self.logger.debug(f"--- Обробка тексту... {self.extension}")
        doc_pieces = {self.__PIECE_HEADER: self.engine.extract_text_between(PATTERN_PIECE_HEADER_START, PATTERN_PIECE_HEADER_END, True),
                      self.__PIECE_1: self.engine.extract_text_between(PATTERN_PIECE_1_START, PATTERN_PIECE_1_END, True),
                      self.__PIECE_4: self.engine.extract_text_between(PATTERN_PIECE_4_START, PATTERN_PIECE_4_END, True)}

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

        self.logger.debug(f"--- ✔️ Обробка закінчено. Знайдено осіб: {len(all_final_records)}")
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
            fields[col.COLUMN_MIL_UNIT] = extract_mil_unit(text)

        text = text_pieces[self.__PIECE_1]

        if text is not None:
            fields[col.COLUMN_DESERT_CONDITIONS] = extract_desert_conditions(text)
            fields[col.COLUMN_DESERTION_DATE] = extract_desertion_date(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_DESERTION_PLACE] = extract_desertion_place(clean_text(text), get_file_name(self.original_filename))
            fields[col.COLUMN_DESERTION_REGION] = extract_desertion_region(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_RETURN_DATE] = extract_return_date(fields[col.COLUMN_DESERT_CONDITIONS])
            fields[col.COLUMN_DESERTION_TYPE] = extract_desertion_type(text, fields[col.COLUMN_DESERTION_PLACE])
            fields[col.COLUMN_CC_ARTICLE] = extract_cc_article(fields[col.COLUMN_DESERTION_TYPE])
            if self._check_return_sign(text_pieces[self.__PIECE_1]):
                fields[col.COLUMN_RETURN_DATE] = extract_return_date(text) or fields[col.COLUMN_DESERTION_DATE]
                fields[col.COLUMN_DESERTION_DATE] = NA
                fields[col.COLUMN_DESERTION_REGION] = NA
                fields[col.COLUMN_DESERTION_PLACE] = NA
                # fields[col.COLUMN_DESERTION_TYPE] = fields[col.COLUMN_DESERTION_PLACE]
            self.logger.debug('--- ' + COLUMN_RETURN_DATE + ':' + str(fields[col.COLUMN_RETURN_DATE]))

        text = text_pieces[self.__PIECE_3]
        ml_extracted = self.ml_parser.parse_text(text)
        if text is not None:
            fields[col.COLUMN_NAME] = self.get_best_match(ml_extracted.get(col.COLUMN_NAME), extract_name(clean_text(text)))
            fields[col.COLUMN_ID_NUMBER] = self.get_best_match(ml_extracted.get(col.COLUMN_ID_NUMBER), extract_id_number(text))
            fields[col.COLUMN_TZK] = extract_rtzk(clean_text(text))
            fields[col.COLUMN_PHONE] = self.get_best_match(ml_extracted.get(col.COLUMN_PHONE), extract_phone(text))
            fields[col.COLUMN_BIRTHDAY] = self.get_best_match(ml_extracted.get(col.COLUMN_BIRTHDAY), extract_birthday(text))
            fields[col.COLUMN_TITLE] = extract_title(text)
            fields[col.COLUMN_TITLE_2] = extract_title_2(fields[col.COLUMN_TITLE])
            fields[col.COLUMN_SERVICE_TYPE] = self.get_best_match(ml_extracted.get(col.COLUMN_SERVICE_TYPE), extract_service_type(text))
            fields[col.COLUMN_ADDRESS] = self.get_best_match(ml_extracted.get(col.COLUMN_ADDRESS), extract_address(clean_text(text)))
            fields[col.COLUMN_TZK_REGION] = extract_region(fields[col.COLUMN_TZK])
            if fields[col.COLUMN_TZK_REGION] == NA:
                fields[col.COLUMN_TZK_REGION] = extract_region(fields[col.COLUMN_ADDRESS])
            fields[col.COLUMN_BIO] = self.get_best_match(ml_extracted.get(col.COLUMN_BIO), extract_bio(clean_text(text), fields[col.COLUMN_NAME]))
            fields[col.COLUMN_ENLISTMENT_DATE] = self.get_best_match(ml_extracted.get(col.COLUMN_ENLISTMENT_DATE), extract_conscription_date(text))
            fields[col.COLUMN_SUBUNIT] = self.get_best_match(ml_extracted.get(col.COLUMN_SUBUNIT), extract_military_subunit(text, get_file_name(self.original_filename)))
            subunit2 = extract_military_subunit(text_pieces[self.__PIECE_3], get_file_name(self.original_filename), mapping=PATTERN_SUBUNIT2_MAPPING)
            if subunit2 is NA:
                subunit2 = extract_military_subunit(text_pieces[self.__PIECE_1],get_file_name(self.original_filename), mapping=PATTERN_SUBUNIT2_MAPPING)
            fields[col.COLUMN_SUBUNIT2] = subunit2
            fields[col.COLUMN_REVIEW_STATUS] = DEFAULT_REVIEW_STATUS
            if fields[col.COLUMN_DESERTION_PLACE] == 'НЦ':
                fields[col.COLUMN_REVIEW_STATUS] = DEFAULT_REVIEW_STATUS_FOR_EDU_CENTER
                fields[col.COLUMN_ORDER_ASSIGNMENT_NUMBER] = 'НЦ'
                fields[col.COLUMN_ORDER_ASSIGNMENT_DATE] = fields[col.COLUMN_DESERTION_DATE]
                fields[col.COLUMN_KPP_NUMBER] = 'НЦ'
                fields[col.COLUMN_KPP_DATE] = fields[col.COLUMN_DESERTION_DATE]
                fields[col.COLUMN_DESERTION_TYPE] = DEFAULT_DESERTION_TYPE_FOR_EDU_CENTER

        fields[col.COLUMN_SERVICE_DAYS] = self._calculate_service_days(fields[col.COLUMN_ENLISTMENT_DATE], fields[col.COLUMN_DESERTION_DATE])

        if self._check_error_sign(text_pieces[self.__PIECE_HEADER]):
            fields[col.COLUMN_DESERTION_TYPE] = REVIEW_STATUS_ERROR
            fields[col.COLUMN_REVIEW_STATUS] = REVIEW_STATUS_ERROR
            fields[col.COLUMN_RETURN_DATE] = format_to_excel_date(datetime.now()),

        text = text_pieces[self.__PIECE_4]
        fields[col.COLUMN_EXECUTOR] = extract_name(text)
        fields[col.COLUMN_EXPERIENCE] = extract_experience(fields[COLUMN_SERVICE_DAYS])
        fields[col.COLUMN_DESERTION_TERM] = extract_desertion_term(fields)

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
            self.logger.warning('------ ⚠️ Невідповідність дати народження та ІПН! ' + str(record[COLUMN_BIRTHDAY] + '/' + str(record[COLUMN_ID_NUMBER])) + '::' + str(record[COLUMN_NAME]))
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

            if len(person_data) > 100:
                persons.append(person_data)
                self.logger.debug('... 🏃‍♂️ПЕРСОНА: ' + extract_name(person_data))

        return persons

    def _calculate_service_days(self, conscription_date_str, desertion_date_str):
        days = calculate_days_between(conscription_date_str, desertion_date_str)
        if days < 0 or days > 4000:
            self.logger.error(f"--- ⚠️ Нелогічна кількість днів служби: {days}. Перевірте дати.")
            return 0
        return days


    def check_for_errors(self, data_for_excel) -> list[str]:
        result = []
        if not data_for_excel:
            return result

        for data_dict in data_for_excel:
            for col_name, value in data_dict.items():
                if value == NA:
                    error = 'КОЛОНКА ' + col_name + ' ПОРОЖНЯ!'
                    result.append(error)
                    self.logger.warning('------ ⚠️ ' + error)
        return result

    def _check_return_sign(self, text):
        for pattern in PATTERN_RETURN_SIGN:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug('--- ✌️ ВИЯВЛЕНО ПОВЕРНЕННЯ! УРА')
                return True
        return False

    def _check_error_sign(self, text):
        for pattern in PATTERN_ERROR_SIGN:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug('--- ☝️ ВИЯВЛЕНО ПОМИЛКОВЕ ПОВІДОМЛЕННЯ')
                return True
        return False

    def get_best_match(self, ml_val, regex_val):
        ml_str = str(ml_val or "").strip()
        regex_str = str(regex_val or "").strip()
        return ml_str if len(ml_str) >= len(regex_str) else regex_str