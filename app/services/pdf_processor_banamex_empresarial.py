import pdfplumber
import re
from typing import List, Dict, Optional

# --- NUEVA FUNCIÓN: Extraer info de la cuenta ---
def extraer_info_cuenta_empresarial(texto_pagina_uno: str) -> Dict:
    """
    Extrae el nombre y número de la cuenta desde la sección RESUMEN GENERAL.
    """
    # Expresión regular para buscar "Cuenta de Cheques Moneda Nacional" seguido de un número.
    patron_cuenta = re.search(r"(Cuenta de Cheques Moneda\s+Nacional)\s+(\d+)", texto_pagina_uno)
    if patron_cuenta:
        return {
            "nombre_cuenta": patron_cuenta.group(1).strip(),
            "numero_cuenta": patron_cuenta.group(2).strip()
        }
    return {
        "nombre_cuenta": "Cuenta Empresarial No Identificada",
        "numero_cuenta": "N/A"
    }

# --- NUEVA FUNCIÓN: Extraer saldos anterior y actual ---
def extraer_saldos_resumen_empresarial(texto_pagina_uno: str) -> Dict:
    """
    Extrae el saldo anterior y saldo actual desde la sección de resumen.
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

# --- Extraer RESUMEN DEL PERIODO (Formato Empresarial) ---
def extraer_resumen_periodo_empresarial(texto_pagina_uno: str) -> Optional[Dict]:
    """
    Extrae los datos del bloque 'RESUMEN DEL ... AL ...' para cuentas empresariales.
    Esta versión usa una expresión regular más robusta.
    """
    try:
        periodo_match = re.search(r"RESUMEN DEL:\s+(.*?)\s+AL\s+(.*?)\n", texto_pagina_uno)
        depositos_match = re.search(r"(\d+)\s+Depósitos[\s\S]*?([\d,]+\.\d{2})", texto_pagina_uno)
        retiros_match = re.search(r"(\d+)\s+Retiros[\s\S]*?([\d,]+\.\d{2})", texto_pagina_uno)

        if periodo_match and depositos_match and retiros_match:
            periodo_str = f"{periodo_match.group(1).strip()} AL {periodo_match.group(2).strip()}"
            return {
                "periodo": periodo_str,
                "depositos_conteo": int(depositos_match.group(1)),
                "depositos_total": float(depositos_match.group(2).replace(',', '')),
                "retiros_conteo": int(retiros_match.group(1)),
                "retiros_total": float(retiros_match.group(2).replace(',', '')),
            }
    except (AttributeError, IndexError, ValueError):
        return None
    return None

# --- Nueva Función para extraer la fecha de corte ---
def extraer_fecha_corte(texto_pagina_uno: str) -> Optional[str]:
    match = re.search(r"ESTADO DE CUENTA AL\s+(.*)", texto_pagina_uno)
    if match:
        return match.group(1).strip()
    return None

# --- Extraer RESUMEN POR MEDIOS DE ACCESO (Formato Empresarial) ---
def extraer_resumen_medios_acceso_empresarial(texto_pagina_uno: str) -> List[Dict]:
    resumen_medios = []
    match = re.search(r"Cheques\s+.*?\$?\s*([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})", texto_pagina_uno)
    if match:
        resumen_medios.append({
            "medio": "Cheques/Transferencias",
            "retiros": float(match.group(1).replace(',', '')),
            "depositos": float(match.group(2).replace(',', ''))
        })
    return resumen_medios

# --- Limpiar páginas de operaciones (Sin cambios) ---
def limpiar_texto_pagina_operaciones(texto_pagina: str) -> str:
    if "DETALLE DE OPERACIONES" not in texto_pagina:
        return ""
    posicion_detalle = texto_pagina.rfind("DETALLE DE OPERACIONES")
    texto_limpio = texto_pagina[posicion_detalle + len("DETALLE DE OPERACIONES"):]
    texto_limpio = re.sub(r'^\s*FECHA\s+CONCEPTO\s+RETIROS\s+DEPOSITOS\s+SALDO\s*\n', '', texto_limpio.strip(), flags=re.MULTILINE)
    texto_limpio = re.sub(r'\n\s*[\d\.A-Z]+\.OD\..*$', '', texto_limpio, flags=re.MULTILINE)
    posicion_saldo_minimo = texto_limpio.find("SALDO MINIMO REQUERIDO")
    if posicion_saldo_minimo != -1:
        texto_limpio = texto_limpio[:posicion_saldo_minimo]
    return texto_limpio.strip()

# --- Categorizar transacción (Sin cambios) ---
def categorizar_transaccion_empresarial(descripcion: str) -> str:
    desc = descripcion.upper()
    if "TRASPASO REF" in desc:
        return "Transferencia de Salida"
    if "PAGO RECIBIDO" in desc:
        return "Transferencia de Entrada / Cobranza"
    if "DEPOSITO EFECTIVO" in desc:
        return "Depósito en Efectivo"
    return "Operación Bancaria"

# --- Procesar bloque de concepto individual (Sin cambios) ---
def procesar_bloque_concepto_empresarial(fecha: str, concepto_lineas: List[str]) -> Optional[Dict]:
    texto_completo = " ".join(concepto_lineas).replace('-\n', '').strip()
    numeros = re.findall(r'[\d,]+\.\d{2}', texto_completo)
    descripcion = re.sub(r'(\s+[\d,]+\.\d{2}\s*)+$', '', texto_completo).strip()
    desc_upper = descripcion.upper()
    monto_transaccion, saldo = 0.0, None
    if "SALDO ANTERIOR" in desc_upper:
        saldo = float(numeros[0].replace(',', '')) if numeros else 0.0
    elif len(numeros) >= 2:
        monto_transaccion, saldo = float(numeros[0].replace(',', '')), float(numeros[-1].replace(',', ''))
    elif len(numeros) == 1:
        monto_transaccion = float(numeros[0].replace(',', ''))
    retiro, deposito = 0.0, 0.0
    if "SALDO ANTERIOR" in desc_upper: tipo_movimiento = "informativo"
    elif "TRASPASO REF" in texto_completo.upper(): tipo_movimiento, retiro = "gasto", monto_transaccion
    elif "PAGO RECIBIDO" in texto_completo.upper() or "DEPOSITO EFECTIVO" in texto_completo.upper(): tipo_movimiento, deposito = "ingreso", monto_transaccion
    else: tipo_movimiento = "informativo"
    if monto_transaccion == 0.0 and "SALDO ANTERIOR" not in desc_upper: return None
    return {"fecha": fecha, "descripcion": descripcion, "retiro": retiro, "deposito": deposito, "saldo": saldo, "tipo_movimiento": tipo_movimiento, "categoria": "Informativo" if tipo_movimiento == "informativo" else categorizar_transaccion_empresarial(descripcion)}

# --- Extraer detalle de operaciones (Sin cambios) ---
def extraer_detalle_operaciones_empresarial(texto_limpio_total: str) -> List[Dict]:
    transacciones = []
    patron_inicio_transaccion = re.compile(r"^(\d{2}\s[A-Z]{3})\s+(.*)")
    fecha_actual, concepto_acumulado = None, []
    lines = texto_limpio_total.split('\n')

    if lines and "SALDO ANTERIOR" in lines[0]:
        saldo_anterior_line = lines.pop(0)
        transaccion = procesar_bloque_concepto_empresarial("", [saldo_anterior_line])
        if transaccion:
            transaccion['descripcion'] = 'SALDO ANTERIOR'
            transacciones.append(transaccion)
    for linea in lines:
        if not linea.strip(): continue
        match = patron_inicio_transaccion.match(linea)
        if match:
            if fecha_actual and concepto_acumulado:
                transaccion = procesar_bloque_concepto_empresarial(fecha_actual, concepto_acumulado)
                if transaccion: transacciones.append(transaccion)
            fecha_actual, concepto_acumulado = match.group(1), [match.group(2)]
        elif fecha_actual:
            concepto_acumulado.append(linea.strip())
    if fecha_actual and concepto_acumulado:
        transaccion = procesar_bloque_concepto_empresarial(fecha_actual, concepto_acumulado)
        if transaccion: transacciones.append(transaccion)
    return transacciones

# --- Función Principal (Empresarial) ---
def procesar_estado_de_cuenta_empresarial(ruta_pdf: str) -> Optional[dict]:
    with pdfplumber.open(ruta_pdf) as pdf:
        if not pdf.pages: return None

        pagina_uno_texto = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2) or ""
        
        # Extracción de datos
        info_cuenta = extraer_info_cuenta_empresarial(pagina_uno_texto)
        saldos_resumen = extraer_saldos_resumen_empresarial(pagina_uno_texto)  # NUEVA EXTRACCIÓN
        resumen_periodo = extraer_resumen_periodo_empresarial(pagina_uno_texto)
        fecha_corte = extraer_fecha_corte(pagina_uno_texto)
        
        texto_limpio_operaciones = ""
        for pagina in pdf.pages:
            texto_pagina_crudo = pagina.extract_text(x_tolerance=2, y_tolerance=2)
            if texto_pagina_crudo:
                texto_limpio_operaciones += limpiar_texto_pagina_operaciones(texto_pagina_crudo) + "\n"

        transacciones = extraer_detalle_operaciones_empresarial(texto_limpio_operaciones)

        # Totales
        total_ingresos = resumen_periodo["depositos_total"] if resumen_periodo else 0.0
        total_gastos = resumen_periodo["retiros_total"] if resumen_periodo else 0.0

        # --- ESTRUCTURA DE RETORNO MODIFICADA ---
        # Se crea un diccionario para la cuenta y se anida dentro de la lista 'cuentas'
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