# app/routers/contact.py

import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Cargar las variables de entorno del archivo .env
load_dotenv()

router = APIRouter(
    prefix="/contact",
    tags=["Contact"]
)

# Pydantic model para validar los datos de entrada
class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

@router.post("/", status_code=status.HTTP_200_OK)
async def send_contact_email(request: ContactRequest):
    """
    Recibe los datos de un formulario de contacto y envía un correo usando SendGrid.
    """

    # --- INICIO DEL CÓDIGO DE DEPURACIÓN ---
    # ¡AÑADE ESTAS LÍNEAS PARA VERIFICAR LAS VARIABLES!
    print("--- INICIANDO DEPURACIÓN DE ENVÍO DE CORREO ---")
    api_key = os.getenv('SENDGRID_API_KEY')
    sender = os.getenv("SENDER_EMAIL")
    recipient = os.getenv("RECIPIENT_EMAIL")

    # Imprimimos de forma segura solo una parte de la API Key para verificarla
    print(f"API Key Encontrada: {api_key[:5]}...{api_key[-4:] if api_key else '¡NO ENCONTRADA!'}")
    print(f"Email Remitente: {sender}")
    print(f"Email Destinatario: {recipient}")
    print("---------------------------------------------")
    # --- FIN DEL CÓDIGO DE DEPURACIÓN ---

    # Construir el correo electrónico
    message = Mail(
        from_email=os.getenv("SENDER_EMAIL"),
        to_emails=os.getenv("RECIPIENT_EMAIL"),
        subject=f"Nuevo mensaje de contacto de: {request.name}",
        html_content=f"""
            <h3>Has recibido un nuevo mensaje de contacto:</h3>
            <p><strong>Nombre:</strong> {request.name}</p>
            <p><strong>Correo Electrónico:</strong> {request.email}</p>
            <hr>
            <p><strong>Mensaje:</strong></p>
            <p>{request.message}</p>
        """
    )

    try:
        # Enviar el correo
        sendgrid_client = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sendgrid_client.send(message)

        # Puedes verificar el código de estado si lo deseas
        if response.status_code >= 200 and response.status_code < 300:
            return {"message": "Correo enviado exitosamente."}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Hubo un error al enviar el correo."
            )

    except Exception as e:
        print(f"Error al enviar correo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el servidor: {e}"
        )