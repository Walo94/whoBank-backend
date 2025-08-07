from pydantic import BaseModel
from typing import List, Optional

class Transaccion(BaseModel):
    """
    Define la estructura para una transacción individual.
    """
    fecha: str
    descripcion: str
    retiro: float = 0.0
    deposito: float = 0.0
    saldo: Optional[float] = None
    tipo_movimiento: str
    categoria: str

class CuentaAnalisis(BaseModel):
    """
    Define la estructura para el análisis de una sola cuenta bancaria.
    """
    nombre_cuenta: Optional[str] = None
    numero_cuenta: Optional[str] = None
    moneda: Optional[str] = None
    saldo_anterior_resumen: Optional[float] = None
    saldo_actual_resumen: Optional[float] = None
    total_ingresos: float
    total_gastos: float
    transacciones: List[Transaccion]

class AnalisisPDF(BaseModel):
    """
    Define la estructura principal y genérica para la respuesta del análisis de un PDF.
    """
    nombre_archivo: str
    banco: str
    fecha_corte: Optional[str] = None
    periodo: Optional[str] = None
    cuentas: List[CuentaAnalisis]