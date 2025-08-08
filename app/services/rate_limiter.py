# app/services/rate_limiter.py
from fastapi import Request, HTTPException
from datetime import datetime, timedelta, timezone
from app.services.supabase_client import supabase
from typing import Dict

# --- Para usuarios anónimos (en memoria) ---
anonymous_usage: dict[str, datetime] = {}

def check_anonymous_limit(request: Request):
    """
    Verifica si una IP ha excedido el límite de 3 conversiónes cada 24 horas.
    """
    ip = request.client.host
    if not ip:
        raise HTTPException(status_code=400, detail="No se pudo determinar la dirección IP")
    
    last_usage = anonymous_usage.get(ip)

    if last_usage:
        if datetime.now(timezone.utc) - last_usage < timedelta(hours=24):
            raise HTTPException(
                status_code=429, 
                detail={
                    "message": "Límite anónimo de 3 conversiónes cada 24 horas excedido.",
                    "cooldown": "Vuelve mañana o regístrate para más conversiones."
                }
            )

    anonymous_usage[ip] = datetime.now(timezone.utc)

# --- Lógica para Usuarios Registrados (Corregida a Síncrona) ---
def check_registered_user_limit(user: Dict): # CAMBIO: de 'async def' a 'def'
    """
    Verifica y actualiza el contador de conversiones diarias para un usuario registrado.
    """
    user_id = user['id']
    try:
        # CAMBIO: Se elimina 'await' y se vuelve a usar .single() que es síncrono
        profile_res = supabase.table("profiles").select("last_conversion_at, daily_conversions_count").eq("id", user_id).single().execute()
        profile = profile_res.data
        
        # ... la lógica interna no cambia ...
        last_conversion_str = profile.get("last_conversion_at")
        daily_count = profile.get("daily_conversions_count", 0)
        
        if last_conversion_str:
            last_conversion_dt = datetime.fromisoformat(last_conversion_str)
            if datetime.now(timezone.utc) - last_conversion_dt > timedelta(hours=24):
                daily_count = 0

        if daily_count >= profile.get("conversions_tokens", 7):

            raise HTTPException(status_code=429, detail="Límite de 7 conversiones diarias excedido. Vuelve mañana o suscríbete para más.")

        # CAMBIO: Se elimina 'await'
        supabase.table("profiles").update({
            "daily_conversions_count": daily_count + 1,
            "last_conversion_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()

    except HTTPException as e:
        raise e
    except Exception as e:
        # El error "PostgrestAPIError: {'code': 'PGRST116', ...}" ocurre si .single() no encuentra nada.
        # Esto significa que el perfil no existe.
        if "PGRST116" in str(e):
             raise HTTPException(status_code=404, detail=f"Crítico: No se encontró un perfil para el usuario ID: {user_id}")
        print(f"Error inesperado en check_registered_user_limit: {e}")
        raise HTTPException(status_code=500, detail=f"Error al gestionar el límite de usuario: {e}")