import pdfplumber
import re
from typing import List, Dict, Optional
from app.schemas.analysisScotiabank import AnalisisScotiabankPDF, CuentaAnalisis, Transaccion


def limpiar_valor_monetario(valor: Optional[str]) -> float:
    if not valor or not isinstance(valor, str):
        return 0.0
    return float(valor.replace('$', '').replace(',', '').strip() or 0.0)


def extraer_encabezado(texto: str) -> Dict[str, str]:
    periodo_match = re.search(r"Periodo\s*([\d\w\-/]+)", texto)
    clabe_match = re.search(r"CLABE\s*(\d+)", texto)
    fecha_corte_match = re.search(r"Fecha de corte\s*([\d\w\-/]+)", texto)

    return {
        "periodo": periodo_match.group(1) if periodo_match else "No encontrado",
        "clabe": clabe_match.group(1) if clabe_match else "No encontrada",
        "fecha_corte": fecha_corte_match.group(1) if fecha_corte_match else "No encontrada"
    }


def extraer_resumen_saldos(texto: str) -> Dict[str, float]:
    saldo_inicial_match = re.search(r"Saldo\s*inicial\s*=?\s*\$?\s*([\d,]+\.\d{2})", texto, re.IGNORECASE)
    saldo_final_match = re.search(r"Saldo\s*final\s*(de la cuenta)?\s*=?\s*\$?\s*([\d,]+\.\d{2})", texto, re.IGNORECASE)
    depositos_match = re.search(r"\(\+\)\s*Dep[oó]sitos\s*\$?\s*([\d,]+\.\d{2})", texto, re.IGNORECASE)
    retiros_match = re.search(r"\(\-\)\s*Retiros\s*\$?\s*([\d,]+\.\d{2})", texto, re.IGNORECASE)

    return {
        "saldo_inicial": limpiar_valor_monetario(saldo_inicial_match.group(1) if saldo_inicial_match else '0'),
        "depositos": limpiar_valor_monetario(depositos_match.group(1) if depositos_match else '0'),
        "retiros": limpiar_valor_monetario(retiros_match.group(1) if retiros_match else '0'),
        "saldo_final": limpiar_valor_monetario(
            saldo_final_match.group(2) if saldo_final_match and saldo_final_match.lastindex >= 2
            else (saldo_final_match.group(1) if saldo_final_match else '0')
        ),
    }


def extraer_transacciones(page, saldo_inicial_resumen: float) -> List[Transaccion]:
    texto_pagina = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
    lineas = texto_pagina.split('\n')

    STOP_WORDS = [
        "LAS TASAS DE INTERES ESTAN EXPRESADAS",
        "Para los efectos del art. 100",
        "Scotiabank Inverlat S.A",
        "Total de comisiones cobradas"
    ]

    inicio_tabla = -1
    fin_tabla = len(lineas)
    for i, linea in enumerate(lineas):
        if "Fecha" in linea and "Concepto" in linea and "Saldo" in linea:
            inicio_tabla = i + 1
        if inicio_tabla != -1 and any(stop_word in linea for stop_word in STOP_WORDS):
            fin_tabla = i
            break
    
    if inicio_tabla == -1: return []

    lineas_tabla = [l.strip() for l in lineas[inicio_tabla:fin_tabla] if l.strip()]

    transacciones_agrupadas = []
    transaccion_actual_lineas = []
    
    for linea in lineas_tabla:
        # ## ANOTACIÓN CLAVE: Expresión regular actualizada para aceptar "DD MON" y "MON DD".
        # Esta es la corrección principal que soluciona el problema de agrupación.
        if re.match(r'^(?:\d{2}\s+[A-Z]{3}|[A-Z]{3}\s+\d{2})\b', linea):
            if transaccion_actual_lineas:
                transacciones_agrupadas.append(transaccion_actual_lineas)
            transaccion_actual_lineas = [linea]
        else:
            if transaccion_actual_lineas:
                transaccion_actual_lineas.append(linea)
    
    if transaccion_actual_lineas:
        transacciones_agrupadas.append(transaccion_actual_lineas)

    saldo_anterior = -1
    lista_transacciones_obj = []

    for tx_lineas in transacciones_agrupadas:
        if not tx_lineas: continue
        
        primera_linea = tx_lineas[0]
        fecha_match = re.match(r'^(?:\d{2}\s+[A-Z]{3}|[A-Z]{3}\s+\d{2})\b', primera_linea)
        fecha = fecha_match.group(0) if fecha_match else "Fecha Desconocida"
        
        montos_str = re.findall(r'\$?[\d,]+\.\d{2}', primera_linea)
        montos = [limpiar_valor_monetario(m) for m in montos_str]

        deposito, retiro, saldo, monto_operacion = 0.0, 0.0, 0.0, 0.0
        
        if not montos: continue

        saldo = montos[-1]
        if len(montos) > 1:
            monto_operacion = montos[-2]
        
        if saldo_anterior != -1:
            diferencia = saldo - saldo_anterior
            if abs(diferencia - monto_operacion) < 0.01:
                deposito = monto_operacion
            elif abs(diferencia + monto_operacion) < 0.01:
                retiro = monto_operacion
            else:
                if diferencia > 0: deposito = diferencia
                else: retiro = abs(diferencia)
        elif monto_operacion > 0:
             if any(k in primera_linea.upper() for k in ["DEPOSITO", "ABONO", "TRANSF INTERBANCARIA", "TRASPASO" , "COMISION"]):
                 deposito = monto_operacion
             else:
                 retiro = monto_operacion

        saldo_anterior = saldo
        
        concepto_completo = " ".join(tx_lineas)
        concepto_limpio = concepto_completo.replace(fecha, '', 1)
        for m_str in montos_str:
            concepto_limpio = concepto_limpio.replace(m_str, '')
        
        concepto_final = re.sub(r'\s+', ' ', concepto_limpio).strip()

        lista_transacciones_obj.append(Transaccion(
            fecha=fecha,
            concepto=concepto_final,
            deposito=deposito,
            retiro=retiro,
            saldo=saldo
        ))

    return lista_transacciones_obj

def procesar_estado_de_cuenta_scotiabank(ruta_pdf: str) -> Optional[AnalisisScotiabankPDF]:
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            texto_completo = "\n".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)
            
            encabezado = extraer_encabezado(texto_completo)
            resumen = extraer_resumen_saldos(texto_completo)

            transacciones_totales = []
            # Tomamos el saldo final de la primera página como punto de partida para el cálculo de saldo_anterior
            # ya que el saldo inicial del resumen es de todo el periodo.
            # Esta es una heurística y podría necesitar ajuste si el formato cambia.
            # Una mejor aproximación podría ser buscar el saldo de la transacción justo antes de la tabla.
            saldo_inicial_calculo = resumen.get("saldo_inicial", 0.0)

            for idx, page in enumerate(pdf.pages):
                texto_pagina = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                if "Detalle de tus movimientos" not in texto_pagina and "Concepto" not in texto_pagina:
                    continue
                
                txs = extraer_transacciones(page, saldo_inicial_calculo)
                
                if txs:
                    print(f"Página {idx+1}: encontradas {len(txs)} transacciones")
                transacciones_totales.extend(txs)

            cuenta = CuentaAnalisis(
                numero_cuenta=encabezado.get("clabe", ""),
                saldo_inicial=resumen["saldo_inicial"],
                depositos=resumen["depositos"],
                retiros=resumen["retiros"],
                saldo_final=resumen["saldo_final"],
                transacciones=transacciones_totales
            )

            return AnalisisScotiabankPDF(
                nombre_archivo=ruta_pdf.split('/')[-1],
                banco="Scotiabank",
                periodo=encabezado["periodo"],
                fecha_corte=encabezado["fecha_corte"],
                cuenta_clabe=encabezado["clabe"],
                cuentas=[cuenta],
            )
    except Exception as e:
        print("Error procesando Scotiabank:", e)
        import traceback; traceback.print_exc()
        return None