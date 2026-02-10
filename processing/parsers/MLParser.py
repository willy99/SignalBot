import spacy
import re

class MLParser:
    def __init__(self, model_path="./output_model/model-best"):
        print(f"Завантаження ML-моделі з {model_path}...")
        self.nlp = spacy.load(model_path)

    def parse_text(self, text: str):
        if not text or not isinstance(text, str):
            return {}

        doc = self.nlp(text)
        results = {}

        for ent in doc.ents:
            results[ent.label_] = self.clean_text(ent.text)

        return results

    def clean_text(self, text: str) -> str:
        if not text: return ""
        # Замінюємо переноси рядків, таби та купу пробілів на один пробіл
        text = re.sub(r'[\n\r\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()