import requests
from xml.etree import ElementTree as ET
from django.core.cache import cache

WSDL_URL = "http://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"

PRODUCTOS_CANASTA = [
    ("Arroz", "arroz"),
    ("Papa pastusa", "papa"),
    ("Huevo rojo A", "huevo"),
    ("Leche pasteurizada", "leche"),
    ("Plátano hartón", "platano"),
    ("Zanahoria", "zanahoria"),
    ("Cebolla cabezona", "cebolla"),
    ("Tomate chonto", "tomate"),
    ("Pollo entero", "pollo"),
    ("Aceite vegetal", "aceite"),
]

def consultar_precio_sipsa(producto: str) -> dict:
    """Consulta precio mayorista de un producto en Corabastos (Bogotá)."""
    cache_key = f"sipsa_{producto}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                    xmlns:srv="http://sipsa.service.dane.gov.co/">
        <soapenv:Header/>
        <soapenv:Body>
            <srv:getPreciosMayoristas>
                <producto>{producto}</producto>
                <mercado>Bogotá - Corabastos</mercado>
                <periodo>semanal</periodo>
            </srv:getPreciosMayoristas>
        </soapenv:Body>
    </soapenv:Envelope>"""

    try:
        response = requests.post(
            WSDL_URL,
            data=soap_body,
            headers={"Content-Type": "text/xml", "SOAPAction": "getPreciosMayoristas"},
            timeout=8,
        )
        root = ET.fromstring(response.content)
        ns = {"ns": "http://sipsa.service.dane.gov.co/"}
        precio = root.find(".//ns:precio", ns)
        fecha = root.find(".//ns:fecha", ns)

        result = {
            "producto": producto,
            "precio": float(precio.text) if precio is not None else None,
            "fecha": fecha.text if fecha is not None else None,
            "unidad": "kg",
            "fuente": "SIPSA-DANE",
        }
        cache.set(cache_key, result, timeout=3600 * 6)  # cache 6 horas
        return result
    except Exception:
        return {"producto": producto, "precio": None, "error": "No disponible"}