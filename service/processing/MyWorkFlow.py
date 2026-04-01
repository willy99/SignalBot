from watchfiles import awatch
from service.connection.EmailClient import EmailClient
from service.connection.SignalClient import SignalClient
from service.ml.AiService import AiService
from service.processing.processors.DocProcessor import DocProcessor
from service.processing.processors.ExcelProcessor import ExcelProcessor
from service.processing.AttachmentHandler import AttachmentHandler
from service.connection.MyDataBase import MyDataBase
from service.processing.processors.BatchProcessor import BatchProcessor
import traceback
from service.storage.LoggerManager import LoggerManager
from service.processing.processors.ExcelReport import ExcelReporter
from service.processing.converter.ColumnConverter import ColumnConverter
from service.storage.BackupData import BackupData
from service.users.UserService import UserService
import threading
import re
import random

class MyWorkFlow:
    REGEX_ANSWERS = [
        (r"(привіт|бажаю|міцного|здоров|вітаю|куку|вечір в хату)",
         ["Привіт! Що трапилося? 🤖", "Бажаю міцного! Я на зв'язку. 🫡", "Вітаю! Слухаю уважно.", "Вечір в хату", "Доброго раночку з кавочкой", "Здоровенькі були та й будьмо!"]),

        (r"(на все добре|пока|побачення)",
         ["На все добре! 🤖", "Тихої ночі. 🫡", "Я пішов спатки.", "Будьмо!"]),

        (r"(як справи|шо там|як воно|як сам)",
         ["Сракопад жахливий! 🚀", "Тримаємось на багах та каві. ☕", "Все стабільно: факапи за розкладом."]),

        (r"(хто ти|що ти за звір|ти хто)",
         ["Я бот-ботяра-саботяра, повний шаїчечки та багів. 🛠️"]),

        (r"(паляниця|укрзалізниця)",
         ["Укрзалізниця! 🇺🇦"]),

        (r"(слава україні|героям слава)",
         ["Героям Слава! 🇺🇦"]),

        (r"(слава нації)",
         ["Смерть ворогам! 🇺🇦"])

    ]


    def __init__(self, db: MyDataBase = None):
        self.log_manager = LoggerManager()
        self.logger = self.log_manager.get_logger()

        self.excelProcessor:ExcelProcessor = None
        self.wordProcessor:DocProcessor = None
        self.reporter:ExcelReporter = None
        self.attachmentHandler:AttachmentHandler = None
        self.signalClient:SignalClient = SignalClient()
        self.emailClient:EmailClient = EmailClient()
        self.db: MyDataBase = db if db is not None else MyDataBase()
        self.excelFilePath = None
        self._excel_lock = threading.Lock()
        self.aiService = AiService()

        self.backuper = BackupData(self.log_manager)

    def initExcelProcessor(self, excelFilePath):
        self.excelProcessor = ExcelProcessor(excelFilePath, log_manager=self.log_manager,)
        self.reporter = ExcelReporter(self.excelProcessor, log_manager=self.log_manager,)
        self.excelFilePath = excelFilePath

    async def parseSignalData(self, data: dict):
        """Розбирає JSON-RPC пакет від Signal та запускає відповідну логіку."""
        try:
            params = data.get("params", {})
            envelope = params.get("envelope", {})

            if "dataMessage" in envelope:
                msg = envelope["dataMessage"]
                source = (envelope.get("source")
                          or envelope.get("sourceNumber")
                          or "Невідомий")
                source_uuid = envelope.get("sourceUuid")
                timestamp = msg.get("timestamp")
                group_info = msg.get("groupInfo")
                group_id = group_info.get("groupId") if group_info else None
                message_text = msg.get("message", "")
                attachments = msg.get("attachments", [])

                if attachments:
                    self.logger.debug("--- ПОЧАТОК ОБРОБКИ ВКЛАДЕНЬ ---")
                    for att in attachments:
                        att_id = att.get("id")
                        filename = att.get("filename")
                        self.logger.debug(f"📎 Отримано файл: {filename} (ID: {att_id})")

                        self.attachmentHandler = AttachmentHandler(self)
                        file_process_messages = self.attachmentHandler.handle_attachment(att_id, filename)

                        emoji = "➕" if len(file_process_messages) == 0 else "⚠️"
                        self.signalClient.send_reaction(group_id, source, emoji, source_uuid, timestamp)
                    self.logger.debug("--- КІНЕЦЬ ОБРОБКИ ВКЛАДЕНЬ ---")

                elif message_text:
                    response = await self._get_text_response(source, message_text)
                    self.logger.debug(f"🤖 Відповідаю: {response}")
                    if group_id is None:
                        self.signalClient.send_message(source, response)

            elif "syncMessage" in envelope:
                sync_msg = envelope["syncMessage"]
                if "sentMessage" in sync_msg:
                    sent = sync_msg["sentMessage"]
                    dest = (sent.get("destinationNumber")
                            or sent.get("destinationUuid")
                            or "когось")
                    text = sent.get("message", "")
                    if text:
                        return f"📤 ВИ НАПИСАЛИ до {dest}: {text}"

        except Exception as e:
            self.logger.debug("--- ПОВНИЙ СТЕК ПОМИЛКИ ---")
            self.logger.debug(traceback.format_exc())
            return f"❌ Помилка парсингу: {e}"

        return None

    async def _get_text_response(self, user_id: str, text: str) -> str:
        """Повертає відповідь з урахуванням стану меню та регулярних виразів."""
        normalized = text.lower().strip()

        # 2. ПРІОРИТЕТ: Робота з меню
        # Якщо в тексті є ключові слова меню АБО якщо користувач уже в якомусь стані (не START)
        if not hasattr(self, '_user_service'):
            self._user_service = UserService(self.db, self.signalClient, self.emailClient)

        current_state = self._user_service.get_user_state(user_id)

        # 3. ФІЛЬТР: Регулярні вирази для вільного спілкування
        for pattern, responses in self.REGEX_ANSWERS:
            if re.search(pattern, normalized):
                import random
                return random.choice(responses)

        # Якщо юзер написав "меню" або він вже знаходиться в процесі вибору (цифри 1, 2, 3...)
        if any(word in normalized for word in ['меню', 'menu', 'help']) or current_state != "START":
            return self._handle_menu(user_id, normalized)

        # 4. ФОЛБЕК: Якщо нічого не підійшло
        return "Моя твоя не розуміти. Напиши 'меню', щоб побачити варіанти. 🔕"

    def _handle_menu(self, user_id: str, text: str) -> str:
        """Обробляє стан-машину текстового меню."""
        # UserService — легкий, можна зберігати як поле, а не створювати щоразу
        if not hasattr(self, '_user_service'):
            self._user_service = UserService(self.db, self.signalClient, self.emailClient)

        user_service = self._user_service
        current_state = user_service.get_user_state(user_id)

        self.logger.debug(f"МЕНЮ: юзер={user_id}, стан={current_state}, текст='{text}'")

        MAIN_MENU = "Ви у Головному меню:\n1. Різна обробка\n2. Статистика\n3. Вихід"
        PROCESS_MENU = "ОБРОБКА MENU:\n1. Batch обробка файлів\n2. Конвертація полів\n0. Вихід"
        MENU_PROMPT = "Напишіть 'меню' для початку роботи."
        STAT_MENU = "Статистика. 0. Вихід"

        print('>> current state ' + str(current_state))
        if text in ("меню", "start", "menu"):
            user_service.set_user_state(user_id, "MAIN_MENU")
            return MAIN_MENU

        if current_state == "MAIN_MENU":
            if text == "1":
                user_service.set_user_state(user_id, "PROCESS")
                return PROCESS_MENU
            if text == "2":
                user_service.set_user_state(user_id, "STAT")
                return STAT_MENU
            if text in ("4", "вихід"):
                user_service.set_user_state(user_id, "START")
                return MENU_PROMPT
            if text == "0":
                return MAIN_MENU

        elif current_state == "PROCESS":
            if text == "0":
                user_service.set_user_state(user_id, "MAIN_MENU")
                return MAIN_MENU
            if text in ("1", "batch"):
                #with self._excel_lock:
                    # BatchProcessor(self.log_manager, self.excelFilePath).start_processing(0)
                return "Зараз вимкнено"
            if text in ("2", "convert"):
                # with self._excel_lock:
                #    ColumnConverter(self.excelFilePath, self.log_manager).convert()
                return "Зараз вимкнено"

        elif current_state == "STAT":
            if text == "0":
                user_service.set_user_state(user_id, "MAIN_MENU")
                return MAIN_MENU
            return "Фігня-цифра"

        return MENU_PROMPT


    async def get_ai_answer(self, user_text) -> str:
        ai_answer = await self.aiService.get_response(user_text)
        return ai_answer
