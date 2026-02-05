from .BaseFileParser import BaseFileParser
import textract

class DocOldParser(BaseFileParser):

    def get_full_text(self):
        byte_content = textract.process(self.file_path)
        return byte_content.decode('utf-8')
