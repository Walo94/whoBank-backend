from fastapi import APIRouter, HTTPException
from app.schemas.user import UserCreate, UserLogin
from app.services.supabase_client import supabase
from gotrue.errors import AuthApiError

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register")
async def create_user(user_credentials: UserCreate):
    """Crea un nuevo usuario en Supabase Auth."""
    try:
        session = await supabase.auth.sign_up({
            "email": user_credentials.email,
            "password": user_credentials.password,
        })
        # El trigger que creamos en la DB se encargará de crear el perfil.
        return {"message": "Usuario creado exitosamente. Revisa tu correo para la confirmación.", "user_id": session.user.id}
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login_user(user_credentials: UserLogin):
    """Inicia sesión y devuelve un token de acceso."""
    try:
        session = await supabase.auth.sign_in_with_password({
            "email": user_credentials.email,
            "password": user_credentials.password
        })
        return {
            "message": "Inicio de sesión exitoso.",
            "access_token": session.session.access_token,
            "user": {
                "id": session.user.id,
                "email": session.user.email,
            }
        }
    except AuthApiError as e:
        raise HTTPException(status_code=401, detail=f"Credenciales inválidas: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))