import requests

def enviar_notificacion(push_token, titulo, mensaje, data={}):
    if not push_token:
        return
    
    try:
        requests.post(
            "https://exp.host/--/api/v2/push/send",
            json={
                "to": push_token,
                "title": titulo,
                "body": mensaje,
                "data": data,
                "sound": "default",
                "priority": "high",
            },
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        print(f"Error enviando notificación: {e}")