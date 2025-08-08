# Archivo: app/schemas/analysisScotiabank.py

from pydantic import BaseModel
from typing import List, Optional

class Transaccion(BaseModel):
    fecha: str
    descripcion: str = ""  # Campo para consistencia con otros bancos
    concepto: str = ""     # Campo específico de Scotiabank
    deposito: float = 0.0
    retiro: float = 0.0
    saldo: float = 0.0
    
    def __init__(self, **data):
        # Si se pasa concepto pero no descripcion, usar concepto como descripcion
        if 'concepto' in data and 'descripcion' not in data:
            data['descripcion'] = data['concepto']
        elif 'descripcion' in data and 'concepto' not in data:
            data['concepto'] = data['descripcion']
        super().__init__(**data)

class CuentaAnalisis(BaseModel):
    numero_cuenta: Optional[str] = None
    nombre_cuenta: str = "CUENTA UNICA PYME"  # Nombre por defecto para Scotiabank
    moneda: str = "PESOS"
    saldo_inicial: float = 0.0
    saldo_anterior_resumen: float = 0.0  # Alias para saldo_inicial
    depositos: float = 0.0
    total_ingresos: float = 0.0  # Alias para depositos
    retiros: float = 0.0
    total_gastos: float = 0.0    # Alias para retiros
    saldo_final: float = 0.0
    saldo_actual_resumen: float = 0.0  # Alias para saldo_final
    transacciones: List[Transaccion] = []
    
    def __init__(self, **data):
        # Establecer alias automáticamente
        if 'saldo_inicial' in data:
            data['saldo_anterior_resumen'] = data['saldo_inicial']
        if 'depositos' in data:
            data['total_ingresos'] = data['depositos']
        if 'retiros' in data:
            data['total_gastos'] = data['retiros']
        if 'saldo_final' in data:
            data['saldo_actual_resumen'] = data['saldo_final']
        super().__init__(**data)

class AnalisisScotiabankPDF(BaseModel):
    nombre_archivo: str
    banco: str = "Scotiabank"
    periodo: str
    fecha_corte: Optional[str] = None
    cuenta_clabe: str
    cuentas: List[CuentaAnalisis] = []