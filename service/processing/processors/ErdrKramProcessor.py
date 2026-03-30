"""
ErdrKramProcessor
=================
Парсить Excel-файл КРАМ (кримінальні провадження):
  - Стовпець 1: текст опису порушення (ПІБ, дата народження, іноді РНОКПП)
  - Стовпець 2: військова частина (завжди А0224, але може варіюватись)
  - Стовпець 3: номер ЄРДР з датою

Для кожного рядка:
  1. Витягує ПІБ, дату народження, РНОКПП з тексту опису
  2. Шукає особу в основній базі через ExcelProcessor.find_person()
  3. Повертає результат порівняння: знайдено / не знайдено,
     є ЄРДР в базі чи ні
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import openpyxl

from dics.deserter_xls_dic import (
    PATTERN_NAME,
    PATTERN_BIRTHDAY,
    PATTERN_BIRTHDAY_FALLBACK,
    PATTERN_ID_MARKER,
    PATTERN_ID_DIGITS,
    PATTERN_ID_STANDALONE,
    COLUMN_ERDR_DATE,
    COLUMN_ERDR_NOTATION,
    COLUMN_NAME,
    COLUMN_BIRTHDAY,
    COLUMN_ID_NUMBER,
    NA,
)
from domain.person_key import PersonKey
from utils.utils import format_to_excel_date

# ---------------------------------------------------------------------------
# Патерн для номера ЄРДР:  №62025050010008946 від 28.02.2025
# або просто: 62025050010008946 від 28.02.2025
# ---------------------------------------------------------------------------
_PATTERN_ERDR_NUMBER = re.compile(
    r'[№#]?\s*(\d{14,20})\s+від\s+(\d{2}\.\d{2}\.\d{4})',
    re.IGNORECASE
)

# Патерн для ПІБ (з deserter_xls_dic)
_PATTERN_NAME = re.compile(PATTERN_NAME)

# Патерн для дати народження
_PATTERN_BIRTHDAY = re.compile(PATTERN_BIRTHDAY, re.IGNORECASE)
_PATTERN_BIRTHDAY_FALLBACK = re.compile(PATTERN_BIRTHDAY_FALLBACK)

# Патерни для РНОКПП
_PATTERN_ID_MARKER = re.compile(PATTERN_ID_MARKER)
_PATTERN_ID_DIGITS = re.compile(PATTERN_ID_DIGITS)
_PATTERN_ID_STANDALONE = re.compile(PATTERN_ID_STANDALONE)


# ---------------------------------------------------------------------------
# Структура одного результату
# ---------------------------------------------------------------------------

@dataclass
class ErdrKramRow:
    # --- Дані з вхідного файлу ---
    source_row: int                     # номер рядка у файлі (для дебагу)
    raw_description: str                # оригінальний текст опису
    raw_mil_unit: str                   # оригінальний текст в/ч
    raw_erdr: str                       # оригінальний текст ЄРДР

    parsed_name: str = NA              # ПІБ, витягнуте з опису
    parsed_birthday: str = NA          # дата народження з опису
    parsed_rnokpp: str = NA            # РНОКПП з опису

    erdr_number: str = NA              # номер ЄРДР з вхідного файлу
    erdr_date: str = NA                # дата ЄРДР з вхідного файлу

    # --- Результат пошуку в основній базі ---
    found_in_db: bool = False
    db_erdr_date: str = NA             # COLUMN_ERDR_DATE з основної бази
    db_erdr_notation: str = NA         # COLUMN_ERDR_NOTATION з основної бази

    error: str = ''                    # якщо щось пішло не так при парсингу

    @property
    def status(self) -> str:
        """Зрозумілий статус для відображення в таблиці."""
        if not self.found_in_db:
            return '❓ Не знайдено в базі'
        has_erdr_in_db = self.db_erdr_date and self.db_erdr_date != NA
        has_erdr_in_file = self.erdr_number and self.erdr_number != NA
        if has_erdr_in_db:
            return '✅ ЄРДР є в базі'
        if has_erdr_in_file:
            return '⚠️ ЄРДР є у файлі, але не в базі'
        return '🕐 Знайдено, ЄРДР відсутній'


# ---------------------------------------------------------------------------
# Парсери
# ---------------------------------------------------------------------------

def _parse_name(text: str) -> str:
    """Витягує ПІБ з тексту опису."""
    match = _PATTERN_NAME.search(text)
    if match:
        return f"{match.group(1).strip()} {match.group(3).strip()} {match.group(4).strip()}".strip()
    return NA


def _parse_birthday(text: str) -> str:
    """Витягує дату народження з тексту опису."""
    match = _PATTERN_BIRTHDAY.search(text)
    if match:
        return format_to_excel_date(match.group(1).strip())

    # Якщо немає явної мітки — шукаємо другу дату в тексті
    # (перша зазвичай є датою події)
    all_dates = _PATTERN_BIRTHDAY_FALLBACK.findall(text)
    if len(all_dates) >= 2:
        return format_to_excel_date(all_dates[1])
    return NA


def _parse_rnokpp(text: str) -> str:
    """Витягує РНОКПП з тексту опису (лише коли є явний маркер)."""
    marker = _PATTERN_ID_MARKER.search(text)
    if marker:
        after = text[marker.end(): marker.end() + 30]
        digits = _PATTERN_ID_DIGITS.search(after)
        if digits:
            return digits.group(1)
    # Без маркера — не беремо: 10-значні числа часто є номерами проваджень
    return NA


def _parse_erdr(text: str) -> tuple[str, str]:
    """
    Витягує номер та дату ЄРДР з тексту.
    Повертає (number, date) або (NA, NA).
    """
    if not text or str(text).strip() == '':
        return NA, NA

    text = str(text)
    match = _PATTERN_ERDR_NUMBER.search(text)
    if match:
        return match.group(1), format_to_excel_date(match.group(2))
    return NA, NA


# ---------------------------------------------------------------------------
# Головний процесор
# ---------------------------------------------------------------------------

class ErdrKramProcessor:
    """
    Зчитує Excel-файл КРАМ і звіряє кожний запис з основною базою.
    """

    def __init__(self, excel_processor, log_manager):
        self.excel_processor = excel_processor
        self.logger = log_manager.get_logger()

    def process_file(self, file_bytes: bytes) -> list[ErdrKramRow]:
        """
        Основний метод: приймає байти Excel-файлу,
        повертає список ErdrKramRow з результатами порівняння.
        """
        import io
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active

        results: list[ErdrKramRow] = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Пропускаємо повністю порожні рядки
            if not any(row):
                continue

            raw_desc     = str(row[0] or '').strip()
            raw_mil_unit = str(row[1] or '').strip()
            raw_erdr     = str(row[2] or '').strip()

            if not raw_desc:
                continue

            result = ErdrKramRow(
                source_row=row_idx,
                raw_description=raw_desc,
                raw_mil_unit=raw_mil_unit,
                raw_erdr=raw_erdr,
            )

            # 1. Парсимо дані з опису
            result.parsed_name     = _parse_name(raw_desc)
            result.parsed_birthday = _parse_birthday(raw_desc)
            result.parsed_rnokpp   = _parse_rnokpp(raw_desc)
            result.erdr_number, result.erdr_date = _parse_erdr(raw_erdr)

            self.logger.debug(
                f"КРАМ рядок {row_idx}: "
                f"ПІБ='{result.parsed_name}' "
                f"ДН='{result.parsed_birthday}' "
                f"РНОКПП='{result.parsed_rnokpp}'"
            )

            # 2. Шукаємо в основній базі (потрібне хоч ПІБ або РНОКПП)
            if result.parsed_name != NA or result.parsed_rnokpp != NA:
                self._lookup_in_db(result)
            else:
                result.error = 'Не вдалося розпізнати ПІБ з тексту'
                self.logger.warning(f"КРАМ рядок {row_idx}: не вдалося розпізнати ПІБ. Текст: {raw_desc[:80]}")

            results.append(result)

        wb.close()
        self.logger.info(f"КРАМ: оброблено {len(results)} рядків")
        return results

    def _lookup_in_db(self, result: ErdrKramRow) -> None:
        """Шукає особу в основній базі і заповнює поля result."""
        key = PersonKey(
            name=result.parsed_name if result.parsed_name != NA else '',
            rnokpp=result.parsed_rnokpp if result.parsed_rnokpp != NA else '',
            des_date='',
            mil_unit='',
        )

        try:
            found = self.excel_processor.find_person(key)
        except Exception as e:
            self.logger.error(f"КРАМ: помилка пошуку для '{result.parsed_name}': {e}")
            result.error = f'Помилка пошуку: {e}'
            return

        if not found:
            result.found_in_db = False
            return

        result.found_in_db = True
        data = found.get('data', {})
        result.db_erdr_date     = data.get(COLUMN_ERDR_DATE, NA) or NA
        result.db_erdr_notation = data.get(COLUMN_ERDR_NOTATION, NA) or NA