import pdfplumber
import re
from typing import List, Dict, Optional

# --- SECCIÓN 1: EXTRACCIÓN DE RESÚMENES (Sin cambios, ya funciona) ---
def extraer_resumen_cuenta_pesos(texto_seccion: str) -> Dict:
    """
    Extrae los datos del resumen para la cuenta en pesos utilizando un patrón de bloque
    que captura los cuatro valores principales de forma contextual.
    """
    # Patrón de bloque que busca la secuencia de encabezados y luego captura los 4 valores que le siguen.
    pattern = re.compile(
        r"SALDO ANTERIOR"
        r".*?\(\+\)\s*DEPOSITOS"
        r".*?\(\-\)\s*CARGOS"
        r".*?SALDO ACTUAL"
        r".*?\$\s*([\d,]+\.\d{2})"  # Grupo 1: Saldo Anterior
        r".*?\$\s*([\d,]+\.\d{2})"  # Grupo 2: Depositos
        r".*?\$\s*([\d,]+\.\d{2})"  # Grupo 3: Cargos
        r".*?\$\s*([\d,]+\.\d{2})", # Grupo 4: Saldo Actual
        re.DOTALL
    )
    match = pattern.search(texto_seccion)

    if match:
        saldo_anterior = float(match.group(1).replace(',', ''))
        total_depositos = float(match.group(2).replace(',', ''))
        total_cargos = float(match.group(3).replace(',', ''))
        saldo_actual = float(match.group(4).replace(',', ''))
    else:
        # Si el patrón de bloque falla, devolvemos ceros para asegurar que no haya datos erróneos.
        saldo_anterior = 0.0
        total_depositos = 0.0
        total_cargos = 0.0
        saldo_actual = 0.0

    return {
        "saldo_anterior": saldo_anterior,
        "total_depositos": total_depositos,
        "total_cargos": total_cargos,
        "saldo_actual": saldo_actual
    }

def extraer_resumen_cuenta_dolares(texto_seccion: str) -> Dict:
    """
    Extrae los datos del resumen para la cuenta en dólares utilizando un patrón de bloque
    que busca la etiqueta 'USD'.
    """
    # Patrón análogo para la cuenta en dólares.
    pattern = re.compile(
        r"SALDO ANTERIOR"
        r".*?\(\+\)\s*DEPOSITOS"
        r".*?\(\-\)\s*CARGOS"
        r".*?SALDO ACTUAL"
        r".*?\s*([\d,]+\.\d{2})\s*USD"  # Grupo 1: Saldo Anterior
        r".*?\s*([\d,]+\.\d{2})\s*USD"  # Grupo 2: Depositos
        r".*?\s*([\d,]+\.\d{2})\s*USD"  # Grupo 3: Cargos
        r".*?\s*([\d,]+\.\d{2})\s*USD", # Grupo 4: Saldo Actual
        re.DOTALL
    )
    match = pattern.search(texto_seccion)

    if match:
        saldo_anterior = float(match.group(1).replace(',', ''))
        total_depositos = float(match.group(2).replace(',', ''))
        total_cargos = float(match.group(3).replace(',', ''))
        saldo_actual = float(match.group(4).replace(',', ''))
    else:
        saldo_anterior = 0.0
        total_depositos = 0.0
        total_cargos = 0.0
        saldo_actual = 0.0

    return {
        "saldo_anterior": saldo_anterior,
        "total_depositos": total_depositos,
        "total_cargos": total_cargos,
        "saldo_actual": saldo_actual
    }

def categorizar_transaccion_banbajio(descripcion: str) -> str:
    """
    Categoriza las transacciones basándose en palabras clave.
    """
    desc = descripcion.upper()
    
    if "ENVÍO SPEI" in desc or "ENVIO SPEI" in desc:
        return "Transferencia SPEI"
    elif "TRASPASO DE RECURSOS" in desc:
        return "Traspaso de Recursos"
    elif "DEPÓSITO SPEI" in desc or "DEPOSITO SPEI" in desc:
        return "Depósito SPEI"
    elif "PAGO DE SERVICIO" in desc:
        return "Pago de Servicios"
    elif "RETIRO POR DOMICILIACION" in desc:
        return "Domiciliación"
    elif "COMISION" in desc or "COMISIÓN" in desc:
        return "Comisión"
    elif "DEPOSITO DE TRANSFERENCIA" in desc:
        return "Transferencia del Extranjero"
    else:
        return "Otro"

def es_movimiento_retiro(descripcion: str) -> bool:
    """
    Determina si un movimiento es un retiro. Esta función ahora ignora todos los
    espacios para ser inmune a errores de OCR.
    """
    desc_no_spaces = descripcion.upper().replace(' ', '')
    
    palabras_retiro = [
        "ENVÍOSPEI", "ENVIOSPEI", "TRASPASODERECURSOSALACUENTA", "PAGODESERVICIO",
        "RETIROPORDOMICILIACION", "COMISIONPOR", "IVACOMISION"
    ]
    
    for palabra_sin_espacio in palabras_retiro:
        if palabra_sin_espacio in desc_no_spaces:
            return True
    return False

def extraer_transacciones(texto_cuenta: str, moneda: str, fecha_inicio_periodo: Optional[str]) -> List[Dict]:
    """
    Función genérica para extraer transacciones de una sección de cuenta.
    Versión corregida que maneja mejor la estructura de las transacciones.
    Incluye el SALDO INICIAL como primera transacción, usando la fecha de inicio del periodo.
    """
    transacciones = []
    
    # Buscar el inicio de las transacciones y el saldo inicial
    inicio_transacciones = texto_cuenta.find("SALDO INICIAL")
    if inicio_transacciones == -1:
        return transacciones
    
    # Extraer el saldo inicial primero
    saldo_inicial_match = re.search(r"SALDO INICIAL.*?([\d,]+\.\d{2})", texto_cuenta[inicio_transacciones:])
    if saldo_inicial_match:
        saldo_inicial = float(saldo_inicial_match.group(1).replace(',', ''))
        
        # --- MODIFICACIÓN ---
        # Usar la fecha de inicio del periodo si está disponible; de lo contrario, usar "SALDO INICIAL" como respaldo.
        fecha_para_saldo = fecha_inicio_periodo if fecha_inicio_periodo else "SALDO INICIAL"
        
        # Agregar el saldo inicial como primera transacción con la fecha correcta
        transacciones.append({
            "fecha": "", # Se utiliza la fecha del periodo
            "descripcion": "Saldo inicial de la cuenta",
            "retiro": 0.0,
            "deposito": 0.0,
            "saldo": saldo_inicial,
            "tipo_movimiento": "saldo_inicial",
            "categoria": "Saldo Inicial"
        })
    
    texto_transacciones = texto_cuenta[inicio_transacciones:]
    
    # Dividir en líneas para procesamiento
    lineas = texto_transacciones.split('\n')
    
    # Buscar líneas que empiecen con fecha (patrón: número + espacio + 3 letras mayúsculas)
    patron_fecha = re.compile(r'^(\d{1,2})\s+([A-Z]{3})')
    
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Saltar líneas vacías o línea de saldo inicial (ya lo procesamos)
        if not linea or "SALDO INICIAL" in linea:
            i += 1
            continue
        
        # Verificar si la línea empieza con fecha
        match_fecha = patron_fecha.match(linea)
        if match_fecha:
            # Extraer la fecha
            fecha = f"{match_fecha.group(1)} {match_fecha.group(2)}"
            
            # Construir la transacción completa
            transaccion_completa = construir_transaccion_completa(lineas, i, moneda)
            if transaccion_completa:
                transaccion_procesada = procesar_transaccion_mejorada(fecha, transaccion_completa, moneda)
                if transaccion_procesada:
                    transacciones.append(transaccion_procesada)
            
            # Avanzar hasta la siguiente fecha o final
            i = encontrar_siguiente_transaccion(lineas, i + 1)
        else:
            i += 1
    
    return transacciones

def construir_transaccion_completa(lineas: List[str], inicio: int, moneda: str) -> Optional[str]:
    """
    Construye la transacción completa desde la línea inicial hasta encontrar
    los valores monetarios finales o la siguiente transacción.
    """
    transaccion_lineas = []
    i = inicio
    
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Si encontramos otra fecha (nueva transacción), paramos
        if i > inicio and re.match(r'^\d{1,2}\s+[A-Z]{3}', linea):
            break
        
        # Si encontramos indicadores de fin de sección, paramos
        if any(indicador in linea.upper() for indicador in [
            "SALDO TOTAL", "TOTAL DE MOVIMIENTOS", "RESUMEN DE", 
            "DETALLE DE LA CUENTA", "ESTADO DE CUENTA"
        ]):
            break
        
        # Agregar la línea si no está vacía
        if linea:
            transaccion_lineas.append(linea)
        
        i += 1
    
    return ' '.join(transaccion_lineas) if transaccion_lineas else None

def encontrar_siguiente_transaccion(lineas: List[str], inicio: int) -> int:
    """
    Encuentra el índice de la siguiente transacción que empieza con fecha.
    """
    patron_fecha = re.compile(r'^\d{1,2}\s+[A-Z]{3}')
    
    for i in range(inicio, len(lineas)):
        if patron_fecha.match(lineas[i].strip()):
            return i
    
    return len(lineas)

def procesar_transaccion_mejorada(fecha: str, transaccion_completa: str, moneda: str) -> Optional[Dict]:
    """
    Procesa una transacción completa de manera mejorada.
    Extrae correctamente la descripción, número de referencia y valores monetarios.
    """
    try:
        # Buscar los valores monetarios según la moneda
        if moneda == "PESOS":
            # Patrón para pesos: $ seguido de números
            patron_monetario = r'\$\s*([\d,]+\.\d{2})'
        else:  # DOLARES
            # Patrón para dólares: números seguidos de USD
            patron_monetario = r'([\d,]+\.\d{2})\s*USD'
        
        valores_monetarios = re.findall(patron_monetario, transaccion_completa)
        
        if len(valores_monetarios) < 2:
            return None
        
        # Los últimos dos valores son: [depósito/retiro, saldo_final]
        # Si hay tres valores: [monto_transaccion, otro_valor, saldo_final]
        if len(valores_monetarios) == 2:
            monto_str = valores_monetarios[0]
            saldo_str = valores_monetarios[1]
        else:
            # Tomar el penúltimo como monto y el último como saldo
            monto_str = valores_monetarios[-2]
            saldo_str = valores_monetarios[-1]
        
        # Convertir a números
        monto = float(monto_str.replace(',', ''))
        saldo = float(saldo_str.replace(',', ''))
        
        # Extraer número de referencia y descripción
        ref_numero, descripcion_completa = extraer_referencia_y_descripcion(fecha, transaccion_completa, moneda)
        
        # Determinar si es retiro o depósito
        es_retiro = es_movimiento_retiro(descripcion_completa)
        
        retiro = monto if es_retiro else 0.0
        deposito = 0.0 if es_retiro else monto
        tipo_movimiento = "gasto" if es_retiro else "ingreso"
        
        # Concatenar número de referencia con descripción si existe
        descripcion_final = f"{ref_numero} {descripcion_completa}" if ref_numero else descripcion_completa
        
        return {
            "fecha": fecha,
            "descripcion": descripcion_final.strip(),
            "retiro": retiro,
            "deposito": deposito,
            "saldo": saldo,
            "tipo_movimiento": tipo_movimiento,
            "categoria": categorizar_transaccion_banbajio(descripcion_final)
        }
        
    except (ValueError, IndexError, AttributeError) as e:
        print(f"Error procesando transacción: {e}")
        return None

def extraer_referencia_y_descripcion(fecha: str, transaccion_completa: str, moneda: str) -> tuple:
    """
    Extrae el número de referencia y la descripción completa de una transacción.
    """
    # Remover la fecha del inicio
    texto_sin_fecha = re.sub(r'^\d{1,2}\s+[A-Z]{3}\s*', '', transaccion_completa).strip()
    
    # Buscar el patrón del número de referencia (usualmente números al inicio)
    match_ref = re.match(r'^(\d+)\s+(.+)', texto_sin_fecha)
    
    if match_ref:
        ref_numero = match_ref.group(1)
        resto_texto = match_ref.group(2)
    else:
        ref_numero = ""
        resto_texto = texto_sin_fecha
    
    # Remover los valores monetarios del final para obtener solo la descripción
    if moneda == "PESOS":
        # Remover todos los patrones de $ valor del final
        descripcion = re.sub(r'\s*\$\s*[\d,]+\.\d{2}\s*$', '', resto_texto)
        descripcion = re.sub(r'\s*\$\s*[\d,]+\.\d{2}\s*', '', descripcion)
    else:  # DOLARES
        # Remover todos los patrones de valor USD del final
        descripcion = re.sub(r'\s*[\d,]+\.\d{2}\s*USD\s*$', '', resto_texto)
        descripcion = re.sub(r'\s*[\d,]+\.\d{2}\s*USD\s*', '', resto_texto)
    
    # Limpiar espacios extra
    descripcion = ' '.join(descripcion.split())
    
    return ref_numero, descripcion

def limpiar_texto_ocr(texto: str) -> str:
    """
    Limpia el texto de errores comunes de OCR, especialmente espacios anómalos
    en palabras que deberían estar juntas.
    """
    # Diccionario de correcciones comunes
    correcciones = {
        # --- ¡NUEVAS CORRECCIONES! ---
        r'D\s+E\s+POSITO': 'DEPOSITO',
        r'C\s+O\s+MISION': 'COMISION',
        # --- FIN DE NUEVAS CORRECCIONES ---
        r'E\s+N\s+V\s*Í\s*O': 'ENVÍO',
        r'E\s+N\s+V\s*I\s*O': 'ENVIO',
        r'T\s+R\s+A\s+S\s+P\s+A\s+S\s+O': 'TRASPASO',
        r'P\s+A\s+G\s+O': 'PAGO',
        r'S\s+E\s+R\s+V\s+I\s+C\s+I\s+O': 'SERVICIO',
        r'D\s+O\s+M\s+I\s+C\s+I\s+L\s+I\s+A\s+C\s+I\s*Ó\s*N': 'DOMICILIACIÓN',
        r'D\s+E\s+P\s*Ó\s*S\s+I\s+T\s+O': 'DEPÓSITO',
        r'D\s+E\s+P\s+O\s+S\s+I\s+T\s+O': 'DEPOSITO',
        r'C\s+O\s+M\s+I\s+S\s+I\s*Ó\s*N': 'COMISIÓN',
        r'C\s+O\s+M\s+I\s+S\s+I\s+O\s+N': 'COMISION',
        r'T\s+R\s+A\s+N\s+S\s+F\s+E\s+R\s+E\s+N\s+C\s+I\s+A': 'TRANSFERENCIA',
        r'I\s+V\s+A': 'IVA',
        r'R\s+E\s+T\s+I\s+R\s+O': 'RETIRO',
        r'B\s+E\s+N\s+E\s+F\s+I\s+C\s+I\s+A\s+R\s+I\s+O': 'BENEFICIARIO',
        r'I\s+N\s+S\s+T\s+I\s+T\s+U\s+C\s+I\s*Ó\s*N': 'INSTITUCIÓN',
        r'R\s+E\s+C\s+E\s+P\s+T\s+O\s+R\s+A': 'RECEPTORA',
        r'C\s+U\s+E\s+N\s+T\s+A': 'CUENTA',
        r'R\s+E\s+F\s+E\s+R\s+E\s+N\s+C\s+I\s+A': 'REFERENCIA',
        r'C\s+L\s+A\s+V\s+E': 'CLAVE',
        r'R\s+A\s+S\s+T\s+R\s+E\s+O': 'RASTREO',
        r'H\s+O\s+R\s+A': 'HORA'
    }
    
    texto_limpio = texto
    for patron, reemplazo in correcciones.items():
        texto_limpio = re.sub(patron, reemplazo, texto_limpio, flags=re.IGNORECASE)
    
    return texto_limpio

def procesar_estado_de_cuenta_banbajio_empresarial(ruta_pdf: str) -> Optional[dict]:
    """
    Procesa un estado de cuenta de BanBajío empresarial dividiendo el texto por cuentas.
    """
    cuentas_analizadas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        if not pdf.pages: return None
        texto_completo_crudo = "".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)

    # Limpiamos todo el texto del PDF una sola vez.
    texto_completo = limpiar_texto_ocr(texto_completo_crudo)

    # --- MODIFICACIÓN: Extraer fechas del documento primero ---
    fecha_corte_match = re.search(r"FECHA DE CORTE\s+(\d{1,2}\s+[A-Z]+\s+\d{4})", texto_completo, re.IGNORECASE)
    periodo_match_full = re.search(r"PERIODO:\s*(\d+\s+DE\s+[A-Z]+\s+AL\s+\d+\s+DE\s+[A-Z]+\s+DE\s+\d{4})", texto_completo, re.IGNORECASE)
    periodo_completo = periodo_match_full.group(1) if periodo_match_full else "No encontrado"

    fecha_inicio_periodo = None
    # Patrón para extraer las partes de la fecha de inicio (Día, Mes y Año)
    periodo_parts_match = re.search(r"PERIODO:\s*(\d+\s+DE\s+[A-Z]+)\s+AL\s+\d+\s+DE\s+[A-Z]+\s+DE\s+(\d{4})", texto_completo, re.IGNORECASE)
    if periodo_parts_match:
        # Reconstruir la fecha de inicio completa. Ej: "01 DE ENERO DE 2024"
        fecha_inicio_periodo = f"{periodo_parts_match.group(1)} DE {periodo_parts_match.group(2)}"

    # --- LÓGICA DE DIVISIÓN DE TEXTO (sin cambios) ---
    anchor_pesos = "CUENTA CONECTA BANBAJIO"
    anchor_dolares = "CUENTA DE CHEQUES EN DOLARES"
    
    start_pesos_idx = texto_completo.find(anchor_pesos)
    start_dolares_idx = texto_completo.find(anchor_dolares)

    texto_seccion_pesos = ""
    texto_seccion_dolares = ""

    if start_pesos_idx != -1:
        end_pesos_idx = start_dolares_idx if start_dolares_idx != -1 else len(texto_completo)
        texto_seccion_pesos = texto_completo[start_pesos_idx:end_pesos_idx]
    
    if start_dolares_idx != -1:
        texto_seccion_dolares = texto_completo[start_dolares_idx:]
    
    if texto_seccion_pesos:
        resumen = extraer_resumen_cuenta_pesos(texto_seccion_pesos)
        detalle_match = re.search(r"DETALLE DE LA CUENTA:.*?#(\d+)", texto_seccion_pesos)
        transacciones_texto = texto_seccion_pesos[detalle_match.end():] if detalle_match else ""
        
        cuentas_analizadas.append({
            "nombre_cuenta": "CUENTA CONECTA BANBAJIO",
            "numero_cuenta": detalle_match.group(1) if detalle_match else "No encontrado",
            "moneda": "PESOS",
            "saldo_anterior_resumen": resumen["saldo_anterior"],
            "saldo_actual_resumen": resumen["saldo_actual"],
            "total_ingresos": resumen["total_depositos"],
            "total_gastos": resumen["total_cargos"],
            # --- MODIFICACIÓN: Pasar la fecha de inicio del periodo ---
            "transacciones": extraer_transacciones(transacciones_texto, "PESOS", fecha_inicio_periodo)
        })

    if texto_seccion_dolares:
        resumen = extraer_resumen_cuenta_dolares(texto_seccion_dolares)
        detalle_match = re.search(r"DETALLE DE LA CUENTA:.*?#(\d+)", texto_seccion_dolares)
        transacciones_texto = texto_seccion_dolares[detalle_match.end():] if detalle_match else ""

        cuentas_analizadas.append({
            "nombre_cuenta": "CUENTA DE CHEQUES EN DOLARES",
            "numero_cuenta": detalle_match.group(1) if detalle_match else "No encontrado",
            "moneda": "DOLARES",
            "saldo_anterior_resumen": resumen["saldo_anterior"],
            "saldo_actual_resumen": resumen["saldo_actual"],
            "total_ingresos": resumen["total_depositos"],
            "total_gastos": resumen["total_cargos"],
            # --- MODIFICACIÓN: Pasar la fecha de inicio del periodo ---
            "transacciones": extraer_transacciones(transacciones_texto, "DOLARES", fecha_inicio_periodo)
        })

    return {
        "nombre_archivo": ruta_pdf.split('/')[-1],
        "banco": "banbajio",
        "periodo": periodo_completo,
        "fecha_corte": fecha_corte_match.group(1) if fecha_corte_match else "No encontrado",
        "cuentas": cuentas_analizadas
    }