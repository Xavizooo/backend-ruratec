"""
Verificación de documento por OCR.

IMPORTANTE — qué es y qué NO es esto:
Este módulo NO verifica identidad real (no consulta la Registraduría ni
ninguna base de datos oficial). Solo lee el texto impreso en la foto de
la cédula que sube el usuario (vía OCR.space) y confirma que ese texto
sea consistente con lo que el usuario escribió en el formulario de
registro. Sirve como filtro básico y como fricción disuasoria, no como
prueba legal de identidad.

Necesitás una API key gratuita de https://ocr.space/ocrapi (no pide
tarjeta para el tier gratis, ~25.000 requests/mes). Pegala abajo o,
mejor, cargala como variable de entorno en Render/Railway y leela con
os.environ.get(...).
"""

import os
import re
import unicodedata
import difflib
import requests

OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "K81773589288957")
OCR_SPACE_URL = "https://api.ocr.space/parse/imageurl"


def _normalizar(texto):
    """Quita tildes, pasa a mayúsculas y deja solo letras/números/espacios."""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    texto = texto.upper()
    texto = re.sub(r'[^A-Z0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


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
    Compara el texto leído en la foto contra los datos del formulario.
    Devuelve (validado: bool, texto_crudo: str).

    Criterios (con tolerancia, porque el OCR nunca es 100% exacto):
      1) El número de cédula (sin puntos ni espacios) debe aparecer
         literalmente en el texto leído.
      2) Casi todas las palabras del nombre completo deben tener una
         coincidencia cercana (fuzzy) en el texto leído.
    """
    texto_crudo = extraer_texto_cedula(url_imagen)
    if not texto_crudo:
        return False, ""

    texto_normalizado = _normalizar(texto_crudo)
    texto_solo_digitos = re.sub(r'\D', '', texto_normalizado)

    numero_limpio = re.sub(r'\D', '', numero_cedula or "")
    numero_encontrado = bool(numero_limpio) and numero_limpio in texto_solo_digitos

    nombre_normalizado = _normalizar(f"{nombre} {apellido}")
    palabras_nombre = [p for p in nombre_normalizado.split() if len(p) >= 3]
    palabras_texto = texto_normalizado.split()

    coincidencias = sum(
        1 for palabra in palabras_nombre
        if difflib.get_close_matches(palabra, palabras_texto, n=1, cutoff=0.8)
    )
    # Toleramos que falte como máximo 1 palabra (ej: un segundo nombre
    # que el OCR no captó bien), pero no más que eso.
    nombre_coincide = bool(palabras_nombre) and coincidencias >= max(1, len(palabras_nombre) - 1)

    validado = numero_encontrado and nombre_coincide
    return validado, texto_crudo