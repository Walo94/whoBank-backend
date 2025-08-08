# pdf_processor_santander.py
import pdfplumber
import re
from typing import List, Dict, Optional
from app.schemas.analysisSantander import AnalisisSantanderPDF, CuentaAnalisis, Transaccion
from app.services.ocr_processor import extraer_texto_con_ocr

def extraer_periodo(texto_completo: str) -> str:
    """
    Extrae el período del estado de cuenta.
    """
    match = re.search(r"PERIODO\s*DEL\s*(\d{2}-[A-Z]{3}-\d{4})\s*AL\s*(\d{2}-[A-Z]{3}-\d{4})", texto_completo)
    if match:
        return f"DEL {match.group(1)} AL {match.group(2)}"
    return "No encontrado"

def extraer_resumen_cuenta_cheques(texto_completo: str) -> Dict[str, float]:
    """
    Extrae el saldo inicial, depósitos, retiros y saldo final de la sección 'Cuenta de cheques'.
    """
    saldo_inicial_match = re.search(r"Saldo inicial\s*\n*\s*([\d,]+\.\d{2})", texto_completo)
    depositos_match = re.search(r"\+Depósitos\s*\n*\s*([\d,]+\.\d{2})", texto_completo)
    retiros_match = re.search(r"- Retiros\s*\n*\s*([\d,]+\.\d{2})", texto_completo)
    saldo_final_match = re.search(r"= Saldo final\s*\n*\s*([\d,]+\.\d{2})", texto_completo)

    return {
        "saldo_inicial": float(saldo_inicial_match.group(1).replace(",", "")) if saldo_inicial_match else 0.0,
        "depositos": float(depositos_match.group(1).replace(",", "")) if depositos_match else 0.0,
        "retiros": float(retiros_match.group(1).replace(",", "")) if retiros_match else 0.0,
        "saldo_final": float(saldo_final_match.group(1).replace(",", "")) if saldo_final_match else 0.0,
    }

def extraer_transacciones_tabla(texto_seccion: str) -> List[Transaccion]:
    """
    Extrae las transacciones de una tabla en el estado de cuenta.
    """
    transacciones = []
    lineas = texto_seccion.strip().split('\n')
    
    # Expresión regular para capturar las columnas de la tabla de transacciones
    patron_transaccion = re.compile(
        r"(\d{2}-[A-Z]{3}-\d{4})\s+"  # Fecha
        r"(\d+)\s+"                  # Folio
        r"(.+?)\s+"                  # Descripción
        r"([\d,]+\.\d{2})?\s*"       # Depósito (opcional)
        r"([\d,]+\.\d{2})?\s*"       # Retiro (opcional)
        r"([\d,]+\.\d{2})"           # Saldo
    )

    for linea in lineas:
        # Intenta hacer match con el patrón de una transacción completa en una línea
        match = patron_transaccion.match(linea.strip())
        if match:
            fecha, folio, descripcion, deposito_str, retiro_str, saldo_str = match.groups()
            
            # Limpieza y conversión de datos
            deposito = float(deposito_str.replace(",", "")) if deposito_str else 0.0
            retiro = float(retiro_str.replace(",", "")) if retiro_str else 0.0
            saldo = float(saldo_str.replace(",", ""))

            transacciones.append(
                Transaccion(
                    fecha=fecha,
                    folio=folio,
                    descripcion=descripcion.strip(),
                    deposito=deposito,
                    retiro=retiro,
                    saldo=saldo,
                )
            )
            
    return transacciones

def procesar_estado_de_cuenta_santander(ruta_pdf: str) -> Optional[AnalisisSantanderPDF]:
    """
    Procesa un estado de cuenta de Santander usando OCR.
    """
    # --- MODIFICACIÓN: Se reemplaza pdfplumber con el procesador OCR ---
    texto_completo = extraer_texto_con_ocr(ruta_pdf)

    if not texto_completo:
        # Si el OCR falla, no se puede continuar.
        return None

    texto_completo = texto_completo_ocr.replace('º', 'o').replace('—', '-')

    periodo = extraer_periodo(texto_completo)
    cuentas = []

    # --- El resto de la lógica de análisis de texto no cambia ---
    # La ventaja es que ahora tienes el texto extraído (aunque con posibles errores de OCR)
    # y puedes aplicar las mismas expresiones regulares.

    # --- Análisis de la Cuenta de Cheques ---
    seccion_cheques_match = re.search(r"Detalle de movimientos cuenta de cheques(.+?)Detalles de movimientos Dinero Creciente Santander", texto_completo, re.DOTALL)
    if seccion_cheques_match:
        texto_cheques = seccion_cheques_match.group(1)
        resumen_cheques = extraer_resumen_cuenta_cheques(texto_completo)
        transacciones_cheques = extraer_transacciones_tabla(texto_cheques)
        
        cuentas.append(
            CuentaAnalisis(
                nombre_cuenta="Cuenta de cheques",
                saldo_inicial=resumen_cheques["saldo_inicial"],
                depositos=resumen_cheques["depositos"],
                retiros=resumen_cheques["retiros"],
                saldo_final=resumen_cheques["saldo_final"],
                transacciones=transacciones_cheques,
            )
        )

    # --- Análisis de la Cuenta DineroCreciente ---
    seccion_creciente_match = re.search(r"Detalles de movimientos Dinero Creciente Santander(.+?)Información fiscal", texto_completo, re.DOTALL)
    if seccion_creciente_match:
        texto_creciente = seccion_creciente_match.group(1)
        transacciones_creciente = extraer_transacciones_tabla(texto_creciente)

        cuentas.append(
            CuentaAnalisis(
                nombre_cuenta="DineroCreciente",
                saldo_inicial=0.0,
                depositos=0.0,
                retiros=0.0,
                saldo_final=0.0,
                transacciones=transacciones_creciente,
            )
        )
    
    return AnalisisSantanderPDF(
        nombre_archivo=ruta_pdf.split('/')[-1],
        periodo=periodo,
        cuentas=cuentas,
    )