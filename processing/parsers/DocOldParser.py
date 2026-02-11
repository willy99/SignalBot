from .BaseFileParser import BaseFileParser
import textract
import subprocess

class DocOldParser(BaseFileParser):

    def get_full_text(self):
        try:
            # Використовуємо системну утиліту Mac для конвертації .doc в чистий текст (stdout)
            result = subprocess.run(
                ['textutil', '-convert', 'txt', '-stdout', self.file_path],
                capture_output=True,
                text=False  # отримуємо байти
            )

            if result.returncode != 0:
                print(f"❌ Помилка textutil: {result.stderr.decode('utf-8')}")
                return ""

            # Декодуємо результат
            text = result.stdout.decode('utf-8', errors='replace')

            # Чистимо специфічні артефакти (якщо вони є)
            text = text.replace('\xa0', ' ')
            text = text.replace('\r', '\n')

            return text

        except Exception as e:
            print(f"❌ Критична помилка DocOldParser (textutil): {e}")
            return ""