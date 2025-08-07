from supabase import create_client, AsyncClient
from app.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

# Creamos el cliente de Supabase
supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)