import io
from abc import ABC, abstractmethod
import datetime
import config
import os

class FileStorageClient(ABC):

    @abstractmethod
    def get_separator(self):
        pass

    @abstractmethod
    def get_file_buffer(self, path: str) -> io.BytesIO:
        pass

    @abstractmethod
    def save_file_from_buffer(self, path: str, buffer: io.BytesIO):
        pass

    @abstractmethod
    def save_json(self, path: str, data: list):
        pass

    @abstractmethod
    def load_json(self, path: str) -> list:
        pass

    @abstractmethod
    def make_dirs(self, path: str):
        pass

    @abstractmethod
    def copy_file(self, source_path: str, dest_path: str):
        """Спільний метод для копіювання файлів"""
        pass

    def list_files(self, path: str, silent: bool = False) -> list:
        pass

    @abstractmethod
    def remove_file(self, path: str):
        pass

    @abstractmethod
    def remove_dir(self, path: str, recursive: bool = True):
        pass

    @abstractmethod
    def walk(self, path: str):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @abstractmethod
    def close(self):
        pass

    def get_target_folder_path(self, effective_date: datetime.date, base_path: str) -> str:
        """Формує ієрархію папок Рік/Місяць/День на основі базового шляху."""
        year_folder = effective_date.strftime(config.FOLDER_YEAR_FORMAT)
        month_folder = effective_date.strftime(config.FOLDER_MONTH_FORMAT)
        day_folder = effective_date.strftime(config.FOLDER_DAY_FORMAT)

        separator = "\\" if base_path.startswith("\\\\") else os.sep

        target_path = (
            f"{base_path.rstrip(separator)}"
            f"{separator}{year_folder}"
            f"{separator}{month_folder}"
            f"{separator}{day_folder}"
        )

        return target_path
