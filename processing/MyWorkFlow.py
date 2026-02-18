from connection.SignalClient import SignalClient
from processing.ExcelProcessor import ExcelProcessor
from processing.AttachmentHandler import AttachmentHandler
from connection.MyDataBase import MyDataBase
from processing.Stat import Stat
from processing.BatchProcessor import BatchProcessor
import traceback
from storage.LoggerManager import LoggerManager
from report.ExcelReport import ExcelReporter
from processing.converter.ColumnConverter import ColumnConverter
from storage.BackupData import BackupData

class MyWorkFlow:

    ANSWERS = {
        "привіт": "Привіт! Що треба? 🤖",
        "як справи": "Сракопад жахливий! 🚀",
        "хто ти": "Я бот-ботяра-саботяра, повний шаїчечки та багів",
        "паляниця": "Укрзалізниця! 🇺🇦"
    }

    def __init__(self):
        self.log_manager = LoggerManager()
        self.logger = self.log_manager.get_logger()

        self.excelProcessor = None
        self.wordProcessor = None
        self.reporter = None
        self.attachmentHandler = AttachmentHandler(self)
        self.client = SignalClient()
        self.db = MyDataBase()
        self.stats = Stat()  # Створюємо об'єкт статистики
        self.excelFilePath = None


        self.backuper = BackupData(self.log_manager)

    def initExcelProcessor(self, excelFilePath):
        self.excelProcessor = ExcelProcessor(excelFilePath, log_manager=self.log_manager,)
        self.reporter = ExcelReporter(self.excelProcessor, log_manager=self.log_manager,)
        self.excelFilePath = excelFilePath

    def parseSignalData(self, data):
        """Витягує текст повідомлення та номер відправника з JSON-RPC пакету."""
        try:
            params = data.get("params", {})
            envelope = params.get("envelope", {})

            # self.logger.debug(str(data))
            # 1. Обробка вхідного повідомлення від когось іншого
            if "dataMessage" in envelope:
                self.stats.messagesProcessed += 1

                msg = envelope["dataMessage"]
                source = envelope.get("source") or envelope.get("sourceNumber") or "Невідомий"
                source_uuid = envelope.get("sourceUuid")  # Важливо для реакцій!
                timestamp = msg.get("timestamp")
                group_info = msg.get("groupInfo")
                recipient = source
                group_id = group_info.get("groupId") if group_info else None

                message_text = msg.get("message", "")

                attachments = msg.get("attachments", [])

                # process attachments
                file_saved = False
                if len(attachments) > 0:
                    self.logger.debug('--------------------------🔓 BEGIN ------------------------------------------ ')
                    for att in attachments:
                        att_id = att.get("id")
                        filename = att.get("filename")

                        self.logger.debug(f"📎 Отримано файл: {filename} (ID: {att_id})")
                        file_saved = self.attachmentHandler.handle_attachment(att_id, filename)
                        self.client.send_reaction(
                            group_id,
                            recipient,
                            "➕" if file_saved else "⚠️",
                            source_uuid,
                            timestamp
                        )
                    self.logger.debug('--------------------------🔓 END -------------------------------------------- ')


                elif message_text:
                    response = ''
                    self.logger.debug('Check is message in answers' + str(message_text) + ' ' + str(message_text in self.ANSWERS))
                    if message_text.lower() in self.ANSWERS:
                        response = self.ANSWERS[message_text.lower()]
                    else:
                        response = self.getResponseAndMove(source, message_text)
                    self.logger.debug(f"🤖 Відповідаю: {response}")
                    if group_id is None:
                        self.client.send_message(source, response)

                    # return f"📥 ВХІДНЕ від {source}: {message_text}"
            # 2. Обробка синхронізації (ви написали з телефону комусь)
            elif "syncMessage" in envelope:
                sync_msg = envelope["syncMessage"]
                if "sentMessage" in sync_msg:
                    sent = sync_msg["sentMessage"]
                    dest = sent.get("destinationNumber") or sent.get("destinationUuid") or "когось"
                    text = sent.get("message", "")
                    if text:
                        return f"📤 ВИ НАПИСАЛИ до {dest}: {text}"

        except Exception as e:
            stack_trace = traceback.format_exc()

            self.logger.debug("--- FULL STACK TRACE ---")
            self.logger.debug(stack_trace)
            return f"❌ Помилка парсингу: {e}"

        return None

    def getResponseAndMove(self, user_id, text):
        current_state = self.db.get_user_state(user_id)
        text = text.lower().strip()

        self.logger.debug(f"DEBUG: User={user_id}, State={current_state}, Text='{text}'")
        main_menu = "Ви у Головному меню:\n1. Різна обробка\n2. Статистика\n3. Вихід"
        process_menu = "ОБРОБКА MENU:\n1. Batch обробка файлів\n2. Конвертація полів\n3. Вихід"
        stat_menu = ":\n1. Статистика і звіти \n2. Звіт по СЗЧ - по підрозділам\n3. Звіт по СЗЧ - monthly\n4. Призвіща\n5. СЗЧ по підрозділам\n0. Вихід"
        menu_prompt = "Напишіть 'меню' для початку роботи."

        if text == "меню" or text == "start" or text == "menu":
            self.db.set_user_state(user_id, "MAIN_MENU")
            return main_menu

        if current_state == "MAIN_MENU":
            if text == "1":
                self.db.set_user_state(user_id, "PROCESS")
                return process_menu
            elif text == "2":
                self.db.set_user_state(user_id, "STAT")
                result = self.stats.get_report()
                result += stat_menu
                return result
            elif text == "4" or text == "вихід":
                self.db.set_user_state(user_id, "START")
                return menu_prompt
            elif text == "0":
                return main_menu

        elif current_state == 'PROCESS':
            if text == "0":
                self.db.set_user_state(user_id, "MAIN_MENU")
                return main_menu
            if text == "1" or text == 'batch':
                batch_processor = BatchProcessor(self, self.excelFilePath)
                batch_processor.start_processing(0)
                return "OK"
            if text == "2" or text == 'convert':
                column_converter = ColumnConverter(self.excelFilePath, self)
                column_converter.convert()
                return "OK"
        elif current_state == "STAT":
            if text == "0":
                self.db.set_user_state(user_id, "MAIN_MENU")
                return main_menu
            if text == "1":
                return self.stats.get_full_report()
            if text == "2":
                return self.reporter.get_summary_report()
            if text == "3":
                return self.reporter.get_montly_report()
            if text == "4":
                return self.reporter.get_all_names_report()
            if text == "5":
                return self.reporter.get_detailed_stats()
            else:
                return "Фігня-цифра"

        # Якщо стан невідомий або START
        return menu_prompt