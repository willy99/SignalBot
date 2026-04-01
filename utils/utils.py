import datetime
import re
from datetime import timedelta
from datetime import datetime, date
import config
import os
from typing import Any, Tuple, Dict
from dics.deserter_xls_dic import NA
from domain.person_key import PersonKey
from service.constants import DB_DATE_FORMAT


def clean_text(text):
    if text is None: return None
    result = " ".join(text.split())
    result = result.replace('ʼ', '\'').replace('’','\'')
    return result

def get_effective_date():
    """Визначає 'робочу' дату з урахуванням години переходу."""
    now = datetime.now()

    # Якщо зараз вечір (наприклад, після 16:00), файли йдуть у папку наступного дня
    if now.hour >= config.DAY_ROLLOVER_HOUR:
        return now + timedelta(days=1)

    # ОБОВ'ЯЗКОВО повертаємо поточну дату, якщо година менша за ліміт
    return now



def to_html_date(val):
    """Перетворює будь-який вхідний формат дати в YYYY-MM-DD для браузера"""
    if not val:
        return ""

    # 1. Якщо прийшов об'єкт datetime від xlwings
    if isinstance(val, (datetime, date)):
        return val.strftime(DB_DATE_FORMAT)

    # 2. Якщо прийшов рядок (наприклад, з вашого config.EXCEL_DATE_FORMAT)
    try:
        dt = datetime.strptime(str(val).strip(), config.EXCEL_DATE_FORMAT)
        return dt.strftime(DB_DATE_FORMAT)
    except (ValueError, TypeError):
        # 3. Якщо формат невідомий, пробуємо стандартний ISO
        try:
            return datetime.fromisoformat(str(val)).strftime(DB_DATE_FORMAT)
        except:
            return ""

def format_to_excel_date(date_val: Any) -> str:
    """
    Приймає datetime або str.
    Повертає рядок у форматі, визначеному в EXCEL_DATE_FORMAT (напр. 08.02.2026).
    """
    if not date_val or date_val == NA:
        return ""

    # 1. Якщо це вже об'єкт datetime
    if isinstance(date_val, datetime):
        return date_val.strftime(config.EXCEL_DATE_FORMAT)

    # 2. Якщо це рядок
    if isinstance(date_val, str):
        try:
            clean_val = date_val.strip().strip('.')
            parts = clean_val.split('.')

            if len(parts) != 3:
                return date_val  # Повертаємо як є, якщо формат дивний

            # Визначаємо формат року: %Y для 2026, %y для 26
            year_part = parts[2]
            year_fmt = "%Y" if len(year_part) == 4 else "%y"

            # Парсимо в об'єкт datetime
            dt_obj = datetime.strptime(clean_val, f"%d.%m.{year_fmt}")

            # Повертаємо у вашому цільовому форматі з константи
            return dt_obj.strftime(config.EXCEL_DATE_FORMAT)

        except (ValueError, IndexError):
            return date_val

    return str(date_val)

def get_file_name(file_path):
    """
    Повертає ім'я файлу без шляху та без розширення.
    """
    # 1. Отримуємо '06.01.2026 СЗЧ з РВБЗ 1 АЕМР АЕМБ ГАЛАЙКО В.В..doc'
    base_name = os.path.basename(file_path)

    # 2. Відрізаємо розширення (.doc)
    name_without_ext = os.path.splitext(base_name)[0]

    return name_without_ext

def format_ukr_date(date_val) -> str:
    if not date_val or str(date_val).lower() in ["none", "nan", ""]:
        return ""

    # 1. Відсікаємо час, якщо він є
    date_str = str(date_val).split(' ')[0].strip()

    # 2. Пробуємо кожен формат із нашого списку
    for fmt in config.EXCEL_DATE_FORMATS_REPORT:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Як тільки знайшли збіг — повертаємо у вашому улюбленому форматі
            return dt.strftime(config.EXCEL_DATE_FORMAT)
        except ValueError:
            continue

    # 3. Якщо жоден формат не підійшов — повертаємо як було (щоб не втратити дані)
    return date_str

def calculate_days_between(date_from_str, date_to_str):
    # print('>> date from ' + str(date_from_str) + ' to ' + str(date_to_str))
    date_from_str = format_to_excel_date(date_from_str)
    date_to_str = format_to_excel_date(date_to_str)

    if date_from_str == NA or date_to_str == NA:
        return 0
    try:
        def parse_date(d_str):
            return datetime.strptime(d_str, config.EXCEL_DATE_FORMAT)

        dt_start = parse_date(date_from_str)
        dt_end = parse_date(date_to_str)

        delta = dt_end - dt_start
        days = delta.days
        # print('> days ' + str(days))
        return days
    except Exception as e:
        print(str(e))
        return 0

def get_typed_value(value):
        if isinstance(value, str):
            try:
                valid_date = datetime.strptime(value, config.EXCEL_DATE_FORMAT)
                return valid_date
            except ValueError:
                return value
        else:
            return value


def check_birthday_id_number(birthday: datetime, idn: str)-> bool:
    if idn is None or birthday is None or idn == '':
        return True
    # Обчислюємо дату з РНОКПП
    base_date = datetime(1899, 12, 31)
    days_count = int(idn[:5])
    birthday_calculated_dt = base_date + timedelta(days=days_count)
    birthday_calculated = format_ukr_date(birthday_calculated_dt).strip()
    birthday_table = format_ukr_date(birthday).strip() if birthday else None
    if birthday_table != birthday_calculated:
        print('------ ⚠️ Актуальний день народження:' + str(birthday_table) + ' По він коду має бути:' + str(birthday_calculated))
        return False
    return True


def get_strint_fromfloat(value, default = None) -> str:
    try:
        value = str(int(float(value))).strip() if value else ""
    except:
        value = str(value).strip() if value else default
    return value

# 029384902_ІМЯ Прізвище по-батькові_24.02.1979_А0224
def get_person_key_from_str(glued_key: str) -> PersonKey:
    key = PersonKey(rnokpp=None, name=None, des_date=None, mil_unit=None)
    if not glued_key: return key
    spl = glued_key.split("_")
    key.rnokpp = spl[0]
    key.name = spl[1]
    key.des_date = spl[2]
    if len(spl) > 3:
        key.mil_unit = spl[3]
    return key


def to_genitive_title(title: str) -> str:
    """Перетворює військове звання у родовий відмінок (кого/чого)."""
    if not title:
        return ""

    words = title.strip().split()
    res = []

    for w in words:
        lw = w.lower()
        # 1. Специфічні слова та прикметники
        if lw == "старший":
            res.append("старшого" if w.islower() else "Старшого")
        elif lw == "молодший":
            res.append("молодшого" if w.islower() else "Молодшого")
        elif lw == "головний":
            res.append("головного" if w.islower() else "Головного")
        elif lw == "старшина":
            res.append("старшини" if w.islower() else "Старшини")

        # 2. Загальні правила для прикметників (на -ий)
        elif lw.endswith("ий"):
            res.append(w[:-2] + "ого")

        # 3. Загальні правила для іменників жіночого роду (на -а)
        elif lw.endswith("а"):
            res.append(w[:-1] + "и")

        # 4. Найпоширеніше правило: іменник на приголосний (солдат, лейтенант, майор, офіцер)
        # Додаємо "а" в кінці. (Враховує також складені звання на кшталт "штаб-сержант" -> "штаб-сержанта")
        elif lw[-1] in "бвгґджзклмнпрстфхцчшщ":
            res.append(w + "а")

        # 5. Якщо нічого не підійшло (fallback)
        else:
            res.append(w)

    return " ".join(res)

def to_genitive_case(fullname: str) -> str:
    """
    Перетворює ПІБ (Називний) у ПІБ (Родовий відмінок).
    Приклад: "Шевченко Тарас Григорович" -> "Шевченка Тараса Григоровича"
    """
    if not fullname:
        return ""

    fullname = fullname.lower()
    parts = fullname.strip().split()
    if len(parts) != 3:
        return fullname  # Якщо ввели просто "Шевченко Тарас" або 4 слова, повертаємо як є

    surname, first_name, patronymic = parts

    # 1. ВИЗНАЧАЄМО СТАТЬ ЗА ПО БАТЬКОВІ
    gender = 'F' if patronymic.lower().endswith('вна') else 'M'

    # 2. ВІДМІНЮЄМО ПО БАТЬКОВІ (Тут правила залізні)
    if gender == 'M':
        pat_gen = patronymic + 'а'
    else:
        pat_gen = patronymic[:-1] + 'и'  # -вна -> -вни

    # 3. ВІДМІНЮЄМО ІМ'Я
    first_gen = first_name
    if gender == 'M':
        if first_name.endswith(('й', 'ь')):
            first_gen = first_name[:-1] + 'я'  # Андрій -> Андрія, Василь -> Василя
        elif first_name.endswith('о'):
            first_gen = first_name[:-1] + 'а'  # Дмитро -> Дмитра
        elif first_name.endswith('а'):
            first_gen = first_name[:-1] + 'и'  # Микола -> Миколи
        elif first_name.endswith('я'):
            first_gen = first_name[:-1] + 'і'  # Ілля -> Іллі
        else:
            first_gen = first_name + 'а'  # Іван -> Івана (приголосні)
    else:  # Жіночі імена
        if first_name.endswith('ія'):
            first_gen = first_name[:-1] + 'ї'  # Марія -> Марії
        elif first_name.endswith('я'):
            first_gen = first_name[:-1] + 'і'  # Надія -> Надії
        elif first_name.endswith('а'):
            first_gen = first_name[:-1] + 'и'  # Олена -> Олени
        elif first_name.endswith('ь'):
            first_gen = first_name[:-1] + 'і'  # Нінель -> Нінелі

    # 4. ВІДМІНЮЄМО ПРІЗВИЩЕ
    surname = surname.lower()
    if gender == 'M':
        if surname.endswith('ий'):
            sur_gen = surname[:-2] + 'ого'  # Залужний -> Залужного
        elif surname.endswith('ьок'):
                sur_gen = surname[:-3] + 'ька'
        elif surname.endswith('о'):
            sur_gen = surname[:-1] + 'а'  # Шевченко -> Шевченка
        elif surname.endswith(('ь', 'й')):
            sur_gen = surname[:-1] + 'я'  # Коваль -> Коваля, Палій -> Палія
        elif surname.endswith('а'):
            sur_gen = surname[:-1] + 'и'  # Сирота -> Сироти
        elif surname.endswith('я'):
            sur_gen = surname[:-1] + 'і'
        elif surname[-1].lower() not in 'аеєиіїоуюяь':
            sur_gen = surname + 'а'  # Мельник -> Мельника (приголосні)
        else:
            sur_gen = surname
    else:  # Жіночі прізвища
        if surname.endswith(('ська', 'цька')):
            sur_gen = surname[:-2] + 'ої'  # Білецька -> Білецької
        elif surname.endswith(('ова', 'єва', 'іна', 'їна')):
            sur_gen = surname[:-1] + 'ої'  # Іванова -> Іванової (русифіковані)
        elif surname.endswith('а'):
            sur_gen = surname[:-1] + 'и'  # Лелека -> Лелеки
        elif surname.endswith('я'):
            sur_gen = surname[:-1] + 'і'
        else:
            sur_gen = surname
        # Всі інші (на приголосний або 'о') у жінок не відмінюються! (Косач, Шевченко, Фаріон)
    first_gen = first_gen.capitalize()
    pat_gen = pat_gen.capitalize()
    sur_gen = sur_gen.upper()

    return f"{sur_gen} {first_gen} {pat_gen}"


def get_year_safe(date_val) -> str:
    if not date_val:
        return None

    # Якщо це справжній об'єкт дати (datetime або date)
    if isinstance(date_val, (datetime, date)):
        return str(date_val.year)

    # Якщо це рядок (або щось інше, що можна перетворити на рядок)
    date_str = str(date_val).strip()
    if len(date_str) >= 4:
        # Варіант 1: Формат ДД.ММ.РРРР (рік в кінці)
        if date_str[-4:].isdigit():
            return date_str[-4:]
        # Варіант 2: Формат РРРР-ММ-ДД (рік на початку)
        elif date_str[:4].isdigit():
            return date_str[:4]

    return None


# ---------------------------------------------------------------------------
# Нормалізація ПІБ до називного відмінка
# ---------------------------------------------------------------------------

_UKR_VOWELS = set('аеєиіїоуюя')

# Паттерн для прізвищ на -ко/-го/-хо (Шевченко, Петренко, Бойченко...)
# Генітив таких прізвищ: Шевченка → стем Шевченк, де кінець [нрлм...ь][кгх]
_SURNAME_NEEDS_O = re.compile(r'(?:[нрлмстдзжшч]|ь)[кгх]$')


def _count_trailing_consonants(s: str) -> int:
    """Кількість приголосних наприкінці рядка до першої голосної."""
    n = 0
    for ch in reversed(s.lower()):
        if ch in _UKR_VOWELS:
            break
        n += 1
    return n


def _needs_o_first_name(stem: str) -> bool:
    """
    True якщо стем імені мабуть походить від імені на -о (Дмитро, Петро, Павло).
    Ознака: рівно 2 приголосні на кінці, остання — р або л.
    """
    s = stem.lower()
    return _count_trailing_consonants(s) == 2 and s[-1] in 'рл'


def _first_to_nom(name: str, gender: str, case: str) -> str:
    """Перетворює ім'я з відмінка у називний."""
    n = name.lower()
    if gender == 'M':
        if case == 'instr':
            if n.endswith('ієм'):  return name[:-3] + 'ій'          # Андрієм → Андрій
            if n.endswith('єм'):   return name[:-2] + 'й'
            if n.endswith('ем'):
                stem = name[:-2]
                return stem + 'ь' if stem.lower().endswith('л') else stem  # Василем → Василь
            if n.endswith('ом'):
                stem = name[:-2]
                return stem + 'о' if _needs_o_first_name(stem) else stem   # Дмитром → Дмитро
        elif case == 'gen':
            if n.endswith('ія'):   return name[:-2] + 'ій'
            if n.endswith('я'):    return name[:-1] + 'й'            # Андрія → Андрій
            if n.endswith('а'):
                stem = name[:-1]
                return stem + 'о' if _needs_o_first_name(stem) else stem   # Дмитра → Дмитро
            if n.endswith('и'):    return name[:-1] + 'а'            # Миколи → Микола
            if n.endswith('і'):    return name[:-1] + 'я'            # Іллі → Ілля
        elif case == 'dat':
            if n.endswith('ієві'): return name[:-4] + 'ій'
            if n.endswith('еві'):  return name[:-3]                  # Ігореві → Ігор
            if n.endswith('ові'):  return name[:-3]
            if n.endswith('ю'):    return name[:-1] + 'й'            # Андрію → Андрій
            if n.endswith('у'):
                stem = name[:-1]
                return stem + 'о' if _needs_o_first_name(stem) else stem
    elif gender == 'F':
        if case == 'instr':
            if n.endswith('єю'): return name[:-2] + 'я'             # Надією → Надія
            if n.endswith('ою'): return name[:-2] + 'а'             # Оленою → Олена
        elif case in ('gen', 'dat'):
            if n.endswith('ії'): return name[:-2] + 'ія'            # Марії → Марія
            if n.endswith('и'):  return name[:-1] + 'а'             # Олени → Олена
            if n.endswith('і'):  return name[:-1] + 'а'             # Олені → Олена
    return name


def _sur_to_nom(surname: str, gender: str, case: str) -> str:
    """Перетворює прізвище з відмінка у називний."""
    s = surname.lower()

    # Невідмінювані на -о (Шевченко, Черненко) — але деякі автори все ж відмінюють!
    # Тому перевіряємо ДО загальної перевірки на -о
    if gender == 'M':
        if case == 'instr':
            if s.endswith('им'):  return surname[:-2] + 'ий'         # Залужним → Залужний
            if s.endswith('ім'):  return surname[:-2] + 'ій'
            if s.endswith('ем'):
                stem = surname[:-2]
                return stem + 'ь' if stem.lower().endswith('л') else stem  # Ковалем → Коваль
            if s.endswith('ом'):
                stem_om = surname[:-2]
                # Прізвища на -ко/-го/-хо в орудному: Петренком → Петренко (видаляємо тільки м)
                if _SURNAME_NEEDS_O.search(stem_om.lower()):
                    return surname[:-1]    # Петренком → Петренко
                return stem_om             # Мельником → Мельник
        elif case == 'gen':
            if s.endswith('ого'): return surname[:-3] + 'ий'         # Залужного → Залужний
            if s.endswith('я'):   return surname[:-1] + 'ь'          # Коваля → Коваль
            if s.endswith('а'):
                stem = surname[:-1]
                return stem + 'о' if _SURNAME_NEEDS_O.search(stem.lower()) else stem
        elif case == 'dat':
            if s.endswith('ому'): return surname[:-3] + 'ий'
            if s.endswith('ові'): return surname[:-3]
            if s.endswith('еві'):
                stem = surname[:-3]
                return stem + 'ь' if stem.lower().endswith('л') else stem
            if s.endswith('у'):
                stem = surname[:-1]
                # Прізвища на -ко/-го/-хо у давальному: Іванченку → Іванченко
                return stem + 'о' if _SURNAME_NEEDS_O.search(stem.lower()) else stem
    elif gender == 'F':
        if case == 'instr':
            if s.endswith('ою'): return surname[:-2] + 'а'           # Сиротою → Сирота
            if s.endswith('єю'): return surname[:-2] + 'я'
        elif case in ('gen', 'dat'):
            if s.endswith('ої'): return surname[:-2] + 'а'           # Білецької → Білецька
            if s.endswith('ій'): return surname[:-2] + 'а'
            if s.endswith('и'):  return surname[:-1] + 'а'
            if s.endswith('і'):  return surname[:-1] + 'а'

    # Невідмінювані: -о (Шевченко) та -их/-іх (Білих)
    if s.endswith('о') or re.search(r'[иі]х$', s):
        return surname

    return surname


def to_nominative_case(fullname: str) -> str:
    """
    Перетворює ПІБ з будь-якого відмінка у називний.
    Визначає відмінок і стать за по-батькові — найнадійнішим індикатором.

    Приклади:
        "Черненко Олександром Вікторовичем" → "Черненко Олександр Вікторович"
        "Мельника Віталія Михайловича"       → "Мельник Віталій Михайлович"
        "Коваля Василя Павловича"            → "Коваль Василь Павлович"
        "Залужного Олексія Сергійовича"      → "Залужний Олексій Сергійович"
    """
    if not fullname:
        return fullname
    parts = fullname.strip().split()
    if len(parts) != 3:
        return fullname

    surname, first_name, patronymic = parts
    p = patronymic.lower()

    # --- Визначаємо стать та відмінок за по-батькові ---
    m_match = re.match(r'^(.+?(?:ович|евич|євич))(а|у|ем|ові|еві)?$', p)
    f_match = re.match(r'^(.+вн)(а|и|і|ою)$', p)

    if m_match:
        gender  = 'M'
        pat_nom = patronymic[:len(m_match.group(1))]  # обрізаємо відмінкове закінчення
        suffix  = (m_match.group(2) or '').lower()
        case    = {'': 'nom', 'а': 'gen', 'у': 'dat', 'ем': 'instr',
                   'ові': 'dat', 'еві': 'dat'}.get(suffix, 'nom')
    elif f_match:
        gender  = 'F'
        stem    = patronymic[:len(f_match.group(1))]
        suffix  = f_match.group(2).lower()
        case    = {'а': 'nom', 'и': 'gen', 'і': 'dat', 'ою': 'instr'}.get(suffix, 'nom')
        pat_nom = stem + 'а'
    else:
        return fullname  # не вдалося розпізнати по-батькові

    if case == 'nom':
        return fullname  # вже у називному

    first_nom = _first_to_nom(first_name, gender, case)
    sur_nom   = _sur_to_nom(surname, gender, case)

    def recase(orig: str, result: str) -> str:
        """Відновлює регістр відповідно до оригіналу (CAPS → CAPS, Title → Title)."""
        if not result:
            return result
        if orig.isupper():
            return result.upper()
        return result[0].upper() + result[1:]

    return f"{recase(surname, sur_nom)} {recase(first_name, first_nom)} {recase(patronymic, pat_nom)}"


def sanitize_filename(self, filename: str) -> str:
    """Очищує ім'я файлу від спроб виходу за межі директорії."""
    if not filename:
        return "unnamed_attachment"

    # 1. Беремо тільки фінальну частину імені (ігноруємо будь-які шляхи / або \)
    safe_name = os.path.basename(filename)

    # 2. Видаляємо підозрілі послідовності точок
    safe_name = safe_name.replace('..', '')

    # 3. Видаляємо пробіли та зайві символи на початку/в кінці
    safe_name = safe_name.strip()

    # 4. Fallback, якщо після очищення нічого не залишилось
    return safe_name if safe_name else "safe_attachment"
