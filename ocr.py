import easyocr
from pdf2image import convert_from_path
import numpy as np

reader = easyocr.Reader(['en']) # Choose your language
images = convert_from_path('scanned_document.pdf')

for img in images:
    # Convert PIL image to numpy array for EasyOCR
    results = reader.readtext(np.array(img))
    for (bbox, text, prob) in results:
        print(text)