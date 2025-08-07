import pdfplumber
import re
from typing import List, Dict, Optional

# --- NUEVA FUNCIÓN: Extraer info de la cuenta ---
def extraer_info_cuenta(texto_pagina_uno: str) -> Dict:
    """
    Extrae el nombre y número de la cuenta desde la sección RESUMEN GENERAL.
    """
    # Expresión regular para buscar "Cuenta de Cheques Moneda Nacional" o "MiCuenta" seguido de un número.
    patron_cuenta = re.search(r"((?:Cuenta de Cheques Moneda Nacional|MiCuenta))\s+(\d+)", texto_pagina_uno)
    if patron_cuenta:
        return {
            "nombre_cuenta": patron_cuenta.group(1).strip(),
            "numero_cuenta": patron_cuenta.group(2).strip()
        }
    return {
        "nombre_cuenta": "Cuenta Personal No Identificada",
        "numero_cuenta": "N/A"
    }

# --- NUEVA FUNCIÓN: Extraer saldos anterior y actual ---
def extraer_saldos_resumen_personal(texto_pagina_uno: str) -> Dict:
    """
    Extrae el saldo anterior y saldo actual desde la sección de resumen para cuentas personales.
    """
    saldo_anterior = None
    saldo_actual = None
    
    # Buscar "Saldo Anterior $XXX,XXX.XX"
    patron_saldo_anterior = re.search(r"Saldo Anterior\s+\$?([\d,]+\.\d{2})", texto_pagina_uno)
    if patron_saldo_anterior:
        saldo_anterior = float(patron_saldo_anterior.group(1).replace(',', ''))
    
    # Buscar "SALDO AL XX DE XXXXX DE YYYY $XXX,XXX.XX"
    patron_saldo_actual = re.search(r"SALDO AL\s+\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+\d{4}\s+\$?([\d,]+\.\d{2})", texto_pagina_uno)
    if patron_saldo_actual:
        saldo_actual = float(patron_saldo_actual.group(1).replace(',', ''))
    
    return {
        "saldo_anterior": saldo_anterior,
        "saldo_actual": saldo_actual
    }

# --- Función para extraer la fecha de corte (Sin cambios) ---
def extraer_fecha_corte(texto_pagina_uno: str) -> Optional[str]:
    match = re.search(r"ESTADO DE CUENTA AL\s+(.*)", texto_pagina_uno)
    if match:
        return match.group(1).strip()
    return None

# --- Extraer RESUMEN DEL PERIODO (Sin cambios) ---
def extraer_resumen_periodo(texto_pagina_uno: str) -> Optional[Dict]:
    try:
        periodo_match = re.search(r"RESUMEN DEL\s+(.*?)\s+AL\s+(.*?)\n", texto_pagina_uno)
        depositos_match = re.search(r"(\d+)\s*Depósitos\s*\$?\s*([\d,]+\.\d{2})", texto_pagina_uno)
        retiros_match = re.search(r"(\d+)\s*Retiros\s*\$?\s*([\d,]+\.\d{2})", texto_pagina_uno)
        if periodo_match and depositos_match and retiros_match:
            periodo_str = f"{periodo_match.group(1).strip()} AL {periodo_match.group(2).strip()}"
            return {"periodo": periodo_str, "depositos_conteo": int(depositos_match.group(1)), "depositos_total": float(depositos_match.group(2).replace(',', '')), "retiros_conteo": int(retiros_match.group(1)), "retiros_total": float(retiros_match.group(2).replace(',', ''))}
    except (AttributeError, IndexError):
        return None
    return None

# --- Extraer RESUMEN POR MEDIOS DE ACCESO (Sin cambios) ---
def extraer_resumen_medios_acceso(texto_pagina_uno: str) -> List[Dict]:
    resumen_medios, seccion_match = [], re.search(r"RESUMEN POR MEDIOS DE ACCESO([\s\S]*)", texto_pagina_uno)
    if not seccion_match: return []
    bloque_resumen = seccion_match.group(1).strip()
    patron_linea = re.compile(r"^([A-Za-z]+)[\s\d]*\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})$", re.MULTILINE)
    matches = patron_linea.findall(bloque_resumen)
    for match in matches:
        if "RETIROS" in match[0].upper() or "DEPOSITOS" in match[0].upper(): continue
        resumen_medios.append({"medio": match[0].strip(), "retiros": float(match[1].replace(',', '')), "depositos": float(match[2].replace(',', ''))})
    return resumen_medios

# --- Limpiar páginas de operaciones (Sin cambios) ---
def limpiar_texto_pagina_operaciones(texto_pagina: str) -> str:
    if "DETALLE DE OPERACIONES" not in texto_pagina: return ""
    texto_limpio = re.sub(r'\n\s*[\d\.A-Z]+\.OD\.\d{4}\.\d{2}\s*$', '', texto_pagina, flags=re.MULTILINE)
    posicion_detalle = texto_limpio.rfind("DETALLE DE OPERACIONES")
    texto_limpio = texto_limpio[posicion_detalle + len("DETALLE DE OPERACIONES"):]
    texto_limpio = re.sub(r'^\s*FECHA\s+CONCEPTO\s+RETIROS\s+DEPOSITOS\s+SALDO\s*\n', '', texto_limpio.strip(), flags=re.MULTILINE)
    return texto_limpio.strip()

# --- Clasificar transacción por descripción (Sin cambios) ---
def categorizar_transaccion(descripcion: str) -> str:
    desc = descripcion.upper()
    if "PAGO INTERBANCARIO" in desc or "PAGO RECIBIDO" in desc or "TRASPASO REF" in desc: return "Transferencia"
    if "DISPOSICIONES EN CAJERO" in desc or "DIS.EFE" in desc: return "Retiro de Efectivo"
    if "OXXO" in desc: return "Compra (Tienda de conveniencia)"
    if "EXENCION COBRO COMISION" in desc: return "Ajuste Bancario"
    if "CFE" in desc: return "Pago de Servicios (Luz)"
    if "NETFLIX" in desc or "SPOTIFY" in desc: return "Suscripciones"
    return "Otro"

PALABRAS_INFORMATIVOS = ["SALDO ANTERIOR", "EXENCION", "EXENTAS", "EXENTAR", "DISPOSICIONES EN CAJERO EXENTAS"]

# --- Procesar bloque de concepto individual (Sin cambios) ---
def procesar_bloque_concepto(fecha: str, concepto_lineas: List[str]) -> Optional[Dict]:
    texto_completo = " ".join(concepto_lineas).replace('-\n', '').strip()
    numeros = re.findall(r'[\d,]+\.\d{2}', texto_completo)
    retiro, deposito = 0.0, 0.0
    saldo = float(numeros[-1].replace(',', '')) if numeros else 0.0
    descripcion = re.sub(r'(\s+[\d,]+\.\d{2}\s*){1,2}$', '', texto_completo).strip()
    desc_upper = descripcion.upper()
    if "SALDO ANTERIOR" in desc_upper: tipo_movimiento = "informativo"
    elif any(palabra in desc_upper for palabra in PALABRAS_INFORMATIVOS): tipo_movimiento = "informativo"
    elif "PAGO RECIBIDO" in desc_upper: deposito, tipo_movimiento = (float(numeros[-2].replace(',', '')) if len(numeros) >= 2 else 0.0), "ingreso"
    else: retiro, tipo_movimiento = (float(numeros[-2].replace(',', '')) if len(numeros) >= 2 else 0.0), "gasto"
    if retiro == 0 and deposito == 0 and "SALDO ANTERIOR" not in desc_upper: tipo_movimiento = "informativo"
    return {"fecha": fecha, "descripcion": descripcion, "retiro": retiro, "deposito": deposito, "saldo": saldo, "tipo_movimiento": tipo_movimiento, "categoria": "Informativo" if tipo_movimiento == "informativo" else categorizar_transaccion(descripcion)}

# --- Extraer detalle de operaciones (Sin cambios) ---
def extraer_detalle_operaciones(texto_limpio_total: str) -> List[Dict]:
    transacciones, patron_inicio_transaccion = [], re.compile(r"^(\d{2}\s[A-Z]{3})\s+(.*)")
    fecha_actual, concepto_acumulado = None, []
    
    for linea in texto_limpio_total.split('\n'):
        if not linea.strip(): continue
        match = patron_inicio_transaccion.match(linea)
        if match:
            if fecha_actual and concepto_acumulado:
                transaccion = procesar_bloque_concepto(fecha_actual, concepto_acumulado)
                if transaccion: transacciones.append(transaccion)
            fecha_actual, concepto_acumulado = match.group(1), [match.group(2)]
        elif fecha_actual:
            concepto_acumulado.append(linea.strip())
    if fecha_actual and concepto_acumulado:
        transaccion = procesar_bloque_concepto(fecha_actual, concepto_acumulado)
        if transaccion: transacciones.append(transaccion)
    return transacciones

# --- Función principal ---
def procesar_estado_de_cuenta(ruta_pdf: str) -> Optional[dict]:
    with pdfplumber.open(ruta_pdf) as pdf:
        if not pdf.pages: return None

        pagina_uno_texto = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2) or ""
        
        # Extracción de datos
        info_cuenta = extraer_info_cuenta(pagina_uno_texto)
        saldos_resumen = extraer_saldos_resumen_personal(pagina_uno_texto)  # NUEVA EXTRACCIÓN
        resumen_periodo = extraer_resumen_periodo(pagina_uno_texto)
        fecha_corte = extraer_fecha_corte(pagina_uno_texto)

        texto_limpio_operaciones = ""
        for pagina in pdf.pages:
            texto_pagina_crudo = pagina.extract_text(x_tolerance=2, y_tolerance=2)
            if texto_pagina_crudo:
                texto_limpio_operaciones += limpiar_texto_pagina_operaciones(texto_pagina_crudo) + "\n"

        transacciones = extraer_detalle_operaciones(texto_limpio_operaciones)

        total_ingresos = resumen_periodo["depositos_total"] if resumen_periodo else 0.0
        total_gastos = resumen_periodo["retiros_total"] if resumen_periodo else 0.0

        # --- ESTRUCTURA DE RETORNO MODIFICADA ---
        datos_cuenta = {
            **info_cuenta,
            "moneda": "PESOS",
            "saldo_anterior_resumen": saldos_resumen["saldo_anterior"],  # NUEVO CAMPO
            "saldo_actual_resumen": saldos_resumen["saldo_actual"],      # NUEVO CAMPO
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "transacciones": transacciones,
        }

        return {
            "nombre_archivo": ruta_pdf.split('/')[-1],
            "banco": "banamex",
            "fecha_corte": fecha_corte,
            "periodo": resumen_periodo["periodo"] if resumen_periodo else "No encontrado",
            "cuentas": [datos_cuenta] # ¡Ahora es una lista!
        }