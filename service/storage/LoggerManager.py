import logging
import os
import config

class LoggerManager:
    def __init__(self, log_name="DeserterBot", logging_level=logging.DEBUG):
        self.log_dir = "logs"
        self._ensure_log_dir()
        self.log_file = os.path.join(self.log_dir, config.LOGGER_FILE_NAME)

        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.setLevel(logging_level)

        # Запобігаємо дублюванню логів, якщо об'єкт створюється двічі
        if not self.logger.handlers:
            self._setup_handlers()

    def _ensure_log_dir(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _setup_handlers(self):
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Файловий хендлер
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

        # Консольний хендлер
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def clear_log(self, keep_lines=5):
        try:
            if os.path.exists(self.log_file):
                # 1. Читаємо всі рядки
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # 2. Залишаємо тільки хвіст (наприклад, останні 5 рядків)
                tail = lines[-keep_lines:] if len(lines) > keep_lines else lines

                # 3. Перезаписуємо файл цим хвостом
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.writelines(tail)

                self.logger.debug(f"--- 🔄 Лог очищено. Залишено останніх рядків: {len(tail)} ---")
        except Exception as e:
            # Важливо не дати скрипту впасти, якщо лог зайнятий іншим процесом
            print(f"Помилка при очищенні логу: {e}")

    def get_logger(self):
        return self.logger

    def get_log_path(self):
        return self.log_file
