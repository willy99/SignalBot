from typing import List

import config
from dics.deserter_xls_dic import MIL_UNITS, COLUMN_MIL_UNIT, COLUMN_INCREMENTAL, COLUMN_ERDR_NOTATION, COLUMN_ERDR_DATE, COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_BIRTHDAY
from dics.security_config import PERM_READ, MODULE_ADMIN
from gui.auth_routes import refresh_session_method
from gui.services.request_context import RequestContext
from domain.person_filter import PersonSearchFilter
from gui.services.auth_manager import AuthManager
from service.processing.DocumentProcessingService import DocumentProcessingService
from service.processing.MyWorkFlow import MyWorkFlow
from service.processing.processors.DocTemplator import DocTemplator
from service.processing.processors.ErdrKramProcessor import ErdrKramProcessor, ErdrKramRow
from service.processing.processors.ExcelReport import ExcelReporter
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
import io
from datetime import date

class ReportController:
    def __init__(self, doc_templator: DocTemplator, worklow: MyWorkFlow, auth_manager: AuthManager):
        self.doc_templator:DocTemplator = doc_templator
        self.reporter:ExcelReporter = worklow.reporter
        self.auth_manager:AuthManager = auth_manager
        self.log_manager:LoggerManager = worklow.log_manager
        self.logger = worklow.log_manager.get_logger()
        self.workflow = worklow

    @refresh_session_method
    def do_subunit_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_subunit_desertion_stats(search_filter)
        return results

    @refresh_session_method
    def get_general_state_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_general_state_report(search_filter)
        return results

    @refresh_session_method
    def get_yearly_desertion_report(self, ctx: RequestContext, search_filter: PersonSearchFilter):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо репорт: ' + str(search_filter))
        results = self.reporter.get_yearly_desertion_stats()
        return results

    @refresh_session_method
    def get_daily_added_records_report(self, ctx: RequestContext, target_date: date = None):
        self.logger.debug('UI:' + ctx.user_name + ': Генеруємо щоденний репорт: ' + str(target_date))
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
        self.logger.info(
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

        self.logger.info(
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

        self.logger.info(
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
                self.logger.info(
                    f"UI:{ctx.user_name}: КРАМ — збережено {success_count} ЄРДР-записів"
                )

        return success_count, errors

    @refresh_session_method
    def compare_file_with_db(
        self,
        ctx: RequestContext,
        file_bytes: bytes,
        mapping: dict,          # {gen_field: upload_col}
        sel_upload: list,       # які колонки файлу показувати у звіті
        sel_general: list,      # які поля бази показувати у звіті
    ) -> list[dict]:
        """
        Порівнює рядки завантаженого Excel-файлу з основною базою.

        Алгоритм:
          1. Читаємо файл, будуємо список рядків із даними.
          2. Для кожного рядка витягуємо ключові поля через mapping
             (ПІБ, РНОКПП, дата народження).
          3. Один пакетний виклик find_persons() → dict[uid, match].
          4. Повертаємо list[dict] з file_data, db_data, found, has_diff.
        """
        import io as _io
        import openpyxl
        from domain.person_key import PersonKey
        from dics.deserter_xls_dic import NA

        self.logger.info(
            f"UI:{ctx.user_name}: compare_file_with_db, "
            f"mapping={mapping}, sel_upload={sel_upload}, sel_general={sel_general}"
        )

        # -- Читаємо файл --------------------------------------------------
        wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active

        # Зчитуємо хедер (рядок 1)
        raw_header = [
            str(cell).strip() if cell is not None else ''
            for cell in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        ]
        col_index: dict[str, int] = {name: i for i, name in enumerate(raw_header)}

        # Маппінг у зворотному напрямку для швидкого доступу
        # gen_field → індекс колонки у файлі
        gf_to_idx: dict[str, int] = {
            gf: col_index[uc]
            for gf, uc in mapping.items()
            if uc in col_index
        }

        # Зчитуємо дані рядки
        file_rows: list[dict] = []   # [{col_name: value, ...}, ...]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            row_dict = {
                raw_header[i]: (str(row[i]).strip() if row[i] is not None else '')
                for i in range(min(len(row), len(raw_header)))
            }
            file_rows.append(row_dict)

        wb.close()
        self.logger.info(f"compare: прочитано {len(file_rows)} рядків з файлу")

        if not file_rows:
            return []

        # -- Будуємо PersonKey для кожного рядка ----------------------------
        def _get(row: dict, gen_field: str) -> str:
            uc = mapping.get(gen_field, '')
            return row.get(uc, '') or ''

        keys: list[PersonKey] = [
            PersonKey(
                name=_get(r, COLUMN_NAME),
                rnokpp=_get(r, COLUMN_ID_NUMBER),
                des_date='',
                mil_unit='',
            )
            for r in file_rows
        ]

        # -- Пакетний пошук -------------------------------------------------
        try:
            db_results: dict[str, dict] = self.workflow.excelProcessor.find_persons(keys)
        except Exception as e:
            self.logger.error(f"compare: помилка find_persons: {e}")
            db_results = {}

        found_count = len(db_results)
        self.logger.info(f"compare: знайдено {found_count} з {len(file_rows)} у базі")

        # -- Збираємо результат ---------------------------------------------
        results: list[dict] = []
        for row, key in zip(file_rows, keys):
            match = db_results.get(key.uid)
            db_data = match.get('data', {}) if match else {}

            # Визначаємо чи є розбіжності у вибраних полях
            has_diff = False
            if match:
                for gf in sel_general:
                    uc = mapping.get(gf)
                    if uc:
                        file_val = (row.get(uc) or '').strip().lower()
                        db_val   = str(db_data.get(gf) or '').strip().lower()
                        if file_val and db_val and file_val != db_val:
                            has_diff = True
                            break

            results.append({
                'file_data': {col: row.get(col, '') for col in sel_upload},
                'db_data':   {gf: str(db_data.get(gf) or '') for gf in sel_general},
                'found':     bool(match),
                'has_diff':  has_diff,
            })

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
