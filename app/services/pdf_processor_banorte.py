import pdfplumber
import re
from typing import List, Dict, Optional
from datetime import datetime
# Se importan los modelos desde el nuevo archivo de esquemas
from app.schemas.analysisBanorte import Transaccion, CuentaAnalisis, AnalisisPDF


# --- SECCIÓN DE FUNCIONES DE EXTRACCIÓN PARA BANORTE ---
def limpiar_valor_monetario(valor: Optional[str]) -> float:
    """Convierte una cadena de texto monetaria (ej. '$1,234.56' o '1,234.56') a float."""
    if not valor or not isinstance(valor, str):
        return 0.0
    valor_limpio = valor.replace('$', '').replace(',', '').strip()
    try:
        return float(valor_limpio) if valor_limpio else 0.0
    except ValueError:
        return 0.0

def extraer_datos_generales_banorte(texto_completo: str) -> Dict:
    """Extrae la información general del encabezado del estado de cuenta."""
    periodo_match = re.search(r"Periodo\s*Del\s*(\d{2}/\w+/\d{4}\s*al\s*\d{2}/\w+/\d{4})", texto_completo, re.IGNORECASE)
    fecha_corte_match = re.search(r"Fecha de corte\s*(\d{2}/\w+/\d{4})", texto_completo, re.IGNORECASE)
    
    # FIX: Búsqueda mejorada para el número de cuenta, buscando 10 dígitos después del nombre de la cuenta.
    cuenta_match = re.search(r"CUENTA PREFERENTE\s+(\d{10})", texto_completo)
    
    moneda_match = re.search(r"Moneda\s*,?\s*(\w+)", texto_completo)

    return {
        "periodo": periodo_match.group(1).replace('\n', ' ').strip() if periodo_match else "No encontrado",
        "fecha_corte": fecha_corte_match.group(1) if fecha_corte_match else "No encontrado",
        "numero_cuenta": cuenta_match.group(1) if cuenta_match else "No encontrado",
        "moneda": moneda_match.group(1).upper() if moneda_match else "No encontrado",
        "nombre_cuenta": "CUENTA PREFERENTE"
    }

def extraer_resumen_banorte(texto_completo: str) -> Dict:
    """Extrae los totales del 'Resumen del periodo'."""
    saldo_inicial_match = re.search(r"Saldo inicial del periodo\s*\$ ([\d,]+\.\d{2})", texto_completo)
    depositos_match = re.search(r"Total de depósitos\s*\$ ([\d,]+\.\d{2})", texto_completo)
    retiros_match = re.search(r"Total de retiros\s*\$ ([\d,]+\.\d{2})", texto_completo)
    saldo_actual_match = re.search(r"Saldo actual\s*\$ ([\d,]+\.\d{2})", texto_completo)

    return {
        "saldo_anterior": limpiar_valor_monetario(saldo_inicial_match.group(1) if saldo_inicial_match else '0'),
        "total_depositos": limpiar_valor_monetario(depositos_match.group(1) if depositos_match else '0'),
        "total_retiros": limpiar_valor_monetario(retiros_match.group(1) if retiros_match else '0'),
        "saldo_actual": limpiar_valor_monetario(saldo_actual_match.group(1) if saldo_actual_match else '0'),
    }

def categorizar_transaccion_banorte(descripcion: str) -> str:
    """Categoriza las transacciones de Banorte basándose en palabras clave."""
    desc = descripcion.upper()
    if "SPEI" in desc and ("COMPRA" in desc or "ORDEN DE PAGO" in desc):
        return "Transferencia SPEI Enviada"
    elif "DEPOSITO" in desc and "TERCEROS" in desc:
        return "Depósito de Terceros"
    elif "DEPOSITO" in desc:
        return "Depósito"
    elif "COMPRA" in desc:
        return "Compra"
    elif "COMISION" in desc or "COMISIÓN" in desc:
        return "Comisión"
    elif "SALDO ANTERIOR" in desc:
        return "Saldo Anterior"
    else:
        return "Otro"

def extraer_transacciones_banorte_texto(page: pdfplumber.page.Page) -> List[Transaccion]:
    """
    Método mejorado para extraer transacciones que valida los montos
    aritméticamente para evitar asignaciones incorrectas.
    """
    transacciones_obj = []
    texto_pagina = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
    
    if "DETALLE DE MOVIMIENTOS" not in texto_pagina:
        return transacciones_obj
    
    lineas = texto_pagina.split('\n')
    
    inicio_movimientos = -1
    for i, linea in enumerate(lineas):
        if "FECHA" in linea and "DESCRIPCIÓN" in linea and "SALDO" in linea:
            inicio_movimientos = i + 1
            break
    
    if inicio_movimientos == -1:
        return transacciones_obj
        
    i = inicio_movimientos
    while i < len(lineas):
        linea = lineas[i].strip()
        
        if not linea or "OTROS" in linea:
            i += 1
            continue
            
        match_fecha = re.match(r'^(\d{2}-\w{3}-\d{2})\s*(.+)', linea)
        if not match_fecha:
            i += 1
            continue
            
        fecha = match_fecha.group(1)
        resto_linea = match_fecha.group(2)
        
        descripcion_parcial = [resto_linea]
        # Usamos set para evitar duplicados si un monto aparece en varias líneas
        montos_encontrados_set = set(re.findall(r'([\d,]+\.\d{2})', resto_linea))
        
        j = i + 1
        while j < len(lineas):
            siguiente_linea = lineas[j].strip()
            if not siguiente_linea or re.match(r'^\d{2}-\w{3}-\d{2}', siguiente_linea) or "OTROS" in siguiente_linea:
                break
            descripcion_parcial.append(siguiente_linea)
            montos_encontrados_set.update(re.findall(r'([\d,]+\.\d{2})', siguiente_linea))
            j += 1
        
        montos_encontrados = list(montos_encontrados_set)
        
        descripcion = ' '.join(descripcion_parcial)
        for monto in montos_encontrados:
            descripcion = descripcion.replace(monto, '').strip()
        descripcion = ' '.join(descripcion.split())
        
        deposito = 0.0
        retiro = 0.0
        saldo = 0.0
        
        if len(montos_encontrados) == 1:
            saldo = limpiar_valor_monetario(montos_encontrados[0])

        elif len(montos_encontrados) == 2:
            # Obtenemos el saldo de la última transacción registrada para el cálculo
            last_saldo = transacciones_obj[-1].saldo if transacciones_obj else 0.0
            
            monto1 = limpiar_valor_monetario(montos_encontrados[0])
            monto2 = limpiar_valor_monetario(montos_encontrados[1])
            
            is_deposit = "DEPOSITO" in descripcion.upper()

            # --- LÓGICA DE VALIDACIÓN ARITMÉTICA ---
            if is_deposit:
                # Si es depósito: Saldo Anterior + Monto 1 = Monto 2?
                if abs((last_saldo + monto1) - monto2) < 0.01:
                    deposito, saldo = monto1, monto2
                # O es: Saldo Anterior + Monto 2 = Monto 1?
                elif abs((last_saldo + monto2) - monto1) < 0.01:
                    deposito, saldo = monto2, monto1
                else: # Fallback si la aritmética no coincide (poco común)
                    deposito, saldo = sorted([monto1, monto2])
            else: # Es retiro/gasto
                # Si es retiro: Saldo Anterior - Monto 1 = Monto 2?
                if abs((last_saldo - monto1) - monto2) < 0.01:
                    retiro, saldo = monto1, monto2
                # O es: Saldo Anterior - Monto 2 = Monto 1?
                elif abs((last_saldo - monto2) - monto1) < 0.01:
                    retiro, saldo = monto2, monto1
                else: # Fallback
                    retiro, saldo = sorted([monto1, monto2], reverse=True)

        elif len(montos_encontrados) >= 3:
            # La lógica original para 3 montos suele ser correcta
            deposito = limpiar_valor_monetario(montos_encontrados[0])
            retiro = limpiar_valor_monetario(montos_encontrados[1])
            saldo = limpiar_valor_monetario(montos_encontrados[2])

        # Asignar tipo de movimiento
        if "SALDO ANTERIOR" in descripcion.upper():
            tipo_movimiento = "saldo_anterior"
        elif deposito > 0:
            tipo_movimiento = "ingreso"
        elif retiro > 0:
            tipo_movimiento = "gasto"
        else:
            tipo_movimiento = "otro"
            
        transacciones_obj.append(Transaccion(
            fecha=fecha,
            descripcion=descripcion,
            retiro=retiro,
            deposito=deposito,
            saldo=saldo,
            tipo_movimiento=tipo_movimiento,
            categoria=categorizar_transaccion_banorte(descripcion)
        ))
        
        i = j
    
    return transacciones_obj

def extraer_transacciones_banorte_tabla(page: pdfplumber.page.Page) -> List[Transaccion]:
    """
    Extrae las transacciones usando coordenadas y posiciones específicas de Banorte.
    """
    transacciones_obj = []
    
    try:
        # Extraer texto con posiciones para mejor análisis
        texto_con_posiciones = page.extract_text_lines()
        
        # Buscar la tabla de movimientos
        inicio_tabla = -1
        for i, linea_info in enumerate(texto_con_posiciones):
            texto = linea_info.get('text', '')
            if "FECHA" in texto and "DESCRIPCIÓN" in texto and "SALDO" in texto:
                inicio_tabla = i + 1
                break
        
        if inicio_tabla == -1:
            return []
        
        # Procesar líneas de la tabla
        transaccion_actual = None
        
        for linea_info in texto_con_posiciones[inicio_tabla:]:
            texto_linea = linea_info.get('text', '').strip()
            
            if not texto_linea or "OTROS" in texto_linea:
                break
            
            # Verificar si es una nueva transacción (empieza con fecha)
            match_fecha = re.match(r'^(\d{2}-\w{3}-\d{2})\s*(.+)', texto_linea)
            
            if match_fecha:
                # Finalizar transacción anterior si existe
                if transaccion_actual:
                    transacciones_obj.append(transaccion_actual)
                
                # Iniciar nueva transacción
                fecha = match_fecha.group(1)
                resto_texto = match_fecha.group(2)
                
                # Extraer montos de la línea usando posiciones
                montos = re.findall(r'([\d,]+\.\d{2})', resto_texto)
                
                # Determinar valores según estructura de columnas
                deposito = 0.0
                retiro = 0.0
                saldo = 0.0
                
                if len(montos) == 1:
                    # Solo saldo (caso SALDO ANTERIOR)
                    saldo = limpiar_valor_monetario(montos[0])
                elif len(montos) == 2:
                    # Puede ser: deposito+saldo o retiro+saldo
                    primer_valor = limpiar_valor_monetario(montos[0])
                    saldo = limpiar_valor_monetario(montos[1])
                    
                    # Determinar si es depósito o retiro por posición en la línea
                    # Buscar posición aproximada del primer monto
                    pos_primer_monto = resto_texto.find(montos[0])
                    texto_antes_monto = resto_texto[:pos_primer_monto].strip()
                    
                    if "DEPOSITO" in texto_antes_monto.upper():
                        deposito = primer_valor
                    else:
                        retiro = primer_valor
                elif len(montos) >= 3:
                    # deposito, retiro, saldo
                    deposito = limpiar_valor_monetario(montos[0])
                    retiro = limpiar_valor_monetario(montos[1])
                    saldo = limpiar_valor_monetario(montos[2])
                
                # Extraer descripción (quitar montos)
                descripcion = resto_texto
                for monto in montos:
                    descripcion = descripcion.replace(monto, '')
                descripcion = ' '.join(descripcion.split())  # Limpiar espacios
                
                # Determinar tipo de movimiento
                if "SALDO ANTERIOR" in descripcion.upper():
                    tipo_movimiento = "saldo_anterior"
                elif deposito > 0:
                    tipo_movimiento = "ingreso"
                elif retiro > 0:
                    tipo_movimiento = "gasto"
                else:
                    tipo_movimiento = "otro"
                
                transaccion_actual = Transaccion(
                    fecha=fecha,
                    descripcion=descripcion,
                    retiro=retiro,
                    deposito=deposito,
                    saldo=saldo,
                    tipo_movimiento=tipo_movimiento,
                    categoria=categorizar_transaccion_banorte(descripcion)
                )
            
            elif transaccion_actual:
                # Línea de continuación de descripción
                # Quitar posibles montos que puedan estar duplicados
                texto_limpio = texto_linea
                montos_linea = re.findall(r'([\d,]+\.\d{2})', texto_linea)
                
                # Si hay montos nuevos, actualizar la transacción
                if montos_linea and not any(re.search(re.escape(m), transaccion_actual.descripcion) for m in montos_linea):
                    # Actualizar montos si es necesario
                    if len(montos_linea) >= 2 and transaccion_actual.saldo == 0:
                        if "DEPOSITO" in transaccion_actual.descripcion.upper():
                            transaccion_actual.deposito = limpiar_valor_monetario(montos_linea[0])
                        else:
                            transaccion_actual.retiro = limpiar_valor_monetario(montos_linea[0])
                        transaccion_actual.saldo = limpiar_valor_monetario(montos_linea[-1])
                
                # Agregar a descripción (sin montos)
                for monto in montos_linea:
                    texto_limpio = texto_limpio.replace(monto, '')
                
                if texto_limpio.strip():
                    transaccion_actual.descripcion += " " + texto_limpio.strip()
        
        # Agregar última transacción
        if transaccion_actual:
            transacciones_obj.append(transaccion_actual)
            
    except Exception as e:
        print(f"Error en extracción por tabla: {e}")
        return []
    
    return transacciones_obj

def extraer_transacciones_banorte(page: pdfplumber.page.Page) -> List[Transaccion]:
    """
    Función principal que intenta primero extracción por texto y luego por tabla.
    """
    # Intentar primero con extracción de texto (más confiable para Banorte)
    transacciones = extraer_transacciones_banorte_texto(page)
    
    # Si no se encontraron transacciones, usar método de tabla
    if not transacciones:
        transacciones = extraer_transacciones_banorte_tabla(page)
    
    return transacciones

# --- ORQUESTADOR PRINCIPAL ---

def procesar_estado_de_cuenta_banorte(ruta_pdf: str) -> Optional[dict]:
    """
    Procesa un estado de cuenta de Banorte, extrae la información clave y la estructura.
    """
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            if not pdf.pages: 
                return None
            
            # Extraer texto completo para datos generales y resumen
            texto_completo = "\n".join(
                page.extract_text(x_tolerance=2, y_tolerance=2) or "" 
                for page in pdf.pages
            )
            
            datos_generales = extraer_datos_generales_banorte(texto_completo)
            resumen = extraer_resumen_banorte(texto_completo)
            
            # Extraer transacciones de todas las páginas
            transacciones_totales = []
            for i, page in enumerate(pdf.pages):
                texto_pagina = page.extract_text() or ""
                
                # Solo procesar páginas con movimientos
                if "DETALLE DE MOVIMIENTOS" in texto_pagina:
                    print(f"Procesando transacciones en página {i+1}")
                    transacciones_pagina = extraer_transacciones_banorte(page)
                    transacciones_totales.extend(transacciones_pagina)
                    print(f"Encontradas {len(transacciones_pagina)} transacciones en página {i+1}")
            
            # Ordenar transacciones por fecha (SALDO ANTERIOR primero)
            def fecha_a_datetime(fecha_str):
                try:
                    # Convertir formato DD-MMM-YY a datetime
                    meses = {
                        'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
                        'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
                    }
                    parts = fecha_str.split('-')
                    dia = int(parts[0])
                    mes = meses.get(parts[1], 1)
                    año = 2000 + int(parts[2])  # Asumir años 20XX
                    return datetime(año, mes, dia)
                except:
                    return datetime.min
            
            # Separar saldo anterior del resto
            saldo_anterior = [t for t in transacciones_totales if t.tipo_movimiento == "saldo_anterior"]
            otras_transacciones = [t for t in transacciones_totales if t.tipo_movimiento != "saldo_anterior"]
            
            # Ordenar otras transacciones por fecha
            otras_transacciones.sort(key=lambda t: fecha_a_datetime(t.fecha))
            
            # Combinar: saldo anterior primero, luego el resto cronológicamente
            transacciones_ordenadas = saldo_anterior + otras_transacciones
            
            print(f"Total de transacciones extraídas: {len(transacciones_ordenadas)}")
            
            # Debug: mostrar transacciones encontradas
            for i, t in enumerate(transacciones_ordenadas):
                print(f"{i+1}. {t.fecha} - {t.descripcion[:50]}... - D:{t.deposito} R:{t.retiro} S:{t.saldo}")
            
            # Crear objeto cuenta
            cuenta = CuentaAnalisis(
                nombre_cuenta=datos_generales["nombre_cuenta"], 
                numero_cuenta=datos_generales["numero_cuenta"],
                moneda=datos_generales["moneda"], 
                saldo_anterior_resumen=resumen["saldo_anterior"],
                saldo_actual_resumen=resumen["saldo_actual"], 
                total_ingresos=resumen["total_depositos"],
                total_gastos=resumen["total_retiros"], 
                transacciones=transacciones_ordenadas
            )
            
            # Crear respuesta final
            respuesta = AnalisisPDF(
                nombre_archivo=ruta_pdf.split('/')[-1], 
                banco="banorte", 
                periodo=datos_generales["periodo"],
                fecha_corte=datos_generales["fecha_corte"], 
                cuentas=[cuenta]
            )

            return respuesta.model_dump()
            
    except Exception as e:
        print(f"Error procesando PDF: {e}")
        return None