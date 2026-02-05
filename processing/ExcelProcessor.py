import openpyxl
import os
import warnings
from copy import copy
from config import DESERTER_TAB_NAME


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

            print(f'>> INIT EXCEL PROCESSOR...')
            # keep_vba=True для вашого .xlsm файлу
            self.workbook = openpyxl.load_workbook(self.file_path, keep_vba=True)
            self.sheet = self.workbook[DESERTER_TAB_NAME]
            self._build_column_map()
            print(f'>> EXCEL LAST ROW::  {self.find_last_row()}')

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

    def insert_record(self, records_list):
        if not records_list:
            return

        next_row = self.sheet.max_row + 1
        last_row = next_row - 1
        max_col = self.sheet.max_column

        # 1. Визначаємо ID (стовбець A)
        # Визначаємо останній ID один раз перед циклом
        last_row = next_row - 1
        last_val = self.sheet.cell(row=last_row, column=1).value
        try:
            current_id = int(last_val) if last_val and str(last_val).isdigit() else 0
        except:
            current_id = 0

        # 2. Перебір кожного словника в масиві
        for data_dict in records_list:
            current_id += 1

            # Визначаємо клітинку-зразок для стилів (завжди беремо з останнього рядка, що БУВ до вставки)
            # Або з попереднього щойно створеного
            sample_row = next_row - 1 if next_row > 2 else 1

            for col_idx in range(1, max_col + 1):
                new_cell = self.sheet.cell(row=next_row, column=col_idx)
                old_cell = self.sheet.cell(row=sample_row, column=col_idx)

                # Копіюємо стилі
                if old_cell.has_style:
                    new_cell.font = copy(old_cell.font)
                    new_cell.border = copy(old_cell.border)
                    new_cell.number_format = copy(old_cell.number_format)

                    new_alignment = copy(old_cell.alignment)
                    new_alignment.wrapText = False  # Один рядок
                    new_alignment.vertical = 'center'
                    new_cell.alignment = new_alignment

            # 3. Записуємо ID та дані
            self.sheet.cell(row=next_row, column=1).value = current_id

            for col_name, value in data_dict.items():
                idx = self.column_map.get(col_name.lower())
                if idx:
                    self.sheet.cell(row=next_row, column=idx).value = value

            # 4. Фіксуємо висоту
            self.sheet.row_dimensions[next_row].height = 15

            # Переходимо до наступного рядка для наступного словника
            next_row += 1

        # print(f"Додано запис у рядок {next_row}")

    def save(self):
        self.workbook.save(self.file_path)
        print("--- ✔️EXCEL - додано інформація")