from typing import List

import config
import io
import openpyxl
from datetime import date, datetime

from dics.security_config import PERM_READ, MODULE_ADMIN
from dics.deserter_xls_dic import *
from domain.person_filter import PersonSearchFilter
from gui.auth_routes import refresh_session_method
from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.processing.DocumentProcessingService import DocumentProcessingService
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from service.processing.processors.ErdrKramProcessor import ErdrKramProcessor, ErdrKramRow
from service.processing.processors.ExcelReport import ExcelReporter
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
from utils.utils import format_to_excel_date


class ReportController:
    def __init__(self, doc_templator: DocTemplator, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.doc_templator: DocTemplator = doc_templator
        self.reporter:      ExcelReporter = worklow.reporter
        self.workflow:      MyWorkFlow    = worklow        # потрібен для compare (excelProcessor)
        self.auth_manager:  AuthManager   = auth_manager
        self.log_manager:   LoggerManager = worklow.log_manager
        self.logger = worklow.log_manager.get_logger()

    @refresh_session_method
    def do_subunit_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт subunit: ' + str(search_filter))
        results = self.reporter.get_subunit_desertion_stats(search_filter)
        return results

    @refresh_session_method
    def get_general_state_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт general: ' + str(search_filter))
        results = self.reporter.get_general_state_report(search_filter)
        return results

    @refresh_session_method
    def get_yearly_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт yealy stat: ' + str(search_filter))
        results = self.reporter.get_yearly_desertion_stats()
        return results

    @refresh_session_method
    def get_daily_added_records_report(self, ctx: RequestContext, target_date: date = None):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо щоденний репорт daily: ' + str(target_date))
        results = self.reporter.get_daily_report(target_date)
        return results

    @refresh_session_method
    def get_daily_returns_report(self, ctx: RequestContext, target_date: date = None, exclude_names: List[str] = None, pre_fetched_archive=None):
        return self.reporter.get_daily_returns_report(target_date, exclude_names, pre_fetched_archive)

    @refresh_session_method
    def get_daily_archive_files(self, ctx: RequestContext, target_date, known_names: list):
        dservice = DocumentProcessingService(self.log_manager)
        return dservice.get_daily_archive_files(target_date, known_names)

    @refresh_session_method
    def get_dupp_names_report(self, ctx: RequestContext):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_dupp_names_report()
        return results

    @refresh_session_method
    def get_error_birthday_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт дублікатів прізвищ в системі: ')
        results = self.reporter.get_inn_birthday_mismatch_report(search_filter)
        return results

    @refresh_session_method
    def get_waiting_for_erdr_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт - справи очікуючі ЄРДР: ')
        results = self.reporter.get_waiting_for_erdr_report(search_filter)
        return results

    @refresh_session_method
    def get_brief_report(self, ctx: RequestContext):
        return self.reporter.get_brief_summary()

    @refresh_session_method
    def process_kram_file(self, ctx: RequestContext, file_bytes: bytes) -> list[ErdrKramRow]:
        """Парсить файл КРАМ і звіряє кожен запис з основною базою."""
        self.logger.debug(
            f"UI:{ctx.user_name}: запуск звірки ЄРДР КРАМ, "
            f"розмір файлу: {len(file_bytes)} байт"
        )
        processor = ErdrKramProcessor(
            excel_processor=self.workflow.excelProcessor,
            log_manager=self.log_manager,
        )
        results = processor.process_file(file_bytes)

        found_count = sum(1 for r in results if r.found_in_db)
        erdr_count = sum(1 for r in results if r.found_in_db and r.db_erdr_date and r.db_erdr_date != 'н/д')
        miss_count = sum(1 for r in results if not r.found_in_db)

        self.logger.debug(
            f"UI:{ctx.user_name}: КРАМ — оброблено {len(results)} рядків. "
            f"Знайдено: {found_count}, є ЄРДР: {erdr_count}, не знайдено: {miss_count}"
        )
        return results

    @refresh_session_method
    def save_erdr_updates(
            self,
            ctx: RequestContext,
            rows_to_save: list[ErdrKramRow],
    ) -> tuple[int, list[str]]:
        """
        Записує ЄРДР-дані з файлу КРАМ у основну Excel-базу.

        Для кожного рядка:
          - бере COLUMN_INCREMENTAL (ID) і COLUMN_MIL_UNIT з db_data що вже знайдені
          - записує erdr_number → COLUMN_ERDR_NOTATION
          - записує erdr_date   → COLUMN_ERDR_DATE

        Повертає (кількість успішно збережених, список помилок).
        """
        if not rows_to_save:
            return 0, []

        self.logger.debug(
            f"UI:{ctx.user_name}: зберігаємо ЄРДР для {len(rows_to_save)} записів"
        )

        processor = self.workflow.excelProcessor
        success_count = 0
        errors: list[str] = []

        # Групуємо по військовій частині — щоб перемикати аркуш якнайменше разів
        grouped: dict[str, list[ErdrKramRow]] = {}
        for r in rows_to_save:
            mil_unit = (r.db_data or {}).get(COLUMN_MIL_UNIT) or MIL_UNITS[0]
            grouped.setdefault(mil_unit, []).append(r)

        with processor.lock:
            for mil_unit, unit_rows in grouped.items():
                processor.switch_to_sheet(mil_unit, silent=True)

                for r in unit_rows:
                    row_id = (r.db_data or {}).get(COLUMN_INCREMENTAL)
                    if not row_id:
                        errors.append(f"Рядок {r.source_row} ({r.parsed_name}): не знайдено ID в базі")
                        continue

                    updated = {
                        COLUMN_MIL_UNIT: mil_unit,
                        COLUMN_INCREMENTAL: row_id,
                        COLUMN_ERDR_NOTATION: r.erdr_number,
                        COLUMN_ERDR_DATE: r.erdr_date,
                    }
                    ok = processor.update_row_by_id(row_id, updated)
                    if ok:
                        success_count += 1
                        self.logger.debug(
                            f"КРАМ: збережено ЄРДР для ID={row_id} "
                            f"({r.parsed_name}): {r.erdr_number} від {r.erdr_date}"
                        )
                    else:
                        errors.append(
                            f"Рядок {r.source_row} ({r.parsed_name}): "
                            f"не вдалося записати в Excel (ID={row_id})"
                        )

            if success_count > 0:
                processor.save()
                self.logger.debug(
                    f"UI:{ctx.user_name}: КРАМ — збережено {success_count} ЄРДР-записів"
                )

        return success_count, errors

    @refresh_session_method
    def compare_file_with_db(
        self,
        ctx: RequestContext,
        file_bytes: bytes,
        mapping: dict[str, str],       # {gen_field: upload_col}
        sel_upload: list[str],         # колонки файлу для відображення (порядок важливий)
        sel_general: list[str],        # поля бази для відображення
    ) -> list[dict]:
        """
        Порівнює рядки з завантаженого xlsx з основною базою СЗЧ.

        Алгоритм:
          1. Читаємо файл, витягуємо рядки у вигляді {col: value}
          2. Для кожного рядка шукаємо збіг у А0224 і А7018 за маппінгом
             (пріоритет: РНОКПП → ПІБ)
          3. Повертаємо список рядків з file_data, db_data, found, db_row_idx, db_mil_unit

        Значення дат нормалізуються до config.EXCEL_DATE_FORMAT (dd.mm.YYYY).
        Для коректного сортування в UI додається _sort_key у форматі YYYY-MM-DD.
        """
        self.logger.info(f"UI:{ctx.user_name}: порівняння файлу, маппінг={list(mapping.keys())}")

        # --- Крок 1: читаємо файл ---
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(c).strip() for c in next(rows_iter) if c is not None]

        file_rows: list[dict] = []
        for row in rows_iter:
            if not any(row):
                continue
            file_rows.append({headers[i]: row[i] for i in range(len(headers))})
        wb.close()

        # --- Крок 2: будуємо пошуковий індекс по обох аркушах ---
        processor = self.workflow.excelProcessor
        key_rnokpp_col = mapping.get(COLUMN_ID_NUMBER, '')
        key_name_col   = mapping.get(COLUMN_NAME, '')
        key_bday_col   = mapping.get(COLUMN_BIRTHDAY, '')

        # Збираємо рядки з обох аркушів — один прохід по кожному
        db_by_rnokpp: dict[str, dict] = {}
        db_by_name:   dict[str, dict] = {}

        for mil_unit in MIL_UNITS:
            try:
                with processor.lock:
                    processor.switch_to_sheet(mil_unit, silent=True)
                    last_row = processor.get_last_row()
                    data = processor.sheet.range(f'A2:BB{last_row}').value
                    header = processor.header      # {col_name: col_index_1based}
            except Exception as e:
                self.logger.warning(f"compare: не вдалось прочитати аркуш {mil_unit}: {e}")
                continue

            if not data:
                continue

            rnokpp_idx = header.get(COLUMN_ID_NUMBER, 1) - 1
            name_idx   = header.get(COLUMN_NAME, 1) - 1

            for i, row in enumerate(data):
                if not row or not row[name_idx]:
                    continue

                serialized: list = []
                for cell in row:
                    processor._transform_cell(cell, serialized)

                row_dict = dict(zip(header, serialized))
                row_dict[COLUMN_MIL_UNIT] = mil_unit

                entry = {
                    'data':        row_dict,
                    'row_idx':     i + 2,
                    'mil_unit':    mil_unit,
                }

                rnokpp_val = str(row_dict.get(COLUMN_ID_NUMBER, '') or '').strip().rstrip('.0')
                name_val   = str(row_dict.get(COLUMN_NAME, '') or '').strip().lower()

                if rnokpp_val and len(rnokpp_val) >= 8:
                    db_by_rnokpp[rnokpp_val] = entry
                if name_val:
                    db_by_name.setdefault(name_val, entry)

        # --- Крок 3: порівняння рядків файлу з індексом ---
        results = []
        for file_row in file_rows:
            # Нормалізуємо дати у file_row
            normalized_file: dict[str, str] = {}
            for col, val in file_row.items():
                normalized_file[col] = format_to_excel_date(val)

            # Пошук — спочатку РНОКПП, потім ПІБ
            db_entry = None
            if key_rnokpp_col:
                rnokpp_raw = str(file_row.get(key_rnokpp_col, '') or '').strip().rstrip('.0')
                if rnokpp_raw and len(rnokpp_raw) >= 8:
                    db_entry = db_by_rnokpp.get(rnokpp_raw)

            if not db_entry and key_name_col:
                name_raw = str(file_row.get(key_name_col, '') or '').strip().lower()
                if name_raw:
                    db_entry = db_by_name.get(name_raw)

            found = db_entry is not None
            db_data_normalized = {
                gf: format_to_excel_date(db_entry['data'].get(gf)) if db_entry else ''
                for gf in sel_general
            }

            results.append({
                'found':        found,
                'file_data':    normalized_file,
                'db_data':      db_data_normalized,
                # db_logical_id — значення колонки A (те, що приймає update_row_by_id)
                # НЕ плутати з db_row_idx (фактичний рядок Excel)
                'db_logical_id': int(db_entry['data'].get(COLUMN_INCREMENTAL, 0)) if db_entry else None,
                'db_mil_unit':   db_entry['mil_unit'] if db_entry else None,
            })

        self.logger.info(
            f"UI:{ctx.user_name}: порівняння завершено — "
            f"{sum(1 for r in results if r['found'])}/{len(results)} знайдено"
        )
        return results


    def is_admin(self):
        return self.auth_manager.has_access(MODULE_ADMIN, PERM_READ)

    def generate_daily_report_word(self, ctx: RequestContext, target_date: str, raw_documents: list) -> tuple[bytes, str]:
        file_bytes, file_name = self.doc_templator.make_daily_report(target_date, raw_documents)

        try:
            client = StorageFactory.create_client(config.REPORT_DAILY_DESERTION, self.log_manager)
            with client:
                destination_path = f"{config.REPORT_DAILY_DESERTION}{client.get_separator()}{file_name}"
                buffer = io.BytesIO(file_bytes)
                client.save_file_from_buffer(destination_path, buffer)
                self.log_manager.get_logger().info(f"✅ Звіт СЗЧ успішно збережено в архів: {destination_path}")
        except Exception as e:
            self.log_manager.get_logger().error(f"❌ Не вдалося зберегти звіт в архівну папку: {e}")
        return file_bytes, file_name


    def get_awol_heatmap_data(self):
        return self.reporter.get_awol_heatmap_data()

    def get_monthly_dynamics_data(self):
        return self.reporter.get_monthly_dynamics_data()