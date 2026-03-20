# service/config_service.py
import sqlite3
import config
from typing import List
from domain.sys_config import SysConfig


class ConfigService:
    # 💡 ДЖЕРЕЛО ПРАВДИ ДЛЯ НОВИХ ПАРАМЕТРІВ
    DEFAULT_SETTINGS = [
        # Основні
        SysConfig(key_name='PROCESS_DOC', category='Основні', value='True', value_type='bool', description='Копіювати документ з Signal у цільову папку'),
        SysConfig(key_name='PROCESS_XLS', category='Основні', value='True', value_type='bool', description='Одразу записувати дані в Excel'),
        SysConfig(key_name='DAILY_BACKUPS', category='Основні', value='True', value_type='bool', description='Робити щоденні бекапи БД та Excel'),
        SysConfig(key_name='SIGNAL_BOT', category='Основні', value='False', value_type='bool', description='Підключатися до Signal та обробляти вкладення'),
        SysConfig(key_name='SAVE_EXCEL_AT_CLOSE', category='Основні', value='False', value_type='bool', description='Зберігати всі зміни в Excel при закритті програми'),

        # Шляхи
        SysConfig(key_name='DOC_DIR', category='Шляхи', value='exchange\\ДД', value_type='str', description='Головна папка для документів'),
        SysConfig(key_name='EXCEL_DIR', category='Шляхи', value='exchange\\projekt407', value_type='str', description='Папка зберігання Excel'),
        SysConfig(key_name='BACKUP_DIR', category='Шляхи', value='exchange\\projekt407\\backups', value_type='str', description='Папка для бекапів'),
        SysConfig(key_name='DESERTER_TAB_NAME', category='Шляхи', value='А0224', value_type='str', description='Назва основного аркуша СЗЧ в Excel'),
        SysConfig(key_name='DESERTER_RESERVE_TAB_NAME', category='Шляхи', value='А7018', value_type='str', description='Назва резервного аркуша СЗЧ в Excel'),

        # Час та Логіка
        SysConfig(key_name='DAY_ROLLOVER_HOUR', category='Час та Логіка', value='16', value_type='int', description='Година (0-23) переходу на наступний день',
                  validation_rule='min:0|max:23'),
        SysConfig(key_name='BACKUP_KEEP_DAYS', category='Час та Логіка', value='30', value_type='int', description='Скільки днів зберігати старі бекапи',
                  validation_rule='min:1|max:365'),
        SysConfig(key_name='CHECK_INBOX_EVERY_SEC', category='Час та Логіка', value='60.0', value_type='float', description='Інтервал перевірки інбоксу (сек)',
                  validation_rule='min:10.0'),

        # Технічні
        SysConfig(key_name='EXCEL_CHUNK_SIZE', category='Технічні', value='2000', value_type='int', description='Розмір блоку для читання Excel', validation_rule='min:100'),
        SysConfig(key_name='LOG_MONITORING_MAX_LINES', category='Технічні', value='1000', value_type='int', description='Максимальна кількість рядків у логах',
                  validation_rule='min:100|max:5000')
    ]

    def __init__(self, db_path: str = config.DB_NAME):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def sync_defaults(self):
        """Додає нові параметри, оновлює метадані існуючих, але не чіпає value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT key_name FROM sys_config")
            existing_keys = {row['key_name'] for row in cursor.fetchall()}

            for setting in self.DEFAULT_SETTINGS:
                if setting.key_name not in existing_keys:
                    cursor.execute("""
                        INSERT INTO sys_config (category, key_name, value, value_type, description, validation_rule)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (setting.category, setting.key_name, setting.value, setting.value_type, setting.description, setting.validation_rule))
                else:
                    cursor.execute("""
                        UPDATE sys_config 
                        SET category = ?, description = ?, validation_rule = ?, value_type = ?
                        WHERE key_name = ?
                    """, (setting.category, setting.description, setting.validation_rule, setting.value_type, setting.key_name))
            conn.commit()

    def get_all(self) -> List[SysConfig]:
        """Отримує всі налаштування і повертає список Pydantic-моделей"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sys_config ORDER BY category, id")
            # 💡 Розпаковуємо словник одразу в Pydantic модель
            return [SysConfig(**dict(row)) for row in cursor.fetchall()]

    def update_value(self, key_name: str, new_value: str) -> bool:
        """Оновлює значення з UI"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sys_config SET value = ? WHERE key_name = ?", (str(new_value), key_name))
            conn.commit()
            return cursor.rowcount > 0

    def apply_to_runtime(self):
        """Перезаписує змінні в config.py в пам'яті."""
        configs = self.get_all()
        for conf in configs:
            setattr(config, conf.key_name, conf.get_typed_value())