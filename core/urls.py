from django.urls import path
from .views import (
    CustomAuthToken, registrar_usuario,
    crear_publicacion, listar_publicaciones, detalle_publicacion,
    registrar_visita, ver_visitas,
    crear_negociacion, confirmar_pago,
    perfil_usuario, guardar_push_token,
    listar_favoritos, agregar_favorito, eliminar_favorito
)

urlpatterns = [
    path('login/', CustomAuthToken.as_view(), name='api_login'),
    path('usuarios/', registrar_usuario, name='registro'),
    path('perfil/', perfil_usuario, name='perfil'),
    path('push-token/', guardar_push_token, name='guardar_push_token'),
    path('publicaciones/', listar_publicaciones, name='listar_publicaciones'),
    path('publicaciones/crear/', crear_publicacion, name='crear_publicacion'),
    path('publicaciones/<int:pk>/', detalle_publicacion, name='detalle_publicacion'),
    path('publicaciones/<int:pk>/visita/', registrar_visita, name='registrar_visita'),
    path('publicaciones/<int:pk>/visitas/', ver_visitas, name='ver_visitas'),
    path('publicaciones/<int:pk>/negociar/', crear_negociacion, name='crear_negociacion'),
    path('negociaciones/<int:pk>/confirmar/', confirmar_pago, name='confirmar_pago'),
    path('favoritos/', listar_favoritos, name='listar_favoritos'),
    path('publicaciones/<int:pk>/favorito/', agregar_favorito, name='agregar_favorito'),
    path('favoritos/<int:pk>/eliminar/', eliminar_favorito, name='eliminar_favorito'),
]