from pydantic import BaseModel
from typing import List, Optional

# Modelo para una transacción individual.
# Lo mantendremos consistente con los otros bancos.
class Transaccion(BaseModel):
    fecha: str
    descripcion: str
    retiro: float = 0.0
    deposito: float = 0.0
    saldo: Optional[float] = None
    tipo_movimiento: str
    categoria: str

# Modelo para el análisis de la cuenta BBVA.
class CuentaAnalisis(BaseModel):
    nombre_cuenta: Optional[str] = None
    numero_cuenta: Optional[str] = None
    moneda: Optional[str] = None
    saldo_anterior_resumen: Optional[float] = None
    saldo_actual_resumen: Optional[float] = None
    total_ingresos: float
    total_gastos: float
    transacciones: List[Transaccion]

# Modelo principal para la respuesta del análisis del PDF de BBVA.
class AnalisisBbvaPDF(BaseModel):
    nombre_archivo: str
    banco: str
    fecha_corte: Optional[str] = None
    periodo: Optional[str] = None
    cuentas: List[CuentaAnalisis]