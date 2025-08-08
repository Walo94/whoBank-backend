# app/services/ocr_processor.py
# app/services/ocr_processor.py

import pytesseract
from pdf2image import convert_from_path
from typing import Optional

def extraer_texto_con_ocr(ruta_pdf: str) -> Optional[str]:
    """
    Usa OCR para extraer texto de un PDF basado en imágenes.
    """
    try:
        # --- LÍNEA AÑADIDA ---
        # Le decimos a pytesseract dónde encontrar el ejecutable de Tesseract.
        # La 'r' antes de la cadena es importante en Windows para manejar las barras invertidas.
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # --- EL RESTO DEL CÓDIGO NO CAMBIA ---
        imagenes = convert_from_path(ruta_pdf)
        
        texto_completo = ""
        for img in imagenes:
            texto_pagina = pytesseract.image_to_string(img, lang='spa')
            texto_completo += texto_pagina + "\n"
            
        return texto_completo
    except Exception as e:
        print(f"Error durante el procesamiento OCR: {e}")
        return None