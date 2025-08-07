from typing import Optional

def identificar_banco(texto_pagina_uno: str) -> Optional[str]:
    """
    Identifica el banco basándose en cadenas de texto fiables en la primera página del PDF.
    """
    texto_upper = texto_pagina_uno.upper()

    # --- CORRECCIÓN: Se usa el texto específico para BBVA ---
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

# --- FUNCIÓN AÑADIDA PARA BANORTE ---
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