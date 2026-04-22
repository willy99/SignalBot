from pathlib import Path

from service.storage.LoggerManager import LoggerManager
from .DocxParser import DocxParser
from .DocOldParser import DocOldParser
from .ImgParser import ImgParser
from .PdfParser import PdfParser
from .TxtParser import TxtParser


class ParserFactory:
    @staticmethod
    def get_parser(file_path, log_manager : LoggerManager):
        extension = Path(file_path).suffix.lower()

        parsers = {
            '.docx': DocxParser,
            '.doc': DocOldParser,
            '.pdf': PdfParser,
            '.txt': TxtParser,
            '.jpg': ImgParser,
            '.jpeg': ImgParser,
            '.png': ImgParser

        }

        parser_class = parsers.get(extension)

        if parser_class:
            return parser_class(file_path, log_manager=log_manager)

        raise ValueError(f"❌ Формат {extension} не підтримується. Файл: {file_path}")