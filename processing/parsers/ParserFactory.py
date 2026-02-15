from pathlib import Path

from storage.LoggerManager import LoggerManager
from .DocxParser import DocxParser
from .DocOldParser import DocOldParser
from .PdfParser import PdfParser

class ParserFactory:
    @staticmethod
    def get_parser(file_path, log_manager : LoggerManager):
        extension = Path(file_path).suffix.lower()

        parsers = {
            '.docx': DocxParser,
            '.doc': DocOldParser,
            '.pdf': PdfParser
        }

        parser_class = parsers.get(extension)

        if parser_class:
            return parser_class(file_path, log_manager=log_manager)

        raise ValueError(f"❌ Формат {extension} не підтримується. Файл: {file_path}")