import pandas as pd
import json
from typing import Any
from config import ML_LOCAL_DESERTER_XLSX, ML_MODEL_JSON
from dics.deserter_xls_dic import *

class TrainingDataExporter:
    def __init__(self, file_path: str = ML_LOCAL_DESERTER_XLSX):
        self.file_path = file_path
        # Визначаємо зв'язки: де шукати (джерело) та що шукати (ціль)
        self.mapping = {
            'conditions_source': {
                'text_col': COLUMN_DESERT_CONDITIONS,
                'target_entities': [
                    COLUMN_DESERTION_DATE,
                    COLUMN_DESERTION_REGION,
                    COLUMN_DESERTION_PLACE,
                    COLUMN_RETURN_DATE
                ]
            },
            'bio_source': {
                'text_col': COLUMN_BIO,
                'target_entities': [
                    COLUMN_NAME,
                    COLUMN_ID_NUMBER,
                    COLUMN_TZK,
                    COLUMN_PHONE,
                    COLUMN_BIRTHDAY,
                    COLUMN_TITLE,
                    COLUMN_SERVICE_TYPE,
                    COLUMN_ADDRESS,
                    COLUMN_ENLISTMENT_DATE,
                    COLUMN_SUBUNIT
                ]
            }
        }

    def _find_entity_offsets(self, full_text: str, entity_value: Any, label: str) -> List:
        """Знаходить позицію (start, end) значення у великому тексті."""
        if pd.isna(entity_value) or str(entity_value).strip() in ["", "N/A", "None"]:
            return []

        val_str = str(entity_value).strip()

        # Шукаємо входження (case-insensitive пошук можна додати за потреби)
        start = full_text.find(val_str)
        if start == -1:
            return []

        end = start + len(val_str)
        return [start, end, label]

    def export_to_jsonl(self, output_file: str = ML_MODEL_JSON):
        """Метод для експорту даних у формат JSONL для навчання ML."""
        print(f"📖 Завантаження Excel: {self.file_path}")

        # Читаємо Excel (використовуємо engine='openpyxl' для .xlsx)
        df = pd.read_excel(self.file_path)

        records = []

        # Використовуємо звичайну ітерацію по рядках
        for index, row in df.iterrows():
            for source_key, cfg in self.mapping.items():
                full_text = row.get(cfg['text_col'])

                # Пропускаємо, якщо основне джерело тексту порожнє
                if pd.isna(full_text) or not str(full_text).strip():
                    continue

                full_text = str(full_text)
                entities = []

                # Шукаємо кожну сутність у цьому тексті
                for entity_col_name in cfg['target_entities']:
                    # Отримуємо реальну назву колонки з константи (якщо вони передані як рядки)
                    val = row.get(entity_col_name)
                    print('>>> val = ' + str(val) + ':' + entity_col_name)

                    offset = self._find_entity_offsets(full_text, val, entity_col_name)
                    if offset:
                        entities.append(offset)

                # Якщо знайшли хоча б одну сутність — зберігаємо для навчання
                if entities:
                    records.append({
                        "text": full_text,
                        "label": entities,
                        "metadata": {
                            "row_index": index,
                            "source": source_key
                        }
                    })

        # Запис у файл
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in records:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f"✅ Експорт завершено. Згенеровано {len(records)} прикладів.")