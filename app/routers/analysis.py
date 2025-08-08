import shutil
import os
import pdfplumber
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, List, Any
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime

# --- Imports de Módulos Propios ---
# Se importan los servicios que se van a utilizar.
from app.services.supabase_client import supabase
from app.core.config import SUPABASE_JWT_SECRET
from app.services import (
    document_identifier,
    pdf_processor_banorte,       # Para identificar el banco y tipo de cuenta.
    rate_limiter,              # Para el control de límites de uso (placeholders).
    pdf_processor_banamex_personal,    # Procesador para Banamex Personal.
    pdf_processor_banamex_empresarial, # Procesador para Banamex Empresarial.
    pdf_processor_banbajio,    # Procesador para BanBajio Empresarial.
    pdf_processor_bbva,         # Procesador para BBVA.
    pdf_processor_banorte,      # Procesador para Banorte.
    pdf_processor_scotiabank,   # Procesador para Scotiabank.

)

# --- Configuración del Router y Autenticación ---
router = APIRouter(prefix="/analysis", tags=["Analysis"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# --- Modelo Pydantic para la Respuesta del Historial ---
# Se usa en el endpoint get_analysis_history para validar la salida.
class HistoryItem(BaseModel):
    file_name: str
    created_at: datetime

# --- Función de Dependencia para Autenticación ---
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    Decodifica el token JWT de Supabase para obtener el usuario actual.
    Devuelve None si no se proporciona token, o lanza una excepción si el token es inválido.
    """
    if not token:
        return None
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"id": user_id}
    except JWTError:
        raise credentials_exception

# --- Endpoint Principal para Procesar PDF ---
# Nota: No se usa 'response_model' aquí porque la función puede devolver diferentes
# modelos de respuesta (uno por cada banco), lo que lo hace dinámico.
@router.post("/process-pdf")
async def process_pdf_endpoint(
    request: Request,
    archivo: UploadFile = File(...),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Endpoint principal que recibe un PDF, lo identifica y lo procesa
    según el banco y el tipo de cuenta.
    """
    # Lógica de rate limiting (sin cambios)
    if current_user:
        rate_limiter.check_registered_user_limit(current_user)
    else:
        rate_limiter.check_anonymous_limit(request)

    if archivo.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    ruta_temporal = f"temp_{archivo.filename}"
    try:
        with open(ruta_temporal, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)

        texto_completo = ""
        with pdfplumber.open(ruta_temporal) as pdf:
            if not pdf.pages:
                raise HTTPException(status_code=422, detail="El archivo PDF está vacío o corrupto.")
            
            # Se extrae el texto de TODAS las páginas para mayor robustez,
            # usando tolerancias que funcionan bien con PDFs complejos.
            texto_completo = "".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)

        if not texto_completo:
            raise HTTPException(status_code=422, detail="No se pudo leer el contenido del PDF o el archivo es ilegible.")

        # --- Flujo de Identificación y Procesamiento Jerárquico ---
        banco = document_identifier.identificar_banco(texto_completo)
        datos_analizados = None

        if banco == "banamex":
            tipo_cuenta = document_identifier.identificar_tipo_cuenta_banamex(texto_completo)
            if tipo_cuenta == "personal":
                datos_analizados = pdf_processor_banamex_personal.procesar_estado_de_cuenta(ruta_temporal)
            elif tipo_cuenta == "empresarial":
                datos_analizados = pdf_processor_banamex_empresarial.procesar_estado_de_cuenta_empresarial(ruta_temporal)
        
        elif banco == "banbajio":
            # Asumimos que solo hay un tipo de cuenta para BanBajío por ahora
            datos_analizados = pdf_processor_banbajio.procesar_estado_de_cuenta_banbajio_empresarial(ruta_temporal)

        # --- INICIO DE LA INTEGRACIÓN DE BBVA ---
        elif banco == "bbva":
            # Por ahora, solo tenemos un procesador para BBVA (Maestra Pyme)
            # No es necesario un identificador de tipo de cuenta adicional.
            datos_analizados = pdf_processor_bbva.procesar_estado_de_cuenta_bbva(ruta_temporal)
        # --- FIN DE LA INTEGRACIÓN DE BBVA ---

        # --- INICIO DE LA INTEGRACIÓN DE BANORTE ---
        elif banco == "banorte":
            # Por ahora, solo tenemos un procesador para Banorte (Preferente)
            # No es necesario un identificador de tipo de cuenta adicional.
            datos_analizados = pdf_processor_banorte.procesar_estado_de_cuenta_banorte(ruta_temporal)
        # --- FIN DE LA INTEGRACIÓN DE BANORTE ---
        # --- INICIO DE LA INTEGRACIÓN DE SCOTIABANK ---
        elif banco == "scotiabank":
            tipo_cuenta = document_identifier.identificar_tipo_cuenta_scotiabank(texto_completo)
            if tipo_cuenta == "pyme_pfae":
                datos_analizados = pdf_processor_scotiabank.procesar_estado_de_cuenta_scotiabank(ruta_temporal)
    # --- FIN DE LA INTEGRACIÓN DE SCOTIABANK ---


        if not datos_analizados:
            banco_str = f"'{banco.upper()}'" if banco else "desconocido"
            raise HTTPException(status_code=422, detail=f"El tipo de estado de cuenta del banco {banco_str} no es soportado o el archivo es ilegible.")

        if current_user:
            supabase.table("analysis_history").insert({
                "user_id": current_user['id'],
                "file_name": archivo.filename
            }).execute()
            
        return datos_analizados

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {str(e)}")
    finally:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

# --- Endpoint para Obtener el Historial de Análisis ---
@router.get("/history", response_model=List[HistoryItem])
async def get_analysis_history(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Obtiene los 5 análisis más recientes para el usuario autenticado.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    
    try:
        response = supabase.table("analysis_history").select("file_name, created_at").eq("user_id", current_user['id']).order("created_at", desc=True).limit(5).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el historial: {e}")