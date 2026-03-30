import smtplib
from email.mime.text import MIMEText
import config


class EmailClient:
    def __init__(self):
        self.smtp_server = config.EMAIL_SMTP_SERVER
        self.smtp_port = config.EMAIL_SMTP_PORT
        self.sender_email = config.EMAIL_SENDER
        self.sender_password = config.EMAIL_PASSWORD

    def send_verification_code(self, receiver_email: str, code: str) -> bool:
        """
        Відправка коду підтвердження на Email.
        Метод синхронний, має викликатися через run.io_bound.
        """
        msg = MIMEText(f"Ваш код підтвердження для входу в систему: {code}\n\n"
                       f"Код дійсний протягом 10 хвилин.")

        msg['Subject'] = '🔐 Код підтвердження 2FA'
        msg['From'] = self.sender_email
        msg['To'] = receiver_email

        try:
            # Використовуємо SMTP_SSL для безпечного з'єднання
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            return True

        except smtplib.SMTPAuthenticationError:
            print("Помилка: Невірний логін або пароль до SMTP сервера.")
            raise ValueError("Помилка авторизації пошти")
        except Exception as e:
            print(f"Критична помилка відправки Email: {e}")
            raise e