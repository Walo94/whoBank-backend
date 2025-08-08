# analysisSantander.py
from pydantic import BaseModel
from typing import List, Optional

class Transaccion(BaseModel):
    """
    Modelo para una transacción individual en el estado de cuenta de Santander.
    """
    fecha: str
    folio: str
    descripcion: str
    deposito: float = 0.0
    retiro: float = 0.0
    saldo: float

class CuentaAnalisis(BaseModel):
    """
    Modelo para el análisis de una sola cuenta dentro del estado de cuenta de Santander.
    """
    nombre_cuenta: str
    saldo_inicial: float
    depositos: float
    retiros: float
    saldo_final: float
    transacciones: List[Transaccion]

class AnalisisSantanderPDF(BaseModel):
    """
    Modelo principal para la respuesta del análisis del estado de cuenta de Santander.
    """
    nombre_archivo: str
    banco: str = "Santander"
    fecha_corte: Optional[str] = None
    periodo: str
    cuentas: List[CuentaAnalisis]