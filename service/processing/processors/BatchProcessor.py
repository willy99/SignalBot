import os
from datetime import datetime, timedelta

import config
from service.storage.LoggerManager import LoggerManager
from service.storage.StorageFactory import StorageFactory
from service.processing.processors.ExcelProcessor import ExcelProcessor
from service.processing.processors.DocProcessor import DocProcessor
import traceback

class BatchProcessor:
    def __init__(self, log_manager: LoggerManager, excel_file_path):
        # Вмикаємо режим батчу
        self.excelProcessor = ExcelProcessor(excel_file_path, log_manager=log_manager, batch_processing=True)
        self.fileProxy = StorageFactory.create_client(excel_file_path, log_manager)
        self.log_manager = log_manager
        self.logger = self.log_manager.get_logger()

    def start_processing(self, days_back=1):
        self.logger.debug("🚀 >>> BATCH STARTED")

        try:
            # 1. Формуємо список папок для читання (сьогодні + попередні дні)
            folders_to_scan = self._get_folders_list(days_back)

            # 2. Збираємо всі файли з цих папок через SMB
            files_to_process = []

            with self.fileProxy as smb:
                for folder in folders_to_scan:
                    files = smb.list_files(folder)  # Припустимо, у вас є такий метод
                    files_to_process.extend([(folder, f) for f in files if f.endswith(('.pdf', '.doc', '.docx'))])

                if not files_to_process:
                    self.logger.debug("📭 Немає нових файлів для обробки в " + str(folder))
                    return

                # 3. Обробляємо кожен файл
                for folder, file_name in files_to_process:
                    self.logger.debug('--------------------------🔓 BEGIN ------------------------------------------ ')
                    full_path = self.fix_slashes(os.path.join(folder, file_name))
                    self.logger.debug(f"📄 Обробка: {file_name}")
                    current_folder_date = self._extract_date_from_folder(folder)

                    try:
                        local_path = os.path.join(config.TMP_DIR, file_name)
                        #copy
                        file_data = smb.get_file_buffer(None, full_path)
                        if file_data:
                            with open(local_path, 'wb') as f:
                                f.write(file_data.getbuffer())

                        doc_processor = DocProcessor(
                            self.log_manager,
                            local_path,
                            file_name,
                            insertion_date=current_folder_date
                        )
                        data_for_excel = doc_processor.process()
                        if data_for_excel:
                            self.excelProcessor.upsert_record(data_for_excel)
                    except Exception as e:
                        self.logger.error(f"❌ Помилка у файлі {file_name}: {e}")
                    finally:
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except Exception as cleanup_error:
                                self.logger.error(f"⚠️ Не вдалося видалити {file_name}: {cleanup_error}")
                        self.logger.debug('--------------------------🔓 END -------------------------------------------- ')

                # 4. ФІНАЛЬНЕ ЗБЕРЕЖЕННЯ (один раз на весь батч)
                self.logger.debug("💾 Збереження результатів у Excel...")
                self.excelProcessor.save(smb)

        except Exception as e:
            self.logger.error(f"🔴 КРИТИЧНА ПОМИЛКА БАТЧУ: {e}")
            traceback.print_exc()
        finally:
            self.excelProcessor.close()
            self.logger.debug("🏁 >>> BATCH FINISHED")

    def _get_folders_list(self, days_back: int):
        """
        Генерує список коректних ієрархічних шляхів до папок за останні N днів.
        """
        folders = []
        today = datetime.now().date()

        for i in range(days_back + 1):
            target_date = today - timedelta(days=i)
            # Використовуємо ваш новий метод для генерації шляху Рік\Місяць\День
            path = self.fileProxy.get_target_folder_path(target_date, config.DOCUMENT_STORAGE_PATH)
            folders.append(path)

        return folders

    def fix_slashes(self, path: str) -> str:
        # Примусова заміна всіх прямих слешів на зворотні
        return path.replace('/', '\\')


    def _extract_date_from_folder(self, folder_path: str) -> datetime:
        """Витягує дату з ієрархічного шляху (Рік/Місяць/День)."""
        try:
            # Нормалізуємо шлях, щоб роздільники були однаковими
            normalized = os.path.normpath(folder_path)
            parts = normalized.split(os.sep)

            # Беремо останні 3 частини (напр. ..., '2026', '02', '08')
            year, month, day = parts[-3], parts[-2], parts[-1]

            return datetime(int(year), int(month), int(day))
        except (ValueError, IndexError):
            # Якщо шлях не відповідає структурі, повертаємо "зараз" як фолбек
            return datetime.now()