import pdfplumber
from typing import Optional

def identificar_tipo_cuenta(ruta_pdf: str) -> Optional[str]:
    """
    Lee la primera página de un PDF para identificar si es una cuenta
    personal ("MiCuenta") o empresarial ("Cuenta de Cheques Moneda Nacional").

    Returns:
        - "personal" si es MiCuenta.
        - "empresarial" si es Cuenta de Cheques.
        - None si no se puede determinar.
    """
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            if not pdf.pages:
                return None

            # Extraer texto solo de la primera página para eficiencia
            texto_pagina_uno = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2)
            
            if not texto_pagina_uno:
                return None

            texto_upper = texto_pagina_uno.upper()

            if "CUENTA DE CHEQUES MONEDA NACIONAL" in texto_upper:
                return "empresarial"
            
            if "MICUENTA" in texto_upper:
                return "personal"

    except Exception:
        # Si hay algún error al leer el PDF, no se puede identificar
        return None
    
    return None