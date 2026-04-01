from service.connection.EmailClient import EmailClient
from service.connection.SignalClient import SignalClient
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

class MyWorkFlow:

    ANSWERS = {
        "привіт": "Привіт! Що треба? 🤖",
        "як справи": "Сракопад жахливий! 🚀",
        "хто ти": "Я бот-ботяра-саботяра, повний шаїчечки та багів",
        "паляниця": "Укрзалізниця! 🇺🇦",
        "слава Україні": "Героям Слава!"
    }

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

        self.backuper = BackupData(self.log_manager)

    def initExcelProcessor(self, excelFilePath):
        self.excelProcessor = ExcelProcessor(excelFilePath, log_manager=self.log_manager,)
        self.reporter = ExcelReporter(self.excelProcessor, log_manager=self.log_manager,)
        self.excelFilePath = excelFilePath

    def parseSignalData(self, data: dict):
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
                    response = self._get_text_response(source, message_text)
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

    def _get_text_response(self, user_id: str, text: str) -> str:
        """Повертає відповідь на текстове повідомлення (меню або стандартна відповідь)."""
        normalized = text.lower().strip()

        if normalized in self.ANSWERS:
            return self.ANSWERS[normalized]

        return self._handle_menu(user_id, normalized)

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

        if text in ("меню", "start", "menu"):
            user_service.set_user_state(user_id, "MAIN_MENU")
            return MAIN_MENU

        if current_state == "MAIN_MENU":
            if text == "1":
                user_service.set_user_state(user_id, "PROCESS")
                return PROCESS_MENU
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
                with self._excel_lock:
                    BatchProcessor(self.log_manager, self.excelFilePath).start_processing(0)
                return "OK"
            if text in ("2", "convert"):
                with self._excel_lock:
                    ColumnConverter(self.excelFilePath, self.log_manager).convert()
                return "OK"

        elif current_state == "STAT":
            if text == "0":
                user_service.set_user_state(user_id, "MAIN_MENU")
                return MAIN_MENU
            return "Фігня-цифра"

        return MENU_PROMPT


    async def get_ai_answer(self, user_text):
        # Спочатку перевіряємо "швидкі команди" (Паляниця і т.д.)
        if user_text.lower() in self.ANSWERS:
            return self.ANSWERS[user_text.lower()]

        # Якщо команди немає — запитуємо нейронку
        try:
            return ''
            '''
            response = await client.chat.completions.create(
                model="gpt-4o",  # або локальна "llama3"
                messages=[
                    {"role": "system", "content": "Ти — бот-саботяра. Твій стиль: суміш програміста та військового."},
                    {"role": "user", "content": user_text}
                ]
            )
            return response.choices[0].message.content
            '''
        except:
            return "Мозок заклинило, йду на перезавантаження... 😵‍💫"