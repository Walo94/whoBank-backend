from pydantic import BaseModel
from typing import List, Optional

# Modelo para una transacción individual (sin cambios)
class Transaccion(BaseModel):
    fecha: str
    descripcion: str
    retiro: float = 0.0
    deposito: float = 0.0
    saldo: Optional[float] = None
    tipo_movimiento: str
    categoria: str

# Nuevo: Modelo para el análisis de UNA SOLA cuenta dentro del estado de cuenta
class CuentaAnalisis(BaseModel):
    nombre_cuenta: Optional[str] = None
    numero_cuenta: Optional[str] = None
    moneda: Optional[str] = None
    saldo_anterior_resumen: Optional[float] = None
    saldo_actual_resumen: Optional[float] = None
    total_ingresos: float
    total_gastos: float
    transacciones: List[Transaccion]

# Modelo principal de la respuesta. Ahora contiene una lista de análisis de cuentas.
class AnalisisBanbajioPDF(BaseModel):
    nombre_archivo: str
    banco: str
    fecha_corte: Optional[str] = None
    periodo: Optional[str] = None
    cuentas: List[CuentaAnalisis]
