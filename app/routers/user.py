from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from pydantic import BaseModel
from datetime import datetime

from app.services.supabase_client import supabase
from app.routers.analysis import get_current_user

router = APIRouter(
    prefix="/user",
    tags=["User"]
)

# --- Modelos de Respuesta para el Panel ---
class ProfileData(BaseModel):
    plan: str
    tokens_disponibles: int

class HistoryItem(BaseModel):
    file_name: str
    created_at: datetime

class UserPanelResponse(BaseModel):
    profile: ProfileData
    history: List[HistoryItem]

@router.get("/panel-data", response_model=UserPanelResponse)
async def get_user_panel_data(current_user: Dict = Depends(get_current_user)):
    """
    Endpoint único para obtener todos los datos necesarios para el panel de usuario.
    Combina la información del perfil y el historial de análisis.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Autenticación requerida")

    user_id = current_user['id']

    try:
        # 1. Obtener los datos del perfil del usuario
        profile_res = supabase.table("profiles").select("plan_activo, daily_conversions_count").eq("id", user_id).single().execute()
        
        if not profile_res.data:
            raise HTTPException(status_code=404, detail="Perfil de usuario no encontrado.")
            
        profile_data = profile_res.data
        tokens_disponibles = 3 - profile_data.get("daily_conversions_count", 0)
        
        profile_info = ProfileData(
            plan=profile_data.get("plan_activo", "gratis").strip().replace("'", ""),
            tokens_disponibles=tokens_disponibles
        )

        # 2. Obtener el historial de análisis
        history_res = supabase.table("analysis_history").select("file_name, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
        
        history_list = [HistoryItem(**item) for item in history_res.data]

        # 3. Devolver todo en una única respuesta
        return UserPanelResponse(profile=profile_info, history=history_list)

    except HTTPException as e:
        # Re-lanzar excepciones HTTP para que FastAPI las maneje
        raise e
    except Exception as e:
        print(f"Error inesperado en get_user_panel_data: {e}")
        raise HTTPException(status_code=500, detail="Error interno al obtener los datos del panel.")
