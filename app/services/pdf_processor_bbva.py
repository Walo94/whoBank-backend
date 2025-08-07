import pdfplumber
import re
from typing import List, Dict, Optional
from app.schemas.analysis_bbva import AnalisisBbvaPDF, CuentaAnalisis

# --- SECCIÓN 1: EXTRACCIÓN DE DATOS PRINCIPALES ---
def extraer_datos_encabezado(texto: str) -> Dict:
    """Extrae la información principal del encabezado del estado de cuenta de BBVA."""
    periodo_match = re.search(r"Periodo\s*DEL\s*(\d{2}/\d{2}/\d{4})\s*AL\s*(\d{2}/\d{2}/\d{4})", texto)
    fecha_corte_match = re.search(r"Fecha de Corte\s*(\d{2}/\d{2}/\d{4})", texto)
    num_cuenta_match = re.search(r"No\. de Cuenta\s*(\d+)", texto)
    tipo_cuenta_match = re.search(r"Estado de Cuenta\s*(MAESTRA PYME BBVA)", texto)
    
    return {
        "periodo": f"DEL {periodo_match.group(1)} AL {periodo_match.group(2)}" if periodo_match else None,
        "fecha_corte": fecha_corte_match.group(1) if fecha_corte_match else None,
        "numero_cuenta": num_cuenta_match.group(1) if num_cuenta_match else None,
        "nombre_cuenta": tipo_cuenta_match.group(1).strip() if tipo_cuenta_match else "No Identificada"
    }

def extraer_resumen_comportamiento(texto: str) -> Dict:
    """
    Extrae los valores del bloque "Comportamiento" de BBVA utilizando un patrón de bloque
    contextual, haciéndolo más robusto a variaciones de formato.
    """
    # Patrón de bloque que busca los encabezados en secuencia y luego captura los 4 valores clave.
    # Es insensible a mayúsculas/minúsculas y maneja saltos de línea.
    patron_bloque = re.compile(
        r"Saldo de Operación Inicial\s+([\d,]+\.\d{2})"  # Grupo 1: Saldo Inicial
        r".*?"                                           # Cualquier texto intermedio
        r"Depósitos\s*/\s*Abonos\s*\(\+\)\s+\d+\s+([\d,]+\.\d{2})"  # Grupo 2: Total Depósitos/Ingresos
        r".*?"                                           # Cualquier texto intermedio
        r"Retiros\s*/\s*Cargos\s*\(\-\)\s+\d+\s+([\d,]+\.\d{2})"    # Grupo 3: Total Retiros/Gastos
        r".*?"                                           # Cualquier texto intermedio
        r"Saldo Final\s*\(\+\)\s+([\d,]+\.\d{2})",       # Grupo 4: Saldo Final
        re.DOTALL | re.IGNORECASE
    )

    match = patron_bloque.search(texto)

    if match:
        # Si el bloque se encuentra, extraemos los valores de los grupos capturados.
        saldo_inicial = float(match.group(1).replace(',', ''))
        total_ingresos = float(match.group(2).replace(',', ''))
        total_gastos = float(match.group(3).replace(',', ''))
        saldo_final = float(match.group(4).replace(',', ''))
    else:
        # Si el patrón de bloque no encuentra coincidencias, devolvemos ceros para evitar errores.
        # Esto indica que la estructura del PDF es inesperada y necesita revisión.
        saldo_inicial = 0.0
        total_ingresos = 0.0
        total_gastos = 0.0
        saldo_final = 0.0

    return {
        "saldo_anterior_resumen": saldo_inicial,
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "saldo_actual_resumen": saldo_final
    }
    
# --- SECCIÓN 2: LÓGICA DE PROCESAMIENTO DE TRANSACCIONES ---
def categorizar_transaccion_bbva(descripcion: str, tipo_movimiento: str) -> str:
    """Categoriza una transacción de BBVA basándose en su descripción y tipo."""
    desc = descripcion.upper()

    # Use the pre-determined type for N06 for better categorization
    if "N06" in desc:
        if tipo_movimiento == "gasto":
            if "REEMBOLSO" in desc:
                return "Reembolso Enviado (N06)"
            return "Pago a Terceros (N06)"
        else: # ingreso
            return "Cobro de Terceros (N06)"
    elif "SPEI RECIBIDO" in desc:
        return "Transferencia SPEI Recibida"
    elif "SPEI ENVIADO" in desc:
        return "Transferencia SPEI Enviada"
    elif "CHEQUE PAGADO" in desc:
        return "Cheque Cobrado"
    elif "DEPOSITO EN EFECTIVO" in desc:
        return "Depósito en Efectivo"
    elif "DEPOSITO CHEQUE" in desc:
        return "Depósito de Cheque"
    elif "DEPOSITO DE TERCERO" in desc:
        return "Depósito de Tercero"
    elif "SERV BANCA INTERNET" in desc:
        return "Comisión Banca Internet"
    elif "CFE SUMINISTRADOR" in desc:
        return "Pago de Servicio (CFE)"
    elif "COMPENSACION" in desc:
        return "Compensación Bancaria"
    else:
        return "Otro"

def es_linea_institucional(linea: str) -> bool:
    linea_upper = linea.upper()
    frases = [
        "ESTIMADO CLIENTE",
        "SU ESTADO DE CUENTA HA SIDO MODIFICADO",
        "TAMBIÉN LE INFORMAMOS QUE SU CONTRATO HA SIDO MODIFICADO",
        "WWW.BBVA.MX",
        "CON BBVA ADELANTE",
        "LA GAT REAL",
        "BBVA MEXICO",
        "PAGINA",
        "AV. PASEO DE LA REFORMA",
        "ESTADO DE CUENTA",
        "RFC",
        "NO. CUENTA",
        "NO. CLIENTE",
        "CIUDAD DE MÉXICO",
        "MAESTRA PYME BBVA",
    ]
    return any(f in linea_upper for f in frases)

def procesar_bloque_transaccion_bbva(fecha: str, bloque_lineas: List[str]) -> Optional[Dict]:
    if not bloque_lineas:
        return None

    primera_linea = bloque_lineas[0].strip()

    # Intenta encontrar el código de la transacción al inicio de la línea.
    codigo_match = re.match(r'^([A-Z0-9]+)\s+(.*)', primera_linea)
    if not codigo_match:
        return None

    codigo = codigo_match.group(1)
    resto_primera_linea = codigo_match.group(2)

    # Extraer todos los montos de la primera línea para procesarlos.
    montos_en_linea = re.findall(r'([\d,]+\.\d{2})', primera_linea)
    if not montos_en_linea:
        return None # Si no hay montos, no podemos procesar la transacción.

    # Construir la descripción completa a partir de todas las líneas del bloque.
    pos_primer_monto = primera_linea.find(montos_en_linea[0])
    descripcion_partes = [primera_linea[:pos_primer_monto].strip()]

    for linea in bloque_lineas[1:]:
        linea_limpia = linea.strip()
        if not linea_limpia or es_linea_institucional(linea_limpia):
            continue

        # Si una línea no contiene montos, es parte de la descripción.
        if not re.search(r'[\d,]+\.\d{2}', linea_limpia):
            descripcion_partes.append(linea_limpia)
        else:
            # Si contiene montos, solo tomamos el texto previo como descripción.
            pos_monto = linea_limpia.find(re.findall(r'([\d,]+\.\d{2})', linea_limpia)[0])
            if pos_monto > 0:
                descripcion_partes.append(linea_limpia[:pos_monto].strip())
    
    descripcion = " ".join(filter(None, descripcion_partes))
    montos_float = [float(m.replace(',', '')) for m in montos_en_linea]
    
    retiro, deposito = 0.0, 0.0
    monto_principal = montos_float[0]

    # --- INICIO DE LA LÓGICA MEJORADA ---

    desc_upper = descripcion.upper()
    
    # Códigos con comportamiento fijo y conocido
    codigos_retiro_claros = {'C03', 'T17', 'S39', 'S40', 'P14', 'P31'}
    codigos_deposito_claros = {'T20', 'C02', 'W02', 'M97', 'Y45'}

    if codigo in codigos_retiro_claros:
        retiro = monto_principal
    elif codigo in codigos_deposito_claros:
        deposito = monto_principal
    elif codigo == 'N06':
        # Lógica específica para el código N06, que es ambiguo.
        # Buscamos palabras clave para determinar si es un cargo o un abono.
        palabras_cargo = ['PAGO', 'PAGO A TERCERO', 'PAGO CUENTA']
        palabras_abono = ['ABONO', 'DEPOSITO', 'REEMBOLSO'] # 'REEMBOLSO' puede ser ambiguo, pero suele ser un ingreso.

        es_cargo_por_keyword = any(p in desc_upper for p in palabras_cargo)
        es_abono_por_keyword = any(p in desc_upper for p in palabras_abono)

        # Si las palabras clave son claras, las usamos.
        if es_abono_por_keyword and not es_cargo_por_keyword:
            deposito = monto_principal
        elif es_cargo_por_keyword and not es_abono_por_keyword:
            retiro = monto_principal
        else:
            # Fallback: Si contiene BNET (Banca en Línea), es muy probable que sea un pago hecho por el usuario.
            if 'BNET' in desc_upper:
                retiro = monto_principal
            else:
                # Si no podemos decidir, por seguridad lo asignamos como gasto para revisión.
                # Esta regla puede ajustarse si se encuentran más patrones.
                retiro = monto_principal 
    else:
        # Lógica general para códigos desconocidos basada en palabras clave
        if any(p in desc_upper for p in ['PAGO', 'ENVIADO', 'CARGO', 'COMISION']):
            retiro = monto_principal
        elif any(p in desc_upper for p in ['RECIBIDO', 'DEPOSITO', 'ABONO', 'INGRESO']):
            deposito = monto_principal
        else:
            # Si no hay pistas, asumimos que es un retiro.
            retiro = monto_principal
            
    # --- FIN DE LA LÓGICA MEJORADA ---

    # Asignación del saldo final de la transacción
    saldo = None
    if len(montos_float) > 1:
        # El saldo suele ser el último monto de la línea y diferente al monto de la transacción.
        posible_saldo = montos_float[-1]
        monto_transaccion = retiro if retiro > 0 else deposito
        if posible_saldo != monto_transaccion:
            saldo = posible_saldo

    return {
        "fecha": fecha,
        "descripcion": descripcion,
        "retiro": retiro,
        "deposito": deposito,
        "saldo": saldo,
        "tipo_movimiento": "gasto" if retiro > 0 else "ingreso",
        "categoria": categorizar_transaccion_bbva(descripcion, "gasto" if retiro > 0 else "ingreso"),
        "codigo": codigo
    }

def extraer_detalle_movimientos(texto_completo: str) -> List[Dict]:
    transacciones = []

    inicio_movimientos = texto_completo.find("Detalle de Movimientos Realizados")
    if inicio_movimientos == -1:
        return []

    fin_movimientos = texto_completo.find("Total de Movimientos", inicio_movimientos)
    if fin_movimientos == -1:
        fin_movimientos = len(texto_completo)

    texto_movimientos = texto_completo[inicio_movimientos:fin_movimientos]
    lineas = texto_movimientos.split('\n')

    bloque_actual = []
    fecha_actual = ""

    patron_fecha = re.compile(r'^(\d{2}/[A-Z]{3})\s+(\d{2}/[A-Z]{3})\s+([A-Z0-9]+)')

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        match = patron_fecha.match(linea)
        if match:
            if fecha_actual and bloque_actual:
                transaccion = procesar_bloque_transaccion_bbva(fecha_actual, bloque_actual)
                if transaccion:
                    transacciones.append(transaccion)

            fecha_actual = match.group(1)
            codigo = match.group(3)
            resto_linea = linea[len(match.group(0)):].strip()
            bloque_actual = [f"{codigo} {resto_linea}"]
        elif fecha_actual and linea:
            if es_linea_institucional(linea):
                continue
            if not any(header in linea.upper() for header in ['FECHA', 'OPER', 'LIQ', 'COD.', 'DESCRIPCIÓN', 'REFERENCIA', 'CARGOS', 'ABONOS', 'OPERACIÓN', 'LIQUIDACIÓN']):
                bloque_actual.append(linea)

    if fecha_actual and bloque_actual:
        transaccion = procesar_bloque_transaccion_bbva(fecha_actual, bloque_actual)
        if transaccion:
            transacciones.append(transaccion)

    return transacciones

# --- SECCIÓN 3: FUNCIÓN PRINCIPAL INTEGRADORA ---

def procesar_estado_de_cuenta_bbva(ruta_pdf: str) -> dict:
    """Función principal que orquesta la extracción de datos de un PDF de BBVA."""
    texto_completo_paginas = ""
    with pdfplumber.open(ruta_pdf) as pdf:
        if not pdf.pages:
            raise ValueError("El PDF está vacío o no se puede leer.")
        # Unir el texto de todas las páginas para un análisis completo
        for page in pdf.pages:
            texto_completo_paginas += page.extract_text(x_tolerance=2) + "\n"

    if not texto_completo_paginas:
        raise ValueError("No se pudo extraer texto del PDF.")

    # 1. Extraer datos del encabezado y resumen (usualmente en la primera página)
    datos_encabezado = extraer_datos_encabezado(texto_completo_paginas)
    resumen_comportamiento = extraer_resumen_comportamiento(texto_completo_paginas)

    # 2. Extraer el detalle de transacciones de todo el documento
    transacciones = extraer_detalle_movimientos(texto_completo_paginas)

    # 3. Construir el objeto de la cuenta
    cuenta_analizada = CuentaAnalisis(
        nombre_cuenta=datos_encabezado["nombre_cuenta"],
        numero_cuenta=datos_encabezado["numero_cuenta"],
        moneda="PESOS",
        saldo_anterior_resumen=resumen_comportamiento["saldo_anterior_resumen"],
        saldo_actual_resumen=resumen_comportamiento["saldo_actual_resumen"],
        total_ingresos=resumen_comportamiento["total_ingresos"],
        total_gastos=resumen_comportamiento["total_gastos"],
        transacciones=transacciones
    )

    # 4. Ensamblar la respuesta final
    resultado_final = AnalisisBbvaPDF(
        nombre_archivo=ruta_pdf.split('/')[-1],
        banco="bbva",
        fecha_corte=datos_encabezado["fecha_corte"],
        periodo=datos_encabezado["periodo"],
        cuentas=[cuenta_analizada]
    )

    return resultado_final.dict()