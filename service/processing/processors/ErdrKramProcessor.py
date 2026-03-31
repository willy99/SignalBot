"""
ErdrKramProcessor
=================
Парсить Excel-файл КРАМ (кримінальні провадження):
  - Стовпець 1: текст опису порушення (ПІБ, дата народження, іноді РНОКПП)
  - Стовпець 2: військова частина (завжди А0224, але може варіюватись)
  - Стовпець 3: номер ЄРДР з датою

Алгоритм:
  1. Парсимо всі рядки файлу — витягуємо ПІБ, дату народження, РНОКПП
  2. Будуємо список PersonKey для всіх рядків одразу
  3. Один виклик find_persons() — один прохід по Excel
  4. Розкладаємо результати назад по рядках
"""

import io
from dataclasses import dataclass

import openpyxl

from dics.deserter_xls_dic import (
    COLUMN_ERDR_DATE,
    COLUMN_ERDR_NOTATION,
    NA,
)
from domain.person_key import PersonKey
from utils.regular_expressions import extract_birthday, extract_id_number, extract_erdr, extract_name_lowercased



# ---------------------------------------------------------------------------
# Структура одного результату
# ---------------------------------------------------------------------------

@dataclass
class ErdrKramRow:
    # Дані з вхідного файлу
    source_row: str
    raw_description: str
    raw_mil_unit: str
    raw_erdr: str

    parsed_name: str = NA
    parsed_birthday: str = NA
    parsed_rnokpp: str = NA

    erdr_number: str = NA
    erdr_date: str = NA

    # Результат пошуку в основній базі
    found_in_db: bool = False
    db_erdr_date: str = NA
    db_erdr_notation: str = NA

    error: str = ''

    @property
    def status(self) -> str:
        if not self.found_in_db:
            return '❓ Не знайдено в базі'
        has_erdr_in_db   = self.db_erdr_date   and self.db_erdr_date   != NA
        has_erdr_in_file = self.erdr_number     and self.erdr_number    != NA
        if has_erdr_in_db:
            return '✅ ЄРДР є в базі'
        if has_erdr_in_file:
            return '⚠️ ЄРДР є у файлі, але не в базі'
        return '🕐 Знайдено, ЄРДР відсутній'




# ---------------------------------------------------------------------------
# Головний процесор
# ---------------------------------------------------------------------------

class ErdrKramProcessor:
    """
    Зчитує Excel-файл КРАМ і звіряє всі записи з основною базою
    за один прохід по Excel (через find_persons).
    """

    def __init__(self, excel_processor, log_manager):
        self.excel_processor = excel_processor
        self.logger = log_manager.get_logger()

    def process_file(self, file_bytes: bytes) -> list[ErdrKramRow]:
        """
        Приймає байти xlsx-файлу КРАМ.
        Повертає список ErdrKramRow з результатами порівняння.
        """
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active

        # ------------------------------------------------------------------
        # КРОК 1: парсимо всі рядки файлу — без звернення до бази
        # ------------------------------------------------------------------
        rows: list[ErdrKramRow] = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):
                continue

            raw_id       = str(row[0] or '').strip()
            raw_desc     = str(row[1] or '').strip()
            raw_mil_unit = str(row[2] or '').strip()
            raw_erdr     = str(row[3] or '').strip()

            if not raw_desc:
                continue

            result = ErdrKramRow(
                source_row=raw_id,
                raw_description=raw_desc,
                raw_mil_unit=raw_mil_unit,
                raw_erdr=raw_erdr,
            )

            result.parsed_name     = extract_name_lowercased(raw_desc)
            result.parsed_birthday = extract_birthday(raw_desc)
            result.parsed_rnokpp   = extract_id_number(raw_desc)
            result.erdr_number, result.erdr_date = extract_erdr(raw_erdr)

            if result.parsed_name == NA and result.parsed_rnokpp == NA:
                result.error = 'Не вдалося розпізнати ПІБ з тексту'
                self.logger.warning(
                    f"КРАМ рядок {row_idx}: не розпізнано ПІБ. Текст: {raw_desc[:80]}"
                )

            self.logger.debug(
                f"КРАМ рядок {row_idx}: "
                f"ПІБ='{result.parsed_name}' "
                f"ДН='{result.parsed_birthday}' "
                f"РНОКПП='{result.parsed_rnokpp}'"
            )

            rows.append(result)

        wb.close()
        self.logger.info(f"КРАМ: розпізнано {len(rows)} рядків, починаємо пошук в базі...")

        # ------------------------------------------------------------------
        # КРОК 2: будуємо список PersonKey для всіх рядків одразу
        # ------------------------------------------------------------------
        # Рядки без ПІБ і РНОКПП пропускаємо — нічого шукати
        searchable = [r for r in rows if r.parsed_name != NA or r.parsed_rnokpp != NA]

        keys: list[PersonKey] = [
            PersonKey(
                name=r.parsed_name   if r.parsed_name   != NA else '',
                rnokpp=r.parsed_rnokpp if r.parsed_rnokpp != NA else '',
                des_date='',
                mil_unit='',
            )
            for r in searchable
        ]

        # ------------------------------------------------------------------
        # КРОК 3: ОДИН виклик find_persons — один прохід по Excel
        # ------------------------------------------------------------------
        try:
            db_results: dict[str, dict] = self.excel_processor.find_persons(keys)
        except Exception as e:
            self.logger.error(f"КРАМ: помилка пакетного пошуку: {e}")
            for r in searchable:
                r.error = f'Помилка пошуку: {e}'
            return rows

        self.logger.info(
            f"КРАМ: знайдено {len(db_results)} з {len(searchable)} записів у базі"
        )

        # ------------------------------------------------------------------
        # КРОК 4: розкладаємо результати назад по рядках
        # ------------------------------------------------------------------
        for r, key in zip(searchable, keys):
            match = db_results.get(key.uid)
            if not match:
                r.found_in_db = False
                continue

            r.found_in_db       = True
            data                = match.get('data', {})
            r.db_erdr_date      = data.get(COLUMN_ERDR_DATE,     NA) or NA
            r.db_erdr_notation  = data.get(COLUMN_ERDR_NOTATION, NA) or NA

        return rows