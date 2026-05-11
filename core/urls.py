from django.urls import path
from .views import (
    CustomAuthToken, registrar_usuario,
    crear_publicacion, listar_publicaciones, detalle_publicacion,
    registrar_visita, ver_visitas,
    crear_negociacion, confirmar_pago
)

urlpatterns = [
    path('login/', CustomAuthToken.as_view(), name='api_login'),
    path('usuarios/', registrar_usuario, name='registro'),
    path('publicaciones/', listar_publicaciones, name='listar_publicaciones'),
    path('publicaciones/crear/', crear_publicacion, name='crear_publicacion'),
    path('publicaciones/<int:pk>/', detalle_publicacion, name='detalle_publicacion'),
    path('publicaciones/<int:pk>/visita/', registrar_visita, name='registrar_visita'),
    path('publicaciones/<int:pk>/visitas/', ver_visitas, name='ver_visitas'),
    path('publicaciones/<int:pk>/negociar/', crear_negociacion, name='crear_negociacion'),
    path('negociaciones/<int:pk>/confirmar/', confirmar_pago, name='confirmar_pago'),
]