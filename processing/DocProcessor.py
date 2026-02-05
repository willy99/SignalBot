from pathlib import Path
from .parsers.ParserFactory import ParserFactory
import config
from utils.utils import format_to_excel_date, get_file_name, clean_text
import dics.deserter_xls_dic as col
from dics.deserter_xls_dic import *
from datetime import datetime
import re

class DocProcessor:

    PIECE_HEADER = 'header'
    PIECE_1 = 'piece 1'
    PIECE_2 = 'piece 2'
    PIECE_3 = 'piece 3'
    PIECE_4 = 'piece 4'

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
        doc_pieces[self.PIECE_HEADER] = self.engine.extract_text_between(PATTERN_PIECE_HEADER_START, PATTERN_PIECE_HEADER_END, True)
        doc_pieces[self.PIECE_1] = self.engine.extract_text_between(PATTERN_PIECE_1_START, PATTERN_PIECE_1_END, True)
        doc_pieces[self.PIECE_4] = self.engine.extract_text_between(PATTERN_PIECE_4_START, PATTERN_PIECE_4_END, True)

        print('>>>header :' + str(doc_pieces[self.PIECE_HEADER]))
        print('>>>1 :' + str(doc_pieces[self.PIECE_1]))
        print('>>>4 :' + str(doc_pieces[self.PIECE_4]))

        raw_piece_3 = self.engine.extract_text_between(PATTERN_PIECE_3_START, PATTERN_PIECE_3_END, True) or ""
        # Нарізаємо на окремих людей
        persons = self.cut_into_person(raw_piece_3)
        all_final_records = []
        for person_text in persons:
            # Робимо копію структури для конкретної людини
            individual_pieces = doc_pieces.copy()
            individual_pieces[self.PIECE_3] = person_text

            # Обробляємо поля (ПІБ, РНОКПП тощо)
            processed_data = self.process_fields(individual_pieces)

            # extend додає елементи списку до загального списку, а не сам список
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

        text = text_pieces[self.PIECE_HEADER]
        if text is not None:
            fields[col.COLUMN_MIL_UNIT] = self._extract_mil_unit(text)

        text = text_pieces[self.PIECE_1]
        if text is not None:
            # Приклад наповнення результатів після аналізу тексту
            fields[col.COLUMN_DESERTION_DATE] = self._extract_desertion_date(text)
            fields[col.COLUMN_DESERTION_REGION] = self._extract_desertion_region(clean_text(text))
            fields[col.COLUMN_DESERT_CONDITIONS] = self._extract_desert_conditions(text)
            fields[col.COLUMN_DESERTION_PLACE] = self._extract_desertion_place(clean_text(text), get_file_name(self.file_path))
            fields[col.COLUMN_RETURN_DATE] = self._extract_return_date(text)

        text = text_pieces[self.PIECE_3]
        if text is not None:
            # Приклад наповнення результатів після аналізу тексту
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

        text = text_pieces[self.PIECE_4]
        fields[col.COLUMN_EXECUTOR] = self._extract_name(text)
        result.append(fields)
        return result


    def validatePieces(self, doc_pieces):
        if doc_pieces[self.PIECE_HEADER] is None:
            raise ValueError(f"❌ Частина з довідкою не витягнуто")
        if doc_pieces[self.PIECE_1] is None:
            raise ValueError(f"❌ Частина 1 не витягнуто!")
        if doc_pieces[self.PIECE_3] is None:
            raise ValueError(f"❌ Частина 3 не витягнуто!")
        if doc_pieces[self.PIECE_4] is None:
            raise ValueError(f"❌ Частина 4 не витягнуто!")


    def cut_into_person(self, doc_piece_3):
        """
        Розрізає блок тексту на окремих осіб за паттерном ПІБ (КАПСОМ).
        Повертає масив рядків, де кожен рядок — це дані однієї особи.
        """
        # print('>>> search persons in:' + doc_piece_3)
        if not doc_piece_3:
            return []

        # Знаходимо всі ПІБ, що стоять на початку рядків
        matches = list(re.finditer(STRICT_NAME_PATTERN, doc_piece_3, re.MULTILINE))

        if not matches:
            # Якщо жодного ПІБ капсом не знайдено, повертаємо весь текст як одну особу
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
        """
        Повертає частину тексту, починаючи з ПІБ.
        Оскільки текст вичищений, використовуємо прямий пошук.
        """
        if not full_name or full_name == NA:
            return text

        # Знаходимо позицію, де починається ПІБ
        start_index = text.find(full_name)

        # Якщо знайшли — ріжемо, якщо ні — повертаємо як є
        if start_index != -1:
            return text[start_index:].strip()

        return text

    def _extract_name(self, text):
        # беремо саме ПЕРШИЙ знайдений ПІБ у тексті

        match = re.search(NAME_PATTERN, text)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"
        return NA

    def _extract_title(self, text):
        """
        Шукає військове звання зі списку ключових слів.
        """

        # Створюємо regex з переліку звань
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
        # 1. Шукаємо ключове слово та результат після нього
        # Додаємо перевірку на текст "не надано", "відсутній" тощо
        marker_pattern = r'(?i)(?:РНОКПП|ІПН|І\.П\.Н\.|РНОК\s*ПП)'

        # Шукаємо позицію маркера
        marker_match = re.search(marker_pattern, text)

        if marker_match:
            # Беремо шматок тексту після маркера (приблизно 30 символів)
            after_marker = text[marker_match.end():marker_match.end() + 30]

            # Якщо відразу після маркера бачимо слова про відсутність — повертаємо NA
            if re.search(r'(?i)(відсутн|не надано|немає|відомості)', after_marker):
                return NA

            # Якщо слова про відсутність немає, шукаємо 10 цифр
            digits_match = re.search(r'(\d{10})\b', after_marker)
            if digits_match:
                return digits_match.group(1)

        # 2. Резервний пошук (тільки якщо маркера взагалі немає в тексті)
        # Шукаємо 10 цифр, які НЕ починаються на '0' (номери телефонів)
        # [1-9] гарантує, що ми не візьмемо мобільний номер 068... чи 093...
        standalone_digits = re.findall(r'\b([1-9]\d{9})\b', text)

        return standalone_digits[0] if standalone_digits else NA

    def _extract_phone(self, text):
        """
        Шукає номер телефону та приводить його до формату 0991141111.
        """
        # Шукаємо цифри, що йдуть після слова "номер" або "телефону"
        # Паттерн охоплює +38, 8, дужки та дефіси
        pattern = r'(?:номер|тел)[\s\w.:]*(\+?3?8?[\s(-]*0\d{2}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2})\b'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            raw_phone = match.group(1)
            # Очищаємо від усього, крім цифр
            digits = re.sub(r'\D', '', raw_phone)
            # Приводимо до формату 0XXXXXXXXX (останні 10 цифр)
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
        """
        Витягує дату народження з підтримкою різних форматів пробілів та скорочень.
        """
        # 1. Використовуємо \s+ (один або більше пробілів будь-якого типу)
        # 2. Додаємо підтримку можливого слова "від" (іноді пишуть "06.02.1975 р. від народження")
        pattern = r'(\d{2}\.\d{2}\.\d{4})\s*(?:року\s+народження|р\.н\.|народження)'

        # Використовуємо re.search з ігноруванням регістру
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            date_str = match.group(1).strip()
            return format_to_excel_date(date_str)

        # Резервний пошук: якщо "року народження" немає, але є формат дати поруч із ПІБ
        # (допомагає, якщо заголовок блоку вже відрізав ключові слова)
        backup_pattern = r'\b(\d{2}\.\d{2}\.\d{4})\b'
        # Шукаємо всі дати і беремо першу, яка зазвичай є датою народження у цьому блоці
        all_dates = re.findall(backup_pattern, text)
        if all_dates:
            return format_to_excel_date(all_dates[0])

        return NA

    def _extract_address(self, text):
        # 1. Знаходимо маркер
        print('text = ' + text)
        marker = "Адреса проживання"
        match_marker = re.search(re.escape(marker), text, re.IGNORECASE)
        if not match_marker:
            return NA

        # Беремо все ПІСЛЯ маркера
        address_part = text[match_marker.end():].strip()

        # Видаляємо "військовослужбовця" та двокрапку
        address_part = re.sub(r'^(?:\s*військовослужбовця)?\s*:?\s*', '', address_part, flags=re.IGNORECASE)
        print('>>>> address part: ' + address_part)

        # 2. ПАТТЕРН: беремо все до першого ";" або "\n"
        # [^;\n]+ — шукає будь-які символи, окрім крапки з комою та переносу рядка
        pattern = r'^((?:(?!Близькі родичі|;|\n).)+)'

        match = re.search(pattern, address_part, re.IGNORECASE | re.DOTALL)

        if match:
            address = match.group(1).strip()
            # Фінальна чистка від зайвих пробілів та крапок у кінці
            return " ".join(address.split()).strip(':;,. ')

        return NA

    def _extract_rtzk(self, text):
        # 1. Покращений паттерн: додаємо підтримку складних назв міст
        pattern = r'(?i)((?:[А-ЯҐЄІЇ][^.,!?\s]*\s+){1,5}?(?:РТЦК|ТЦК|МТЦК)(?:\s*(?:та|&)?\s*СП)?(?:\s+м\.\s+[А-ЯІЇЄа-яіїє\-\']+(?:\s+[А-ЯІЇЄа-яіїє\-\']+)*|\s+[А-ЯІЇЄа-яіїє\']+\s+обл\.?)?)'

        match = re.search(pattern, text)
        if match:
            res = match.group(1).strip()

            # 2. Очищення. ПЕРШИМ ділом видаляємо дату, але ОБЕРЕЖНО
            # Видаляємо тільки саму дату, не чіпаючи текст ПЕРЕД нею
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

            # 3. Фінальна чистка
            # join(split()) прибере зайві пробіли, якщо дата була всередині
            final_res = " ".join(res.split()).strip(':;,. ')

            # Видаляємо залишки фраз, якщо вони стали на початку після чистки
            final_res = re.sub(r'(?i)^(на військову службу|призваний)\s+', '', final_res)

            return final_res if final_res else NA

        return NA

    def _extract_desertion_date(self, text):
        """
        Шукає дату, пов'язану з моментом зникнення (під час перевірки або залишення).
        """
        # Шукаємо дату ДД.ММ.РРРР, яка стоїть перед описом відсутності
        pattern = r'(\d{2}\.\d{2}\.\d{4})(?=\s+року\s+(?:під час перевірки|був відсутній|самовільно залишив))'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            # Використовуємо вашу функцію форматування для отримання m/d/yy
            return format_to_excel_date(match.group(1))

        # Якщо за специфічним якорем не знайдено, беремо першу дату в блоці обставин
        fallback = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        if fallback:
            return format_to_excel_date(fallback.group(1))

        return NA

    def _extract_desert_conditions(self, text):
        """
        Шукає абзац з обставинами (перевірка наявності/шикування + відсутність).
        """
        # 1. Універсальне розбиття на абзаци
        paragraphs = [p.strip() for p in re.split(r'[\r\n]{2,}', text) if p.strip()]

        # Ключові слова для перевірки/контролю
        check_markers = ["під час перевірки", "під час шикування", "перевірці наявності", "не повернувся", "не прибуття"]
        # Ключові слова для факту відсутності
        absence_markers = ["відсутн", "виявлено відсутність", "не було в наявності", "не повернувся", "не прибуття"]

        for para in paragraphs:
            clean_para = " ".join(para.split()).lower()

            # 2. Перевіряємо, чи є хоча б один маркер перевірки ТА хоча б один маркер відсутності
            has_check = any(marker in clean_para for marker in check_markers)
            has_absence = any(marker in clean_para for marker in absence_markers)

            if has_check and has_absence:
                # Повертаємо абзац одним рядком без внутрішніх розривів
                return " ".join(para.split())

        return NA

    def _extract_return_date(self, text):
        """
        Повертає дату тільки якщо в тексті є факт присутності.
        Якщо 'був присутній' не знайдено — повертає N/A.
        """
        # 1. Перевіряємо наявність ключової фрази
        if "був присутній" not in text.lower():
            return ''

        # 2. Якщо фраза є, шукаємо дату ДД.ММ.РРРР, яка стоїть ПЕРЕД "року був присутній"
        # Або просто дату в цьому ж реченні
        pattern = r'(\d{2}\.\d{2}\.\d{4})(?=\s+року\s+був\s+присутній)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return format_to_excel_date(match.group(1))

        # 3. Резервний пошук дати ТІЛЬКИ якщо ми вже знаємо, що людина була присутня
        # (на випадок іншого порядку слів)
        fallback_with_presence = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        if fallback_with_presence:
            return format_to_excel_date(fallback_with_presence.group(1))

        return ''

    def _extract_desertion_region(self, text):
        """
        Витягує повну географічну назву: населений пункт, район та область.
        """
        # 1. Визначаємо ключові маркери початку (н.п., с., м., місто, село тощо)
        # 2. Захоплюємо все до слова "області" або "обл." включно.
        # Патерн пояснення:
        # (?i) - ігнорувати регістр
        # (?:н\.п\.|с\.|м\.|село|місто|селище|смт)\s+ - початок з маркера
        # ([А-ЯҐЄІЇ].*?(?:області|обл\.)) - назва з великої літери до слова область

        pattern = r'(?i)(?:н\.п\.|с\.|м\.|село|місто|селище|смт)\s+([А-ЯҐЄІЇ][^.;]*?(?:області|обл\.))'

        match = re.search(pattern, text, re.DOTALL)
        if match:
            # Очищаємо від зайвих пробілів та переносів рядків
            full_address = " ".join(match.group(1).split())
            # Видаляємо зайві крапки в кінці, якщо вони є
            return full_address.strip().rstrip('.')

        # Додатковий пошук: якщо не знайшли маркер н.п., шукаємо просто конструкцію "Район... Область"
        backup_pattern = r'(?i)([А-Я][а-яіЇє]*?\s+район[у|а]\s+[А-Я][а-яіЇє]*?\s+області)'
        backup_match = re.search(backup_pattern, text)
        if backup_match:
            return " ".join(backup_match.group(1).split())

        return NA

    def _calculate_service_days(self, conscription_date_str, desertion_date_str):
        """
            Рахує дні та перевіряє їх на логіку.
            """
        if conscription_date_str == NA or desertion_date_str == NA:
            return 0

        try:
            def parse_date(d_str):
                return datetime.strptime(d_str, config.EXCEL_DATE_FORMAT)

            dt_start = parse_date(conscription_date_str)
            dt_end = parse_date(desertion_date_str)

            # Рахуємо різницю
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
        # 1. Автоматично формуємо список унікальних значень із мапінгу (Values)
        short_values = set()
        for val in SUBUNIT_MAPPING.values():
            # Видаляємо \1, щоб отримати чисту абревіатуру для пошуку
            clean_val = val.replace(r'\1', '').strip()
            if clean_val:
                short_values.add(clean_val)

        # ЕТАП 1: Перевірка назви файлу (тепер з IGNORECASE)
        if file_name:
            # Сортуємо від найдовших до найкоротших
            sorted_shorts = sorted(short_values, key=len, reverse=True)

            for short_val in sorted_shorts:
                pattern = rf'(?:^|[\s_])(\d*[\s_]*)?{re.escape(short_val)}(?=[\s_]|$)'

                # Додаємо re.IGNORECASE, щоб 'аемб' або 'Аемб' теж працювали
                match = re.search(pattern, file_name, re.IGNORECASE)

                if match:
                    res = match.group(0).strip()
                    # Гарне форматування: додаємо пробіл між цифрою та текстом, якщо його не було
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
