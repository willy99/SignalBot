from dics.deserter_xls_dic import REGEX_ANSWERS
from service.connection.EmailClient import EmailClient
from service.connection.SignalClient import SignalClient
from service.processing.processors.DocProcessor import DocProcessor
from service.processing.processors.ExcelProcessor import ExcelProcessor
from service.processing.workflow.AttachmentHandler import AttachmentHandler
from service.connection.MyDataBase import MyDataBase
import traceback

from service.processing.workflow.SignalBotHandler import SignalBotHandler
from service.storage.LoggerManager import LoggerManager
from service.processing.processors.ExcelReport import ExcelReporter
from service.storage.BackupData import BackupData
from service.users.UserService import UserService
import threading
import re
import html

class MyWorkFlow:

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
        self._bot_handler: SignalBotHandler = None

    def initExcelProcessor(self, excelFilePath):
        self.excelProcessor = ExcelProcessor(excelFilePath, log_manager=self.log_manager,)
        self.reporter = ExcelReporter(self.excelProcessor, log_manager=self.log_manager,)
        self.excelFilePath = excelFilePath

        user_service = UserService(self.db, self.signalClient, self.emailClient)
        self._bot_handler = SignalBotHandler(
            user_service=user_service,
            reporter=self.reporter,
            log_manager=self.log_manager,
            excel_file_path=self.excelFilePath,
            excel_lock=self._excel_lock,
            excel_processor=self.excelProcessor
        )

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
                    self._handle_attachments(attachments, group_id, source, source_uuid, timestamp)
                elif message_text:
                    await self._handle_text_message(source, group_id, message_text)


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

    async def _handle_text_message(self, source: str, group_id, message_text: str) -> None:
        """Обробляє вхідне текстове повідомлення."""
        normalized = message_text.lower().strip()

        # Швидкі відповіді без авторизації (привітання тощо)
        for pattern, responses in REGEX_ANSWERS:
            if re.search(pattern, normalized):
                import random
                response = random.choice(responses)
                self.signalClient.send_message(source, response)
                return
        # Повна обробка з авторизацією та стейт-машиною
        if self._bot_handler is None:
            self.logger.warning("Signal-бот: _bot_handler не ініціалізовано")
            response = "⚠️ Система ще не готова. Спробуйте пізніше."
        else:
            response = await self._bot_handler.handle(source, message_text)

        self.logger.debug(f"🤖 Відповідаю {source}: {response[:60]}...")

        # Відповідаємо тільки в особистих повідомленнях, не в групах
        if group_id is None and response:
            self.signalClient.send_message(source, response)


    def _handle_attachments(self, attachments: list, group_id, source: str, source_uuid, timestamp) -> None:
        """Обробляє вхідні вкладення."""
        self.logger.debug("--- ПОЧАТОК ОБРОБКИ ВКЛАДЕНЬ ---")
        for att in attachments:
            att_id   = att.get("id")
            filename = att.get("filename")
            self.logger.debug(f"📎 Отримано файл: {filename} (ID: {att_id})")

            handler = AttachmentHandler(self)
            messages = handler.handle_attachment(att_id, filename)

            emoji = "➕" if len(messages) == 0 else "⚠️"
            self.signalClient.send_reaction(
                group_id, source, emoji, source_uuid, timestamp
            )
        self.logger.debug("--- КІНЕЦЬ ОБРОБКИ ВКЛАДЕНЬ ---")