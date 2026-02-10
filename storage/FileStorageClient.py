import io
from abc import ABC, abstractmethod
import datetime
import config
import os

class FileStorageClient(ABC):
    @abstractmethod
    def get_file_buffer(self, path: str) -> io.BytesIO:
        pass

    @abstractmethod
    def save_file_from_buffer(self, path: str, buffer: io.BytesIO):
        pass

    @abstractmethod
    def make_dirs(self, path: str):
        pass

    @abstractmethod
    def copy_file(self, source_path: str, dest_path: str):
        """Спільний метод для копіювання файлів"""
        pass

    def list_files(self, path: str) -> list:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @abstractmethod
    def close(self):
        pass

    def get_target_document_folder_path(self, effective_date: datetime.date) -> str:
        # 1. Формуємо назви для кожного рівня
        year_folder = effective_date.strftime(config.FOLDER_YEAR_FORMAT)
        month_folder = effective_date.strftime(config.FOLDER_MONTH_FORMAT)
        day_folder = effective_date.strftime(config.FOLDER_DAY_FORMAT)

        separator = "\\" if config.DOCUMENT_STORAGE_PATH.startswith("\\\\") else os.sep

        # 3. Збираємо шлях
        target_path = (
            f"{config.DOCUMENT_STORAGE_PATH.rstrip(separator)}"
            f"{separator}{year_folder}"
            f"{separator}{month_folder}"
            f"{separator}{day_folder}"
        )

        return target_path