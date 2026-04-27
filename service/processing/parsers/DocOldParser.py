import sys
import subprocess
import os
import regex as re
import shutil
import tempfile

from config import is_win
from .BaseFileParser import BaseFileParser
import config

class DocOldParser(BaseFileParser):

    def get_full_text(self):

        text = self._try_textutil()

        # Якщо textutil повернув сміття (немає кирилиці або забагато дивних символів)
        if not text or self._is_garbage(text):
            self.logger.warning("⚠️ textutil не впорався, пробуємо antiword...")
            if config.is_win():
                text = self._try_antiword_win()
            else:
                text = self._try_antiword()

        # 2. Якщо Antiword не зміг (наприклад, файл пошкоджений) — резервний Word
        if not text or self._is_garbage(text):
            self.logger.warning(f"⚠️ Antiword не зміг ({os.path.basename(self.file_path)}), запускаю MS Word...")
            return self._try_windows_word()

        return text

    def _try_textutil(self):
        try:
            result = subprocess.run(
                ['textutil', '-convert', 'txt', '-stdout', self.file_path],
                capture_output=True
            )
            return result.stdout.decode('utf-8', errors='replace')
        except:
            return ""

    def _try_antiword(self):
        try:
            # antiword чудово витягує текст зі старих .doc
            result = subprocess.run(
                ['antiword', '-m', 'UTF-8', self.file_path],
                capture_output=True
            )
            return result.stdout.decode('utf-8', errors='replace')
        except Exception as e:
            self.logger.error(f"❌ antiword не встановлено або помилка: {e}")
            return ""

    def _try_antiword_win(self):
        # Шлях до папки, де лежить antiword.exe
        base_dir = config.PACKAGES_ANTIWORD_HOME_PATH
        exe_path = os.path.join(base_dir, "bin", "antiword.exe")

        # Вказуємо Antiword, де шукати таблиці кодувань (Mapping tables)
        # Він шукає папку .antiword всередині вказаного шляху
        antiword_home = os.path.join(base_dir, "home")

        # Створюємо копію файлу з простим ім'ям (щоб уникнути проблем з кирилицею в шляху)
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"anti_tmp_{os.getpid()}.doc")

        try:
            shutil.copy2(os.path.abspath(self.file_path), temp_file)

            env = os.environ.copy()
            env["ANTIWORDHOME"] = antiword_home
            env["HOME"] = antiword_home

            result = subprocess.run(
                [exe_path, '-m', 'UTF-8', temp_file],
                capture_output=True,
                env=env,
                text=False,  # Читаємо як байти, щоб уникнути помилок декодування Windows
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            if result.returncode == 0:
                return result.stdout.decode('utf-8', errors='replace')
            else:
                stderr = result.stderr.decode(errors='replace')
                self.logger.debug(f"Antiword stderr: {stderr}")
                return ""
        except Exception as e:
            self.logger.debug(f"Antiword error: {e}")
            return ""
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def _try_windows_word(self):
        """Резервний метод через COM (тільки якщо Antiword підвів)"""
        if not is_win(): return None
        import win32com.client
        import pythoncom

        word = None
        try:
            pythoncom.CoInitialize()
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False

            abs_path = os.path.abspath(self.file_path)
            doc = word.Documents.Open(abs_path, ReadOnly=True, Visible=False)

            text = doc.Content.Text
            text = text.replace('\r', '\n')  # Виправляємо злипання рядків

            doc.Close(False)
            return text
        except Exception as e:
            self.logger.error(f"❌ Помилка MS Word: {e}")
            return ""
        finally:
            if word:
                try:
                    word.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()

    def _is_garbage(self, text):
        if not text or len(text.strip()) < 10:
            return True
        return not bool(re.search(r'[а-яіїєґА-ЯІЇЄҐ]', text))