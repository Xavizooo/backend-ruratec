"""
Verificación de documento por OCR.

IMPORTANTE — qué es y qué NO es esto:
Este módulo NO verifica identidad real (no consulta la Registraduría ni
ninguna base de datos oficial). Solo lee el texto impreso en la foto de
la cédula que sube el usuario (vía OCR.space) y confirma que el número
de cédula que escribió en el formulario aparezca en esa foto. Sirve como
filtro básico y como fricción disuasoria, no como prueba legal de
identidad.

✅ SIMPLIFICADO: ya no se compara el nombre/apellido contra el texto del
documento (esa comparación era muy sensible a errores de OCR — nombres
compuestos, tildes mal leídas, orden de nombres, etc. — y generaba
muchos falsos negativos). Ahora el único criterio es que el número de
cédula ingresado aparezca literalmente en el texto leído de la foto.

Necesitás una API key gratuita de https://ocr.space/ocrapi (no pide
tarjeta para el tier gratis, ~25.000 requests/mes). Pegala abajo o,
mejor, cargala como variable de entorno en Render/Railway y leela con
os.environ.get(...).
"""

import os
import re
import requests

OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "K81773589288957")
OCR_SPACE_URL = "https://api.ocr.space/parse/imageurl"


def extraer_texto_cedula(url_imagen):
    """
    Le pasa a OCR.space la URL pública de la imagen (la de Cloudinary,
    por ejemplo) y devuelve el texto crudo detectado, o None si falla
    o no logra leer nada.
    """
    try:
        response = requests.get(
            OCR_SPACE_URL,
            params={
                "apikey": OCR_SPACE_API_KEY,
                "url": url_imagen,
                "language": "spa",
                "OCREngine": 2,
                "scale": "true",
            },
            timeout=20,
        )
        data = response.json()
        if data.get("IsErroredOnProcessing"):
            return None
        resultados = data.get("ParsedResults") or []
        if not resultados:
            return None
        return resultados[0].get("ParsedText", "")
    except Exception:
        return None


def validar_documento(numero_cedula, nombre, apellido, url_imagen):
    """
    Compara el número de cédula del formulario contra el texto leído
    en la foto. Devuelve (validado: bool, texto_crudo: str).

    nombre y apellido se mantienen en la firma por compatibilidad con
    la vista que ya los pasa, pero ya NO se usan en la validación.

    Criterio único: el número de cédula (sin puntos, espacios ni
    guiones) debe aparecer literalmente entre los dígitos detectados
    en el texto de la foto.
    """
    texto_crudo = extraer_texto_cedula(url_imagen)
    if not texto_crudo:
        return False, ""

    texto_solo_digitos = re.sub(r'\D', '', texto_crudo)
    numero_limpio = re.sub(r'\D', '', numero_cedula or "")

    validado = bool(numero_limpio) and numero_limpio in texto_solo_digitos

    return validado, texto_crudo