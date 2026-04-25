from dics.deserter_xls_dic import *
import re
from datetime import datetime
from utils.utils import format_to_excel_date, to_nominative_case


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


def _build_title_strip_re():
    """
    Будує regex для видалення військових звань з початку рядка.
    Ітерує по КЛЮЧАХ PATTERN_TITLE_MAPPING (не по values!), щоб охопити
    всі словоформи: 'рядовим', 'солдатом', 'військовослужбовцями' etc.
    """

    def clean_key(k: str) -> str:
        c = k.replace('(?i)', '')
        # Відрізаємо кінцевий службовий символьний клас [\b,.\s]
        last_bracket = c.rfind('[')
        if last_bracket != -1:
            tail = c[last_bracket:]
            # Якщо це НЕ кирилиця в дужках — це службовий клас, прибираємо
            if 'б' not in tail and 'я' not in tail and 'і' not in tail:
                c = c[:last_bracket]
        return c.rstrip()

    parts = sorted(
        [clean_key(k) for k in PATTERN_TITLE_MAPPING.keys()],
        key=len, reverse=True
    )
    return re.compile(r'^\s*(?:' + '|'.join(parts) + r')\s*', re.IGNORECASE)


_TITLE_STRIP_RE_V2 = _build_title_strip_re()
_LEADING_NOISE_RE = re.compile(r'^(?:[а-яґєіїʼ\'-]+\s+)+', re.IGNORECASE)
_CLEAN_SURNAME_RE = re.compile(r"^[А-ЯҐЄІЇа-яґєії'ʼ-]{2,}$")
_NAME_WITH_CASE_RE = re.compile(PATTERN_NAME_WITH_CASE)


def extract_name_lowercased(text: str) -> str:
    """
    Витягує ПІБ з тексту кримінального провадження.
    Підтримує будь-який регістр прізвища (CAPS або звичайний).
    Повертає ПІБ у тому відмінку, в якому воно зустрічається в тексті
    (нормалізацію до називного робить to_nominative_case у виклику).

    Алгоритм очищення group(1):
      1. Спочатку прибираємо шумові слова з малої літери ('призовом', 'зокрема' etc)
      2. Потім прибираємо звання через ключі PATTERN_TITLE_MAPPING
         (охоплює всі словоформи: рядовим, солдатом, прапорщик, військовослужбовцями)
      3. Якщо залишилось чисте прізвище → повертаємо
      4. Fallback: беремо останнє слово group(1) або group(3) як прізвище
    """
    m = _NAME_WITH_CASE_RE.search(text)
    if not m:
        return NA

    raw_g1 = m.group(1).strip()
    first_name = m.group(3).strip()
    patronymic = m.group(4).strip()

    # Порядок важливий: спочатку шум, потім звання
    stripped = _LEADING_NOISE_RE.sub('', raw_g1).strip()
    stripped = _TITLE_STRIP_RE_V2.sub('', stripped).strip()

    if stripped and _CLEAN_SURNAME_RE.match(stripped):
        return f'{stripped} {first_name} {patronymic}'.strip()

    # Fallback: остання заглавна частина group(1) є прізвищем
    last_word = raw_g1.rsplit(None, 1)[-1] if raw_g1 else ''
    if last_word and last_word[0].isupper():
        return f'{last_word} {first_name} {patronymic}'.strip()

    # Fallback 2: group(1) — тільки шум, прізвище у group(3)
    parts = patronymic.split(None, 1)
    fn = parts[0] if parts else ''
    pat = parts[1] if len(parts) > 1 else ''
    return to_nominative_case(f'{first_name} {fn} {pat}'.strip() or NA)


def extract_erdr(text: str) -> tuple[str, str]:
    """Витягує номер та дату ЄРДР. Повертає (number, date) або (NA, NA)."""
    if not text or not str(text).strip():
        return NA, NA
    match = re.compile(PATTERN_ERDR, re.IGNORECASE).search(str(text))
    if match:
        return match.group(1), format_to_excel_date(match.group(2))
    return NA, NA

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
    if part == 'лейтенант' or 'майор' in canonical_title or 'капітан' in canonical_title:
        part = 'офіцер'
    if 'сержант' in canonical_title:
        part = 'сержант'
    if 'матрос' in canonical_title or 'старшина' in canonical_title or 'прапорщик' in canonical_title:
        part = 'солдат'
    return part


def extract_mil_unit(text):
    UNIT_ALIASES = {
        'А7019': 'А7018',
        'А7017': 'А7018'
    }
    matches = re.findall(PATTERN_MIL_UNIT, text)

    if not matches:
        return NA

    # 1. Спершу перевіряємо, чи є в тексті "прикомандировані" частини (7018, 7019 тощо)
    # Ми робимо це пріоритетом, бо А0224 буде в кожному документі як отримувач
    for m in matches:
        unit = m.upper()

        # Якщо частина є в списку аліасів (7019 -> 7018)
        if unit in UNIT_ALIASES:
            return UNIT_ALIASES[unit]

        # Якщо це безпосередньо 7018
        if unit == 'А7018':
            return unit

    # 2. Якщо частин 701x не знайдено, повертаємо першу ліпшу (наприклад, А0224)
    return matches[0].upper()

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

    # Шукаємо дати після слова "призваний/направлений"
    lookback_area = text[start_match.start():]
    raw_dates = re.findall(PATTERN_DATE, lookback_area)

    if not raw_dates:
        return NA

    parsed_dates = []
    for rd in raw_dates:
        date_str = rd[0] if isinstance(rd, tuple) else rd
        year_match = re.search(r'\d{4}', date_str)
        if year_match:
            parsed_dates.append((date_str, int(year_match.group(0))))

    # Якщо раптом жодна дата не містить 4-значного року, повертаємо першу
    if not parsed_dates:
        first_date = raw_dates[0][0] if isinstance(raw_dates[0], tuple) else raw_dates[0]
        return format_to_excel_date(first_date)

    # Знаходимо найменший та найбільший рік у знайдених датах
    min_year = min(year for _, year in parsed_dates)
    max_year = max(year for _, year in parsed_dates)

    # Мінімальний вік призову (18 років)
    MIN_AGE = 18

    valid_conscription_dates = []

    # Перевіряємо, чи є в тексті дата народження (розкид між найменшою і найбільшою датою >= 18 років)
    has_dob_in_list = (max_year - min_year) >= MIN_AGE

    for date_str, year in parsed_dates:
        if has_dob_in_list:
            # Якщо дата народження є, беремо тільки ті дати, що на 18+ років більші за найменшу
            if year - min_year >= MIN_AGE:
                valid_conscription_dates.append(date_str)
        else:
            # Якщо розкид дат малий (наприклад, 2022 і 2024), значить дати народження тут немає
            valid_conscription_dates.append(date_str)

    if valid_conscription_dates:
        # Перша ж "доросла" дата після слова "призваний" є нашою ціллю
        return format_to_excel_date(valid_conscription_dates[0])

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
    desertion_place = extract_desertion_place(text)
    if desertion_place:
        if 'ППД' == desertion_place:
            return 'Миколаївська область'
        if 'НЦ' == desertion_place:
            return 'Житомирська область'
    return NA


def extract_military_subunit(text, file_name=None, mapping=PATTERN_SUBUNIT_MAPPING):
    """
    Витягує назву підрозділу.
    Пріоритет 1: Пошук у тексті (найбільш точний).
    Пріоритет 2: Пошук у назві файлу (якщо в тексті нічого немає).
    """

    # =========================================================================
    # ЕТАП 1: Пошук у ТЕКСТІ (Найвищий пріоритет)
    # =========================================================================
    if text:
        for pattern, abbreviation in mapping.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Якщо в абревіатурі є маркер \1 (наприклад, для номера батальйону)
                if r'\1' in abbreviation:
                    # Безпечне отримання групи (якщо група не знайшлася, беремо порожній рядок)
                    digit = match.group(1) if match.groups() and match.group(1) else ""
                    res = abbreviation.replace(r'\1', digit).strip()
                else:
                    res = abbreviation
                return res

    # =========================================================================
    # ЕТАП 2: Пошук у НАЗВІ ФАЙЛУ (Запасний варіант)
    # =========================================================================
    if file_name:
        short_values = set()
        for val in mapping.values():
            clean_val = val.replace(r'\1', '').strip()
            if clean_val:
                short_values.add(clean_val)

        # Сортуємо від найдовших до найкоротших, щоб спочатку ловити специфічні назви
        sorted_shorts = sorted(short_values, key=len, reverse=True)

        for short_val in sorted_shorts:
            # Паттерн шукає без урахування регістру (re.IGNORECASE)
            # Шукаємо: (Початок рядка АБО пробіл/підкреслення) + (Опціонально цифри та пробіли/підкреслення) + Назва
            pattern = rf'(?:^|[\s_])(\d*[\s_]*)?{re.escape(short_val)}(?=[\s_]|$)'
            match = re.search(pattern, file_name, re.IGNORECASE)

            if match:
                # Отримуємо цифри перед назвою (наприклад, "3" з "3 САДН")
                prefix = match.group(1) or ""
                digits = re.sub(r'\D', '', prefix)  # Залишаємо тільки цифри

                # Формуємо результат: цифри + пробіл + значення з мапінгу (short_val)
                if digits:
                    return f"{digits} {short_val}"
                return short_val

    # =========================================================================
    # ЕТАП 3: Якщо нічого не знайдено
    # =========================================================================
    return NA

def extract_desertion_place(text, file_name=None):
    sorted_patterns = sorted(
        PATTERN_DESERTION_PLACE_MAPPING.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )

    for pattern, short_name in sorted_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return short_name

    if file_name:
        for pattern, mapping_value in sorted_patterns:
            if re.search(mapping_value, file_name, re.IGNORECASE):
                return mapping_value

    return NA

def extract_desertion_type(text, desertion_where):
    des_type = DEFAULT_DESERTION_TYPE
    for pattern, short_name in PATTERN_DESERTION_TYPE_MAPPING.items():
        if re.search(pattern, text, re.IGNORECASE):
            return short_name
    if desertion_where == 'НЦ':
        des_type = DEFAULT_DESERTION_TYPE_FOR_EDU_CENTER
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

