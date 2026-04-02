"""
SignalBotHandler
================
Обробляє вхідні текстові повідомлення від Signal-бота.
Відповідає за:
  - перевірку авторизації відправника (тільки верифіковані 2FA-користувачі)
  - стейт-машину меню
  - формування текстових відповідей і звітів

Навмисно НЕ знає про:
  - SignalClient (не відправляє сам — повертає текст, викликач відправляє)
  - ExcelProcessor напряму (звертається через ExcelReporter)
  - MyWorkFlow (отримує залежності через __init__)
"""

from datetime import date
from typing import Optional

from domain.user import User
from service.users.UserService import UserService
from service.processing.processors.ExcelReport import ExcelReporter
from service.processing.processors.BatchProcessor import BatchProcessor
from service.processing.converter.ColumnConverter import ColumnConverter
from service.storage.LoggerManager import LoggerManager
from itertools import groupby
import re
from datetime import datetime

class SignalBotHandler:

    # ------------------------------------------------------------------
    # Константи меню
    # ------------------------------------------------------------------
    _MAIN_MENU  = (
        "Головне меню:\n"
        "1. Операції з файлами\n"
        "2. Статистика і звіти\n"
        "0. Вихід"
    )
    _PROCESS_MENU = (
        "Операції:\n"
        "1. Batch-обробка файлів\n"
        "2. Конвертація полів\n"
        "0. Назад"
    )
    _STAT_MENU = (
        "Статистика і звіти:\n"
        "1. Щоденний зведений звіт (сьогодні)\n"
        "0. Назад"
    )
    _MENU_PROMPT = "Напишіть 'меню' для початку роботи."

    def __init__(
        self,
        user_service: UserService,
        reporter: ExcelReporter,
        log_manager: LoggerManager,
        excel_file_path: str,
        excel_lock,
    ):
        self.user_service  = user_service
        self.reporter      = reporter
        self.log_manager   = log_manager
        self.logger        = log_manager.get_logger()
        self.excel_file_path = excel_file_path
        self._excel_lock   = excel_lock  # threading.Lock з MyWorkFlow

    # ------------------------------------------------------------------
    # Авторизація
    # ------------------------------------------------------------------

    def authorize(self, phone_number: str) -> Optional[object]:
        """
        Повертає User якщо номер верифіковано через 2FA,
        або None якщо доступ заборонено.
        Не повідомляє зловмисника про причину відмови.
        """
        user = self.user_service.get_user_by_phone(phone_number)
        if user:
            self.logger.info(
                f"Signal-бот: авторизація OK — {user.username} ({phone_number[-4:]}****)"
            )
        else:
            self.logger.warning(
                f"Signal-бот: СПРОБА ДОСТУПУ від незнайомого номера {phone_number}"
            )
        return user

    # ------------------------------------------------------------------
    # Основний обробник
    # ------------------------------------------------------------------

    def handle(self, phone_number: str, text: str) -> str:
        """
        Головний метод: перевіряє авторизацію і повертає текстову відповідь.
        Нічого не відправляє сам — відправка залишається у MyWorkFlow.

        Returns:
            Рядок-відповідь або None якщо відповідати не треба.
        """
        # 1. Перевірка авторизації
        user:User = self.authorize(phone_number)
        if not user:
            return "❌ Доступ заборонено. Ваш номер не верифіковано в системі."

        # 2. Швидкі відповіді (не залежать від стану)
        normalized = text.lower().strip()
        if normalized in ("привіт", "hello", "hi"):
            return f"Привіт, {user.full_name or user.username}! Напишіть 'меню' для роботи."

        # 3. Стейт-машина
        return self._process_state(phone_number, normalized)

    # ------------------------------------------------------------------
    # Стейт-машина
    # ------------------------------------------------------------------

    def _process_state(self, phone_number: str, text: str) -> str:
        state = self.user_service.get_user_state(phone_number)

        # special cases
        date_match = re.search(r"(?:щоден[н]?ий\s*(?:звіт\s*за|звіт|за|[,])?)\s*(\d{2}\.\d{2}\.\d{4})", text.lower())
        if date_match:
            date_str = date_match.group(1)
            try:
                parsed_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                return self._daily_report_text(parsed_date)
            except ValueError:
                return f"❌ Неправильний формат дати: {date_str}. Використовуйте ДД.ММ.РРРР"

        self.logger.debug(
            f"Signal-бот: phone=...{phone_number[-4:]}, state={state}, text='{text}'"
        )

        # Глобальна команда — скидання в меню
        if text in ("меню", "start", "menu", "/start"):
            self.user_service.set_user_state(phone_number, "MAIN_MENU")
            return self._MAIN_MENU

        if state == "MAIN_MENU":
            return self._handle_main_menu(phone_number, text)

        elif state == "PROCESS":
            return self._handle_process_menu(phone_number, text)

        elif state == "STAT":
            return self._handle_stat_menu(phone_number, text)

        # Невідомий стан або START
        return self._MENU_PROMPT

    def _handle_main_menu(self, phone_number: str, text: str) -> str:
        if text == "1":
            self.user_service.set_user_state(phone_number, "PROCESS")
            return self._PROCESS_MENU
        if text == "2":
            self.user_service.set_user_state(phone_number, "STAT")
            return self._STAT_MENU
        if text in ("0", "вихід"):
            self.user_service.set_user_state(phone_number, "START")
            return self._MENU_PROMPT
        return self._MAIN_MENU

    def _handle_process_menu(self, phone_number: str, text: str) -> str:
        if text == "0":
            self.user_service.set_user_state(phone_number, "MAIN_MENU")
            return self._MAIN_MENU
        if text in ("1", "batch"):
            try:
                with self._excel_lock:
                    BatchProcessor(self.log_manager, self.excel_file_path).start_processing(0)
                return "✅ Batch-обробку завершено."
            except Exception as e:
                self.logger.error(f"Signal-бот: помилка batch: {e}")
                return f"❌ Помилка batch-обробки: {e}"
        if text in ("2", "convert"):
            try:
                with self._excel_lock:
                    ColumnConverter(self.excel_file_path, self.log_manager).convert()
                return "✅ Конвертацію завершено."
            except Exception as e:
                self.logger.error(f"Signal-бот: помилка конвертації: {e}")
                return f"❌ Помилка конвертації: {e}"
        return self._PROCESS_MENU

    def _handle_stat_menu(self, phone_number: str, text: str) -> str:
        if text == "0":
            self.user_service.set_user_state(phone_number, "MAIN_MENU")
            return self._MAIN_MENU
        if text == "1":
            return self._daily_report_text()
        return self._STAT_MENU

    # ------------------------------------------------------------------
    # Форматування звіту
    # ------------------------------------------------------------------

    def _daily_report_text(self, target_date: date = None) -> str:
        try:
            for_date = target_date if target_date else date.today()
            lines = [f"📊 *ЗВЕДЕНИЙ ЗВІТ ЗА {for_date.strftime('%d.%m.%Y')}*\n"]

            # --- Блок 1: Загальна статистика (Беремо як приклад для А0224) ---
            summary_rows = self.reporter.get_brief_summary()
            if summary_rows:
                s = summary_rows[0]
                lines.append("📌 *Загальна статистика А0224:*")
                lines.append(f"  Всього СЗЧ: {s.get('total_awol', 0)}")
                lines.append(f"  В розшуку:   {s.get('in_search', 0)}")
                lines.append(f"  Повернулись: {s.get('returned', 0)}")
                lines.append("")

            # --- Блок 2: Нові записи сьогодні ---
            daily_data = self.reporter.get_daily_report(for_date)

            if not daily_data:
                lines.append("ℹ️ Нових записів за сьогодні немає.")
            else:
                # Сортуємо для коректної роботи groupby: спочатку по в/ч, потім по категорії
                daily_data.sort(key=lambda x: (x['sheet_name'], x['category']))

                # Групуємо по Військовій частині (sheet_name)
                for sheet_name, sheet_group in groupby(daily_data, key=lambda x: x['sheet_name']):
                    lines.append(f"🏢 *ЧАСТИНА {sheet_name}*")
                    lines.append("=" * 20)

                    # Перетворюємо групу в список, щоб пройтися по ній двічі (для СЗЧ та Повернень)
                    records = list(sheet_group)

                    # 1. Секція СЗЧ (standard_event)
                    new_awol = [r for r in records if r['category'] == 'standard_event']
                    if new_awol:
                        lines.append(f" 🏃‍♂️ *НОВІ ПОДІЇ / СЗЧ ({len(new_awol)}):*")
                        for i, r in enumerate(new_awol, 1):
                            locality = r.get('desertion_locality') or r.get('desertion_place') or '—'
                            lines.append(
                                f"{i}. {r['title']} {r['name']}\n"
                                f"   • {r['subunit']} | СЗЧ від: {r['des_date'].strftime('%d.%m.%Y') if r['des_date'] else '—'}\n"
                                f"   • Місце: {locality}"
                            )
                        lines.append("")

                    # 2. Секція Повернень (late_return)
                    returned = [r for r in records if r['category'] == 'late_return']
                    if returned:
                        lines.append(f"✅ *НЕСВОЄЧАСНІ ПОВЕРНЕННЯ ({len(returned)}):*")
                        for i, r in enumerate(returned, 1):
                            # Рахуємо скільки днів був відсутній
                            absent_days = r.get('term_absent', '—')
                            lines.append(
                                f"{i}. {r['title']} {r['name']}\n"
                                f"   • {r['subunit']} | Відсутній: {absent_days} діб\n"
                                f"   • Повернувся: {r['ret_date'].strftime('%d.%m.%Y') if r['ret_date'] else '—'}"
                            )
                        lines.append("")

                    lines.append("")  # Розділювач між частинами

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Signal-бот: помилка формування звіту: {e}")
            return f"❌ Не вдалось сформувати звіт: {e}"
