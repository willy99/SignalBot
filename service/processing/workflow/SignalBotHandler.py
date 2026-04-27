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
from collections import defaultdict
from dics.deserter_xls_dic import MIL_UNITS, COLUMN_MIL_UNIT
from domain.person_filter import PersonSearchFilter
from domain.user import User
from service.processing.processors.ExcelProcessor import ExcelProcessor
from service.users.UserService import UserService
from service.processing.processors.ExcelReport import ExcelReporter
from service.processing.processors.BatchProcessor import BatchProcessor
from service.processing.converter.ColumnConverter import ColumnConverter
from service.storage.LoggerManager import LoggerManager
import regex as re
from datetime import datetime
from domain.person import Person
import html

class SignalBotHandler:

    # ------------------------------------------------------------------
    # Константи меню
    # ------------------------------------------------------------------
    _MAIN_MENU  = (
        "Головне меню:\n"
        "1. Операції з файлами\n"
        "2. Статистика і звіти\n"
        "0. Вихід\n"
        "пошук ПІБ - шукає інформацію за введеними даними\n"
        "щоденний за dd.mm.YYYY - щоденний звіт за дату"

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
    _MENU_PROMPT = ("Напишіть 'меню' для початку роботи.\n"
        "пошук ПІБ - шукає інформацію за введеними даними\n"
        "щоденний за dd.mm.YYYY - щоденний звіт за дату"
    )

    def __init__(
        self,
        user_service: UserService,
        reporter: ExcelReporter,
        log_manager: LoggerManager,
        excel_file_path: str,
        excel_lock,
        excel_processor: ExcelProcessor
    ):
        self.user_service  = user_service
        self.reporter      = reporter
        self.log_manager   = log_manager
        self.logger        = log_manager.get_logger()
        self.excel_file_path = excel_file_path
        self._excel_lock   = excel_lock  # threading.Lock з MyWorkFlow
        self.excel_processor = excel_processor

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
            self.logger.debug(
                f" ✅ Signal-бот: авторизація OK — {user.username} ({phone_number[-4:]}****)"
            )
        else:
            self.logger.warning(
                f" ❌ Signal-бот: СПРОБА ДОСТУПУ від незнайомого номера {phone_number}"
            )
        return user

    # ------------------------------------------------------------------
    # Основний обробник
    # ------------------------------------------------------------------

    async def handle(self, phone_number: str, text: str) -> str:
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
        return await self._process_state(phone_number, normalized)

    # ------------------------------------------------------------------
    # Стейт-машина
    # ------------------------------------------------------------------

    async def _process_state(self, phone_number: str, text: str) -> str:
        state = self.user_service.get_user_state(phone_number)
        self.logger.debug('>>>> text from signal ' + str(html.escape(text)))
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

        search_match = re.search(r"^(?:пошук|шука[й|ти]*|знайди)\s+(.+)", text.lower().strip())
        if search_match:
            query_text = search_match.group(1).strip()
            return await self._handle_person_search(query_text)

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
            return self._daily_report_text(date.today())
        return self._STAT_MENU

    # ------------------------------------------------------------------
    # Форматування звіту
    # ------------------------------------------------------------------

    def _daily_report_text(self, target_date: date) -> str:
        """
        Текстовий варіант щоденного зведеного звіту для Signal.
        Структура дзеркалює daily_report_view:
          1. Загальна статистика (brief_summary)
          2. Нові СЗЧ — А0224 і А7018 окремо (standard_event з get_daily_report)
          3. Звичайні повернення (get_daily_returns_report, за виключенням несвоєчасних)
          4. Несвоєчасні повернення (late_return з get_daily_report)
        """
        try:
            today = target_date if target_date else date.today()
            lines = [f"📊 Зведений звіт за {today.strftime('%d.%m.%Y')}\n"]

            # ----------------------------------------------------------
            # Блок 1: Загальна статистика
            # ----------------------------------------------------------
            summary_rows = self.reporter.get_brief_summary()
            if summary_rows:
                s = summary_rows[0]
                lines.append("📌 Загальна статистика А0224:")
                lines.append(f"  Всього СЗЧ:    {s.get('total_awol', 0)}")
                lines.append(f"  В розшуку:      {s.get('in_search', 0)}")
                lines.append(f"  Повернулись:    {s.get('returned', 0)}")
                lines.append(f"  В БРЕЗ:         {s.get('res_returned', 0)}")
                lines.append("")

            # ----------------------------------------------------------
            # Блок 2: Нові СЗЧ — розбивка по частинах + несвоєчасні
            # ----------------------------------------------------------
            daily_raw = self.reporter.get_daily_report(today)

            new_awol_a0224 = []
            new_awol_a7018 = []
            late_returns = []

            for r in daily_raw:
                # форматуємо дати одразу
                for field in ('des_date', 'ret_date', 'ins_date'):
                    val = r.get(field)
                    if val and hasattr(val, 'strftime'):
                        r[field] = val.strftime('%d.%m.%Y')

                if r.get('category') == 'late_return':
                    late_returns.append(r)
                elif r.get('sheet_name') == 'А7018':
                    new_awol_a7018.append(r)
                else:
                    new_awol_a0224.append(r)

            if new_awol_a0224:
                lines.append(f"⬅️ СЗЧ А0224 ({len(new_awol_a0224)}):")
                for i, r in enumerate(new_awol_a0224, 1):
                    lines.append(self._format_awol_line(i, r))
            else:
                lines.append("⬅️ СЗЧ А0224: нових записів немає")

            lines.append("")

            if new_awol_a7018:
                lines.append(f"⬅️ СЗЧ А7018 ({len(new_awol_a7018)}):")
                for i, r in enumerate(new_awol_a7018, 1):
                    lines.append(self._format_awol_line(i, r))
                lines.append("")

            # ----------------------------------------------------------
            # Блок 3: Звичайні повернення
            # Логіка з view: виключаємо тих, хто вже в late_returns
            # ----------------------------------------------------------
            try:
                return_data_raw = self.reporter.get_daily_returns_report(today)

                # Виключаємо несвоєчасних — вони будуть у окремому блоці
                late_names = {
                    r.get('name', '').strip().lower()
                    for r in late_returns
                    if r.get('name')
                }
                return_data = [
                    r for r in return_data_raw
                    if r.get('name', '').strip().lower() not in late_names
                ]

                if return_data:
                    lines.append(f"↪️ Повернулися ({len(return_data)}):")
                    for i, r in enumerate(return_data, 1):
                        name = r.get('name', '—')
                        title = r.get('title', '—')
                        subunit = r.get('subunit', '—')
                        des_dt = r.get('des_date', '—')
                        ret_dt = r.get('ret_date', '—')
                        lines.append(
                            f"  {i}. {title} {name}\n"
                            f"     {subunit}\n"
                            f"     СЗЧ: {des_dt} → повернувся: {ret_dt}"
                        )
                else:
                    lines.append("↪️ Повернень за сьогодні немає")

            except Exception as e:
                self.logger.warning(f"Signal-бот: не вдалось отримати повернення: {e}")
                lines.append("↪️ Повернення: дані недоступні")

            lines.append("")

            # ----------------------------------------------------------
            # Блок 4: Несвоєчасні повернення
            # ----------------------------------------------------------
            if late_returns:
                lines.append(f"🕒 Несвоєчасні повернення ({len(late_returns)}):")
                for i, r in enumerate(late_returns, 1):
                    name = r.get('name', '—')
                    title = r.get('title', '—')
                    subunit = r.get('subunit', '—')
                    des_dt = r.get('des_date', '—')
                    ret_dt = r.get('ret_date', '—')
                    days_abs = r.get('term_absent', '—')
                    lines.append(
                        f"  {i}. {title} {name}\n"
                        f"     {subunit}\n"
                        f"     Вибув: {des_dt} / Прибув: {ret_dt} / Відсутній: {days_abs} діб"
                    )

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Signal-бот: помилка формування звіту: {e}")
            return f"❌ Не вдалось сформувати звіт: {e}"

    @staticmethod
    def _format_awol_line(num: int, r: dict) -> str:
        """Форматує один рядок нового СЗЧ для Signal-повідомлення."""
        name = r.get('name', '—')
        title = r.get('title', '—')
        subunit = r.get('subunit', '—')
        des_dt = r.get('des_date', '—')
        locality = r.get('desertion_locality') or r.get('desertion_place') or '—'
        return (
            f"  {num}. {title} {name}\n"
            f"     {subunit}\n"
            f"     СЗЧ: {des_dt} | {locality}"
        )


    async def _handle_person_search(self, query: str) -> str:
        # 1. Перевірка авторизації через UserService
        # Припускаємо, що у вашому UserService є метод get_user_by_phone
        if len(query) < 3:
            return "⚠️ Запит занадто короткий. Введіть хоча б 3 літери прізвища."

        try:
            # 2. Формування фільтра (використовуємо ваш об'єкт PersonSearchFilter)
            filter_obj = PersonSearchFilter(query=query)
            mil_unit = MIL_UNITS[0]
            filter_obj.mil_unit = mil_unit
            results_a0224 = self.excel_processor.search_people(filter_obj)
            for item in results_a0224:
                item['data'][COLUMN_MIL_UNIT] = mil_unit
            mil_unit = MIL_UNITS[1]
            filter_obj.mil_unit = mil_unit  # спроба знайти на другому табі
            results_a7018 = self.excel_processor.search_people(filter_obj)
            for item in results_a7018:
                item['data'][COLUMN_MIL_UNIT] = mil_unit
            results = results_a0224 + results_a7018

            persons = [Person.from_excel_dict(item['data']) for item in results]

            if not persons:
                return f"🔍 За запитом «{query}» нікого не знайдено."

            # 1. Групуємо дані
            grouped_data = defaultdict(list)
            for p in persons:
                bday_key = p.birthday.strftime("%d.%m.%Y") if isinstance(p.birthday, date) else p.birthday or "???"
                group_key = f"{p.name.strip().upper()}_{p.rnokpp or bday_key}"
                grouped_data[group_key].append(p)

            response_lines = [f"📋 Знайдено унікальних осіб: {len(grouped_data)}"]

            for i, (key, episodes) in enumerate(list(grouped_data.items())[:7], 1):
                main = episodes[0]  # Беремо загальні дані з першого запису групи

                bday = main.birthday.strftime("%d.%m.%Y") if isinstance(main.birthday, date) else main.birthday or "???"

                # Шапка про людину (загальна інформація)
                line = (
                    f"👤 {main.title} {main.name}\n"
                    f"- Дн: {bday} | РНОКПП: {main.rnokpp or '---'}\n"
                    f"- {main.mil_unit} | {main.subunit}  " + (f"| {str(main.suspended)}" if main.suspended else '')
                )

                # Виводимо кожен епізод СЗЧ окремими рядками
                line += "\n\n- 📌 Епізоди СЗЧ:"
                for ep in episodes:
                    d_date = ep.desertion_date.strftime("%d.%m.%Y") if isinstance(ep.desertion_date, date) else ep.desertion_date or "---"
                    ret_date = f' - {ep.return_date}' if ep.return_date else f' - {ep.return_reserve_date}' if ep.return_reserve_date else " - ..."
                    erdr_str = ""
                    if ep.erdr_date:
                        e_date = ep.erdr_date.strftime("%d.%m.%Y") if isinstance(ep.erdr_date, date) else ep.erdr_date
                        erdr_str = f"\n   ЄРДР: {e_date}"

                    line += f"\n  ▫️ {d_date} ({ep.desertion_place or 'місце не вказано'}){ret_date}{erdr_str}"
                    if ep.review_status:
                        line += f" [Статус: {ep.review_status}]"

                response_lines.append(line + "\n\n" + "—" * 15)

            if len(persons) > 10:
                response_lines.append("...показано перші 10 результатів. Уточніть запит.")

            return "\n".join(response_lines)

        except Exception as e:
            self.logger.error(f"Помилка пошуку в Signal: {e}\n")
            return "❌ Сталася помилка під час звернення до бази даних."