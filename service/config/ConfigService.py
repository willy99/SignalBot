import config
from typing import List
from domain.sys_config import SysConfig


class ConfigService:
    """
    Сервіс системних налаштувань.
    Використовує переданий екземпляр MyDataBase — власних з'єднань не відкриває.
    """

    DEFAULT_SETTINGS = [
        # Основні
        SysConfig(key_name='PROCESS_DOC',       category='Основні', value='True',  value_type='bool', description='Копіювати документ з Signal у цільову папку'),
        SysConfig(key_name='PROCESS_XLS',       category='Основні', value='True',  value_type='bool', description='Одразу записувати дані в Excel'),
        SysConfig(key_name='DAILY_BACKUPS',      category='Основні', value='True',  value_type='bool', description='Робити щоденні бекапи БД та Excel'),
        SysConfig(key_name='SIGNAL_BOT',         category='Основні', value='False', value_type='bool', description='Підключатися до Signal та обробляти вкладення'),
        SysConfig(key_name='SAVE_EXCEL_AT_CLOSE',category='Основні', value='False', value_type='bool', description='Зберігати всі зміни в Excel при закритті програми'),

        # Шляхи
        SysConfig(key_name='DOC_DIR',            category='Шляхи', value='exchange\\ДД',               value_type='str', description='Головна папка для документів'),
        SysConfig(key_name='EXCEL_DIR',          category='Шляхи', value='exchange\\projekt407',        value_type='str', description='Папка зберігання Excel'),
        SysConfig(key_name='BACKUP_DIR',         category='Шляхи', value='exchange\\projekt407\\backups',value_type='str', description='Папка для бекапів'),
        SysConfig(key_name='FOLDER_YEAR_FORMAT', category='Шляхи', value='%Y',                         value_type='str', description='Частина (рік) папки архівів'),
        SysConfig(key_name='FOLDER_MONTH_FORMAT',category='Шляхи', value='%m',                         value_type='str', description='Частина (місяць) папки архівів'),
        SysConfig(key_name='FOLDER_DAY_FORMAT',  category='Шляхи', value='%d.%m.%Y',                   value_type='str', description='Формат назви папки архівів. Приклад - %d.%m.%Y'),
        SysConfig(key_name='TMP_DIR',            category='Шляхи', value='~/tmp/',                     value_type='str', description='Локальна папка для тимчасового сміття'),

        # Час та Логіка
        SysConfig(key_name='DAY_ROLLOVER_HOUR',      category='Час та Логіка', value='16', value_type='int', description='Година (0-23) переходу на наступний робочий день', validation_rule='min:0|max:23'),
        SysConfig(key_name='BACKUP_KEEP_DAYS',       category='Час та Логіка', value='30', value_type='int', description='Скільки днів зберігати старі бекапи',              validation_rule='min:1|max:365'),
        SysConfig(key_name='CHECK_INBOX_EVERY_SEC',  category='Час та Логіка', value='60', value_type='int', description='Інтервал перевірки інбоксу (сек)',                  validation_rule='min:10|max:3600'),

        # Технічні
        SysConfig(key_name='LOG_MONITORING_MAX_LINES', category='Технічні', value='1000',          value_type='int', description='Максимальна кількість рядків у логах',    validation_rule='min:100|max:5000'),
        SysConfig(key_name='SOCKET_PATH',              category='Технічні', value='/tmp/signal-bot.sock', value_type='str', description='Шлях для сокету сігнала'),
        SysConfig(key_name='TCP_HOST',                 category='Технічні', value='127.0.0.1',     value_type='str', description='Хост для сокету сігнала'),
        SysConfig(key_name='TCP_PORT',                 category='Технічні', value='1234',          value_type='int', description='Порт для сокету сігнала',                  validation_rule='min:1|max:65535'),

        # Excel
        SysConfig(key_name='DESERTER_TAB_NAME',         category='Excel', value='А0224',   value_type='str', description='Назва основного аркуша СЗЧ в Excel'),
        SysConfig(key_name='DESERTER_RESERVE_TAB_NAME', category='Excel', value='А7018',   value_type='str', description='Назва аркуша БРЕЗівців в Excel'),
        SysConfig(key_name='EXCEL_CHUNK_SIZE',          category='Excel', value='2000',    value_type='int', description='Розмір блоку для читання Excel',     validation_rule='min:100|max:5000'),
        SysConfig(key_name='EXCEL_DATE_FORMAT',         category='Excel', value='%d.%m.%Y',value_type='str', description='Формат дат в Excel'),
        SysConfig(key_name='EXCEL_LIGHT_GRAY_COLOR',    category='Excel', value='EEEEEE',  value_type='str', description='Колір (HEX) для повідомлень',        validation_rule='regex:^[0-9A-Fa-f]{6}$'),
        SysConfig(key_name='EXCEL_BLUE_COLOR',          category='Excel', value='BDD7EE',  value_type='str', description='Колір (HEX) для відправок на ДБР',   validation_rule='regex:^[0-9A-Fa-f]{6}$'),
        SysConfig(key_name='EXCEL_SUPPORT_COLOR',       category='Excel', value='E8FFFE',  value_type='str', description='Колір (HEX) для супроводів',         validation_rule='regex:^[0-9A-Fa-f]{6}$'),

        # UI
        SysConfig(key_name='UI_DATE_FORMAT',    category='UI', value='DD.MM.YYYY', value_type='str', description='Формат дат для відображення в UI'),
        SysConfig(key_name='MAX_QUERY_RESULTS', category='UI', value='50',         value_type='int', description='Обмеження кількості записів без пейджеру', validation_rule='min:5|max:500'),
        SysConfig(key_name='RECORDS_PER_PAGE',  category='UI', value='10',         value_type='int', description='Кількість записів на сторінку',            validation_rule='min:5|max:500'),
    ]

    def __init__(self, db):
        """
        Приймає екземпляр MyDataBase.
        Власних з'єднань з SQLite не відкриває — всі запити йдуть через db.
        """
        self.db = db

    def sync_defaults(self) -> None:
        """
        Додає нові параметри та оновлює метадані існуючих.
        Значення (value) вже збережених параметрів не змінює.
        """
        existing_rows = self.db.__execute_fetchall__("SELECT key_name FROM sys_config")
        existing_keys = {row['key_name'] for row in existing_rows}

        for setting in self.DEFAULT_SETTINGS:
            if setting.key_name not in existing_keys:
                # Новий параметр — додаємо повністю
                self.db.__execute_query__(
                    """
                    INSERT INTO sys_config (category, key_name, value, value_type, description, validation_rule)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (setting.category, setting.key_name, setting.value,
                     setting.value_type, setting.description, setting.validation_rule)
                )
            else:
                # Параметр вже є — оновлюємо лише метадані, value не чіпаємо
                self.db.__execute_query__(
                    """
                    UPDATE sys_config
                    SET category = ?, description = ?, validation_rule = ?, value_type = ?
                    WHERE key_name = ?
                    """,
                    (setting.category, setting.description,
                     setting.validation_rule, setting.value_type, setting.key_name)
                )

    def get_all(self) -> List[SysConfig]:
        """Повертає всі налаштування у вигляді списку SysConfig."""
        rows = self.db.__execute_fetchall__(
            "SELECT * FROM sys_config ORDER BY category, id"
        )
        return [SysConfig(**dict(row)) for row in rows]

    def update_value(self, key_name: str, new_value: str) -> bool:
        """Оновлює значення одного параметра з UI."""
        result = self.db.__execute_query__(
            "UPDATE sys_config SET value = ? WHERE key_name = ?",
            (str(new_value), key_name)
        )
        # __execute_query__ повертає lastrowid; для UPDATE перевіряємо інакше
        # (lastrowid при UPDATE може бути 0, але операція пройшла якщо не None)
        return result is not None

    def apply_to_runtime(self) -> None:
        """Перезаписує змінні модуля config значеннями з бази (в пам'яті)."""
        for conf in self.get_all():
            setattr(config, conf.key_name, conf.get_typed_value())