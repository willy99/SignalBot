from dics.deserter_xls_dic import *
import re
from datetime import datetime
from utils.utils import format_to_excel_date


def extract_locality(conditions: str) -> str:
    if not conditions or conditions == NA:
        return NA
    match = re.search(PATTERN_LOCALITY, conditions)
    if match:
        return match.group(1)
    return NA

def extract_region(tck_text: str) -> str:
    if not tck_text or tck_text == NA:
        return NA
    for pattern, region_name in PATTERN_REGION:
        if re.search(pattern, tck_text):
            return region_name
    return NA


def extract_name(text):
    match = re.search(PATTERN_NAME, text)
    if match:
        return f"{match.group(1)} {match.group(3)} {match.group(4)}".strip()
    return NA


def extract_title(text):
    # Проходимо по мапінгу (важливо: довгі назви мають бути вище коротких)
    for pattern, canonical_name in PATTERN_TITLE_MAPPING.items():
        if re.search(pattern, text, re.IGNORECASE):
            return canonical_name
    return NA

def extract_title_2(canonical_title):
    if canonical_title is None: return NA
    parts = canonical_title.split()
    part = parts[-1] if parts else NA
    if part == 'лейтенант':
        part = 'офіцер'
    return part

def extract_mil_unit(text):
    match = re.search(PATTERN_MIL_UNIT, text)
    if match:
        return match.group(0).upper()
    return NA


def extract_bio(text, full_name):
    if not full_name or full_name == NA:
        return text
    start_index = text.find(full_name)
    if start_index != -1:
        return text[start_index:].strip()

    return text

def extract_id_number(text):
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

def extract_phone(text):
    match = re.search(PATTERN_PHONE, text, re.IGNORECASE)

    if match:
        raw_phone = match.group(2)
        digits = re.sub(r'\D', '', raw_phone)
        if len(digits) >= 10:
            return digits[-10:]
    return NA

def extract_service_type(text):
    for pattern, result in PATTERN_SERVICE_TYPE_MAPPING.items():
        if re.search(pattern, text, re.IGNORECASE):
            return result
    return DEFAULT_SERVICE_TYPE # default


def extract_conscription_date(text):
    start_match = re.search(PATTERN_RTZK_CALLED, text)
    if start_match is None:
        return NA

    lookback_area = text[start_match.start():-1]
    # 2. Шукаємо всі дати в цій зоні
    dates = re.findall(PATTERN_DATE, lookback_area)
    if dates:
        found_date = dates[0]
        return format_to_excel_date(found_date)

    return NA

def extract_birthday(text):
    match = re.search(PATTERN_BIRTHDAY, text, re.IGNORECASE)

    if match:
        date_str = match.group(1).strip()
        return format_to_excel_date(date_str)

    backup_pattern = PATTERN_BIRTHDAY_FALLBACK
    all_dates = re.findall(backup_pattern, text)
    if all_dates:
        return format_to_excel_date(all_dates[0])

    return NA

def extract_address(text):
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

def extract_rtzk(text: str) -> str:
    match = re.search(PATTERN_RTZK, text)
    if not match:
        return NA

    res = match.group(1).strip()
    for p in PATTERN_RTZK_TRASH:
        res = re.sub(p, '', res)

    res = res.rstrip('., ')

    res = re.sub(r'(?i)ЦТК', 'ТЦК', res)
    res = " ".join(res.split())

    return res

def extract_desertion_date(text):
    match = re.search(PATTERN_DESERTION_DATE, text, re.IGNORECASE)

    if match:
        return format_to_excel_date(match.group(1))
    fallback = re.search(PATTERN_DATE, text)
    if fallback:
        return format_to_excel_date(fallback.group(1))

    return NA

def extract_desert_conditions(text):
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

def extract_return_date(text):
    clean_txt = re.sub(r'\s+', ' ', text).lower()

    match = re.search(PATTERN_RETURN_MARKERS, clean_txt, re.IGNORECASE)
    if not match:
        return None

    match = re.search(PATTERN_RETURN_DATE, text, re.IGNORECASE)
    if match:
        return format_to_excel_date(match.group(1))

    fallback_with_presence = extract_desertion_date(text)
    return fallback_with_presence

def extract_desertion_region(text):
    # Навчальний центр - одразу житомір!
    if re.search("з НЦ", text, re.IGNORECASE) and len(text) < 100:
        return "Житомирська область"

    match = re.search(PATTERN_DESERTION_REGION_MAIN, text, re.DOTALL)
    desertion_place = None
    if match:
        full_address = " ".join(match.group(1).split())
        desertion_place = full_address.strip().rstrip('.')

    if not desertion_place:
        backup_match = re.search(PATTERN_DESERTION_REGION_BACKUP, text)
        if backup_match:
            desertion_place = " ".join(backup_match.group(1).split())
    if not desertion_place: # fallback for the whole string
        desertion_place = text

    if desertion_place:
        return extract_region(desertion_place)
    return NA



def extract_military_subunit(text, file_name=None, mapping=PATTERN_SUBUNIT_MAPPING):
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


def extract_desertion_place(text, file_name=None):
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

def extract_desertion_type(text, desertion_where):
    des_type = 'СЗЧ'
    for pattern, short_name in PATTERN_DESERTION_TYPE_MAPPING.items():
        if re.search(pattern, text, re.IGNORECASE):
            return short_name
    if desertion_where == 'НЦ':
        des_type = 'СЗЧ з А2900'
    return des_type

def extract_cc_article(desertion_type):
    if desertion_type == 'СЗЧ зброя':
        return "429"
    if desertion_type == 'відмова':
        return "402"
    return "407"

def extract_experience(days: int):
    if days > EXPERIENCED_MORE_THAN_DAYS:
        return 'experienced'
    return 'newcomer'

def extract_desertion_term(fields):
    ret_date_str = fields.get(COLUMN_RETURN_DATE)
    des_date_str = fields.get(COLUMN_DESERTION_DATE)
    if not ret_date_str or not des_date_str:
        return 'більше 3 діб'
    try:
        ret_date = datetime.strptime(str(ret_date_str).strip(), '%d.%m.%Y').date()
        des_date = datetime.strptime(str(des_date_str).strip(), '%d.%m.%Y').date()
        days_between = (ret_date - des_date).days
        return 'до 3 діб' if days_between <= 3 else 'більше 3 діб'
    except ValueError:
        return 'більше 3 діб'

