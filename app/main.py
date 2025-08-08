# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, analysis  # Importa los routers
from app.routers import contact

# --- Creación de la Instancia de FastAPI ---
app = FastAPI(
    title="WhoBank API",
    description="API para analizar estados de cuenta bancarios.",
    version="1.0.0"
)

# --- Configuración de CORS ---
# Define los orígenes permitidos para las peticiones del frontend
origins = [
    "http://192.168.70.108:8080", # URL de desarrollo de Vite/React
    "http://localhost:8080", # URL común de desarrollo de React
    "https://converter-bank.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todas las cabeceras
)

# --- Inclusión de los Routers ---
# Aquí se conectan los endpoints definidos en otros archivos a la app principal.
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(contact.router)

# --- Endpoint Raíz ---
@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint principal que da la bienvenida a la API.
    """
    return {"message": "Bienvenido a WhoBank API"}