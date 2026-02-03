from connection.SignalClient import SignalClient
from processing.ExcelProcessor import ExcelProcessor
from processing.AttachmentHandler import AttachmentHandler
from connection.MyDataBase import MyDataBase
from processing.Stat import Stat

class MyWorkFlow:

    ANSWERS = {
        "привіт": "Привіт! Що треба? 🤖",
        "як справи": "Сракопад жахливий! 🚀",
        "хто ти": "Я бот-ботяра-саботяра, повний шаїчечки та багів",
        "паляниця": "Укрзалізниця! 🇺🇦"
    }

    def __init__(self):
        self.excelProcessor = None
        self.wordProcessor = None
        self.attachmentHandler = AttachmentHandler(self)
        self.client = SignalClient()
        self.db = MyDataBase()
        self.stats = Stat()  # Створюємо об'єкт статистики

    def initExcelProcessor(self, file_path):
        self.excelProcessor = ExcelProcessor(file_path)



    def parseSignalData(self, data):
        """Витягує текст повідомлення та номер відправника з JSON-RPC пакету."""
        try:
            params = data.get("params", {})
            envelope = params.get("envelope", {})

            print(str(data))
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
                    for att in attachments:
                        att_id = att.get("id")
                        filename = att.get("filename")

                        print(f"📎 Отримано файл: {filename} (ID: {att_id})")
                        file_saved = self.attachmentHandler.handle_attachment(att_id, filename)

                elif message_text:
                    response = ''
                    print('Check is message in answers' + str(message_text) + ' ' + str(message_text in self.ANSWERS))
                    if message_text.lower() in self.ANSWERS:
                        response = self.ANSWERS[message_text.lower()]
                    else:
                        response = self.getResponseAndMove(source, message_text)
                    print(f"🤖 Відповідаю: {response}")
                    if group_id is None:
                        self.client.send_message(source, response)

                    # return f"📥 ВХІДНЕ від {source}: {message_text}"
                if file_saved:
                    self.client.send_reaction(
                        group_id,
                        recipient,
                        "➕",
                        source_uuid,
                        timestamp
                    )
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
            return f"❌ Помилка парсингу: {e}"

        return None

    def getResponseAndMove(self, user_id, text):
        # Отримуємо чистий стан
        current_state = self.db.get_user_state(user_id)
        text = text.lower().strip()

        print(f"DEBUG: User={user_id}, State={current_state}, Text='{text}'")

        # Глобальна команда для скидання або входу
        if text == "меню" or text == "start":
            self.db.set_user_state(user_id, "MAIN_MENU")
            return "Ви у Головному меню:\n1. Техпідтримка\n2. Статистика\n3. Вихід"

        # Логіка для стану MAIN_MENU
        if current_state == "MAIN_MENU":
            if text == "1":
                self.db.set_user_state(user_id, "SUPPORT")
                return "Опишіть вашу проблему або натисніть 0 для повернення."
            elif text == "2":
                # Стан не змінюємо, просто даємо інфу
                return self.stats.get_report()
            elif text == "3" or text == "вихід":
                self.db.set_user_state(user_id, "START")
                return "До зустрічі! Напишіть 'меню', щоб почати знову."
            elif text == "0":
                return "Ви вже у Головному меню. Виберіть пункт 1, 2 або 3."

        # Логіка для стану SUPPORT
        elif current_state == "SUPPORT":
            if text == "0":
                self.db.set_user_state(user_id, "MAIN_MENU")
                return "Повертаємось... Ви у Головному меню:\n1. Техпідтримка\n2. Статистика\n3. Вихід"
            else:
                # Тут можна додати збереження проблеми в БД
                return f"✅ Ваш запит '{text}' прийнято. Наші фахівці зв'яжуться з вами.\n\nНатисніть 0 для виходу в меню."

        # Якщо стан невідомий або START
        return "Напишіть 'меню' для початку роботи."