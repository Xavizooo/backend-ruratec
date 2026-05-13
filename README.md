# 🌱 RURATEC — Backend

> API REST que conecta directamente a **agricultores con comerciantes**, eliminando intermediarios en la cadena de suministro agrícola.

---

## 📋 Descripción

Motor lógico de la plataforma Ruratec. Se encarga de la gestión de identidades (agricultores y comerciantes), el ciclo de vida de los productos agrícolas, la generación de enlaces de contacto directo vía **WhatsApp** y la lógica financiera para el procesamiento de pagos, incluyendo el cálculo automático de la **comisión del 4%** por transacción.

---

## 👥 Integrantes

| Nombre |
|---|
| Luis Danilo Martinez Cañon |
| Andres Felipe Diaz Barbosa |
| Hector Ivan Amado Betancur |
| Javier Andres Torres Sanchez |
| Juan David Ducuara Santa |

---

## 🛠️ Tecnologías utilizadas

- **Lenguaje:** Python 3.x
- **Framework:** Django / Django REST Framework (DRF)
- **Base de datos:** PostgreSQL (Producción) / SQLite (Desarrollo)
- **Librerías principales:**
  - **Simple JWT** — Autenticación segura basada en tokens
  - **CORS Headers** — Conexión con el frontend
  - **WhatsApp API Integration** — Comunicación entre usuarios

---

## ✅ Requisitos previos

- **Python** `>= 3.10`
- **pip** (gestor de paquetes de Python)
- **PostgreSQL** instalado y configurado
- Herramienta para entornos virtuales (`venv`)

---

## 🚀 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Xavizooo/backend-ruratec.git
   cd backend-ruratec
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Ejecución local

1. **Preparar la base de datos:**
   ```bash
   python manage.py migrate
   ```

2. **Iniciar el servidor:**
   ```bash
   python manage.py runserver
   ```

La API será accesible en: [http://localhost:8000/api](http://localhost:8000/api)

---

## 🗄️ Base de datos

El sistema está configurado para usar **PostgreSQL**. Debes crear una base de datos llamada `ruratec_db` y configurar las credenciales en el archivo `.env`.

> Para pruebas rápidas sin configurar Postgres, puedes usar SQLite modificando el `settings.py`.

---

## 🔐 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con los siguientes parámetros:

```env
SECRET_KEY=tu_clave_secreta
DEBUG=True
DATABASE_URL=postgresql://usuario:password@localhost:5432/ruratec_db
JWT_SECRET_KEY=tu_jwt_secret
COMMISSION_RATE=0.04
WHATSAPP_BASE_URL=https://wa.me/
```

---

## 👤 Usuario de prueba

1. **Crear superusuario:**
   ```bash
   python manage.py createsuperuser
   ```

2. **Acceso al panel admin:** [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 📦 Despliegue

El backend está diseñado para desplegarse en plataformas como **Render**, **Railway** o **Heroku**.

- Cambia `DEBUG=False` en producción
- Configura `ALLOWED_HOSTS` con el dominio de producción

---

## 📌 Evidencias

- ✅ **Endpoints de Auth** — Registro y Login con JWT funcionando
- ✅ **CRUD de Productos** — Gestión completa de inventario agrícola
- ✅ **Módulo de Pagos** — Cálculo y registro de transacciones con comisión del 4%

---

## 🔗 Repositorio Frontend

[https://github.com/Xavizooo/frontend-proyecto](https://github.com/Xavizooo/frontend-proyecto)
