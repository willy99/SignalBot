import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
import json
import os

class ModelTrainer:
    def __init__(self, jsonl_path: str, model_name: str = "uk_core_news_lg"):
        self.jsonl_path = jsonl_path
        self.model_name = model_name
        self.nlp = spacy.load(model_name)

    def prepare_data(self, output_path: str = "ml/train.spacy"):
        """Конвертує JSONL у бінарний формат .spacy з перевіркою на перекриття сутностей."""
        db = DocBin()
        count = 0

        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                text = data['text']
                labels = data['label']  # [start, end, label]

                doc = self.nlp.make_doc(text)
                ents = []

                for start, end, label in labels:
                    span = doc.char_span(start, end, label=label, alignment_mode="contract")
                    if span is not None:
                        ents.append(span)

                # Важливо: прибираємо перекриття (якщо одна сутність всередині іншої)
                filtered_ents = filter_spans(ents)
                doc.ents = filtered_ents
                db.add(doc)
                count += 1

        db.to_disk(output_path)
        print(f"✅ Підготовлено {count} документів у форматі .spacy")

    def create_config(self):
        """Генерує базовий конфіг для навчання (автоматично через CLI)."""
        # Це краще робити через термінал, але можна викликати системно:
        os.system(f"python -m spacy init fill-config ./base_config.cfg ./config.cfg")
        print("⚙️ Конфігураційний файл створено.")
