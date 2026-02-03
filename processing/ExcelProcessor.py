import openpyxl
import os
import warnings
from dics.deserter_xls_dic import COLUMN_NAME


class ExcelProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.workbook = None
        self.sheet = None
        self.column_map = {}  # Тут зберігатимемо індекси {назва: номер_колонки}

        # Ігноруємо помилки дат, про які ви згадували раніше
        warnings.filterwarnings("ignore", category=UserWarning)
        self._load_workbook()

    def _load_workbook(self):
        """Внутрішній метод для відкриття файлу та мапінгу колонок"""
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Файл {self.file_path} не знайдено")

            # keep_vba=True для вашого .xlsm файлу
            self.workbook = openpyxl.load_workbook(self.file_path, keep_vba=True)
            self.sheet = self.workbook.active
            self._build_column_map()
            print(f'>> pib colkumn::  {self.column_map.get(COLUMN_NAME.lower())}')
            print(f'>> last row::  {self.find_last_row()}')

        except Exception as e:
            print(f"Помилка ініціалізації Excel: {e}")

    def _build_column_map(self):
        """Створює словник імен колонок для швидкого доступу"""
        if self.sheet:
            header_row = next(self.sheet.iter_rows(min_row=1, max_row=1))
            for cell in header_row:
                if cell.value:
                    clean_name = str(cell.value).strip().lower()
                    self.column_map[clean_name] = cell.column

    def find_last_row(self):
        return self.sheet.max_row

    def insert_record(self, data_dict):
        """
        Приймає словник з даними з Word, наприклад:
        {'піб': 'Іванов І.І.', 'стаття': '407', 'дата сзч': '20.01.2025'}
        """
        next_row = self.find_last_row() + 1

        for key, value in data_dict.items():
            col_idx = self.column_map.get(key.strip().lower())
            if col_idx:
                self.sheet.cell(row=next_row, column=col_idx).value = value
            else:
                print(f"Попередження: Колонку '{key}' не знайдено в Excel")

        print(f"Додано запис у рядок {next_row}")

    def save(self):
        self.workbook.save(self.file_path)
        print("Файл успішно збережено")