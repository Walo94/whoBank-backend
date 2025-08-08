from typing import Optional

def identificar_banco(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el banco basándose en cadenas de texto fiables en la primera página del PDF.
    """
    texto_upper = texto_pagina_uno.upper()

    # --- Se usa el texto específico para BBVA ---
    if "MAESTRA PYME BBVA" in texto_upper:
        return "bbva"

    # Búsqueda robusta para BanBajio.
    if "BANCO DEL BAJIO S.A." in texto_upper:
        return "banbajio"

    # Búsqueda robusta para Banamex (Citibanamex).
    if "RESUMEN POR MEDIOS DE ACCESO" in texto_upper:
        return "banamex"

    # Búsqueda para Banorte
    if "ESTADO DE CUENTA / CUENTA PREFERENTE" in texto_upper:
        return "banorte"

    # ---CONDICIÓN PARA SANTANDER ---
    if "SANTANDER SELECT" in texto_upper or "BANCO SANTANDER MÉXICO, S.A." in texto_upper:
        return "santander"

    # Usamos "SCOTIABANK" porque es el identificador más consistente en todo el documento.
    if "SCOTIABANK" in texto_upper:
        return "scotiabank"
        
    
    return None

def identificar_tipo_cuenta_banamex(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el tipo de cuenta para un estado de cuenta de Banamex.
    """
    texto_upper = texto_pagina_uno.upper()
    if "CUENTA DE CHEQUES MONEDA NACIONAL" in texto_upper:
        return "empresarial"
    if "MICUENTA" in texto_upper:
        return "personal"
    return None

def identificar_tipo_cuenta_banbajio(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el tipo de cuenta para un estado de cuenta de BanBajio.
    """
    texto_upper = texto_pagina_uno.upper()
    if "CUENTA CONECTA BANBAJIO" in texto_upper:
        return "empresarial"
    return None

# --- FUNCIÓN BBVA ---
def identificar_tipo_cuenta_bbva(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el tipo de cuenta para un estado de cuenta de BBVA.
    """
    texto_upper = texto_pagina_uno.upper()
    # Por ahora, solo identificamos la cuenta empresarial.
    if "MAESTRA PYME BBVA" in texto_upper:
        return "empresarial"
    # Aquí se podría añadir lógica para cuentas personales de BBVA en el futuro.
    return None

# --- FUNCIÓN BANORTE ---
def identificar_tipo_cuenta_banorte(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el tipo de cuenta para un estado de cuenta de Banorte.
    """
    texto_upper = texto_pagina_uno.upper()
    # [cite_start]Se busca el texto específico del tipo de cuenta en el PDF [cite: 2, 12]
    if "CUENTA PREFERENTE" in texto_upper:
        return "preferente"
    # Aquí se podrían añadir otras lógicas para diferentes cuentas de Banorte en el futuro.
    return None

def identificar_tipo_cuenta_scotiabank(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el tipo de cuenta para un estado de cuenta de Scotiabank.
    """
    texto_upper = texto_pagina_uno.upper()
    # Identificador basado en el producto CU PYME PFAE PQ [cite: 13]
    if "CU PYME PFAE PQ" in texto_upper:
        return "pyme_pfae"
    return None