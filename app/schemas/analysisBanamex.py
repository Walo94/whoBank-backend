from pydantic import BaseModel
from typing import List, Optional

# --- MODELO PARA EL RESUMEN DEL PERIODO ---
class ResumenPeriodo(BaseModel):
    periodo: str
    depositos_conteo: int
    depositos_total: float
    retiros_conteo: int
    retiros_total: float

# Define cómo se ve una transacción
class Transaccion(BaseModel):
    fecha: str
    descripcion: str
    retiro: float = 0.0
    deposito: float = 0.0
    saldo: Optional[float] = None
    tipo_movimiento: str # "gasto", "ingreso" o "informativo"
    categoria: str # ej. "Transferencia", "Pago de Servicios", etc.

# Modelo para el análisis de UNA SOLA cuenta
class CuentaAnalisis(BaseModel):
    nombre_cuenta: Optional[str] = None
    numero_cuenta: Optional[str] = None
    moneda: Optional[str] = "PESOS" # Para Banamex, será Moneda Nacional
    saldo_anterior_resumen: Optional[float] = None
    saldo_actual_resumen: Optional[float] = None
    total_ingresos: float
    total_gastos: float
    transacciones: List[Transaccion]

# Define el resumen por cada medio de acceso
class MedioDeAcceso(BaseModel):
    medio: str
    retiros: float
    depositos: float

# Define cómo se verá la respuesta completa de la API
class AnalisisPDF(BaseModel):
    nombre_archivo: str
    banco: str
    resumen_periodo: Optional[ResumenPeriodo]
    total_ingresos: float
    total_gastos: float
    resumen_medios: List[MedioDeAcceso]
    transacciones: List[Transaccion]
    fecha_corte: Optional[str] = None
    cuentas: List[CuentaAnalisis]