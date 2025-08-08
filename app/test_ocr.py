# test_ocr.py
from pdf2image import convert_from_path
import pytesseract
import os

# MUY IMPORTANTE: Reemplaza esta ruta con la ubicación real de tu PDF de Santander.
# Ejemplo en Windows: 'C:\\Users\\TuUsuario\\Desktop\\Estado Cuenta Santander.pdf'
# Ejemplo en macOS/Linux: '/Users/tu_usuario/Desktop/Estado Cuenta Santander.pdf'
ruta_al_pdf = "C:\\Users\\SISTEMAS\\Desktop\\Santander.pdf"

print("--- Iniciando prueba de OCR ---")

if not os.path.exists(ruta_al_pdf):
    print(f"ERROR: El archivo no se encontró en '{ruta_al_pdf}'. Por favor, verifica la ruta.")
else:
    try:
        print("Paso 1: Convirtiendo PDF a imágenes con pdf2image...")
        # Si esto falla, el problema es con 'poppler'.
        imagenes = convert_from_path(ruta_al_pdf)
        print(f"Paso 1 Exitoso: Se generaron {len(imagenes)} imágenes.")

        print("\nPaso 2: Aplicando OCR a la primera imagen con Tesseract...")
        # Si esto falla, el problema es con 'Tesseract' o los archivos de idioma.
        texto = pytesseract.image_to_string(imagenes[0], lang='spa')
        print("Paso 2 Exitoso: Tesseract funcionó.")

        print("\n--- ¡Prueba completada exitosamente! ---")
        print("Texto extraído de la primera página:")
        print("-----------------------------------------")
        print(texto)
        print("-----------------------------------------")

    except Exception as e:
        print("\n--- !!! OCURRIÓ UN ERROR DURANTE LA PRUEBA !!! ---")
        print("El error fue:")
        print(e)
        print("\n--- SUGERENCIAS ---")
        print("-> Si el error menciona 'poppler' o 'pdftoppm', necesitas instalar o configurar Poppler.")
        print("-> Si el error menciona 'tesseract' o 'is not installed or it's not in your PATH', necesitas instalar Tesseract o añadirlo al PATH.")
        print("-> Si el error menciona 'Failed loading language', te falta el paquete de idioma 'spa'.")