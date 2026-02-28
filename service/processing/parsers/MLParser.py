import spacy
import re
from service.storage.LoggerManager import LoggerManager

class MLParser:
    def __init__(self, model_path, log_manager: LoggerManager, use_ml=True):
        self.use_ml = use_ml
        if self.use_ml:
            self.nlp = spacy.load(model_path)
            self.logger = log_manager.get_logger()
            self.logger.debug(f"Завантаження ML-моделі з {model_path}...")
        else:
            self.use_ml = False

    def parse_text(self, text: str):
        if not self.use_ml:
            return {}
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