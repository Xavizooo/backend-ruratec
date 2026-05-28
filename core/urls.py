from django.urls import path
from .views import (
    CustomAuthToken, registrar_usuario,
    crear_publicacion, listar_publicaciones, detalle_publicacion,
    registrar_visita, ver_visitas,
    crear_negociacion, confirmar_pago, negociacion_pendiente, cancelar_negociacion,
    perfil_usuario, guardar_push_token,
    listar_favoritos, agregar_favorito, eliminar_favorito,
    canasta_familiar,
    editar_publicacion, eliminar_publicacion,
    listar_notificaciones, marcar_leida, marcar_todas_leidas,
    responder_negociacion, negociaciones_agricultor,
    estado_negociacion, cancelar_negociacion)
)

urlpatterns = [
    path('login/', CustomAuthToken.as_view(), name='api_login'),
    path('usuarios/', registrar_usuario, name='registro'),
    path('perfil/', perfil_usuario, name='perfil'),
    path('push-token/', guardar_push_token, name='guardar_push_token'),
    path('canasta/', canasta_familiar, name='canasta-familiar'),
    path('publicaciones/', listar_publicaciones, name='listar_publicaciones'),
    path('publicaciones/crear/', crear_publicacion, name='crear_publicacion'),
    path('publicaciones/<int:pk>/', detalle_publicacion, name='detalle_publicacion'),
    path('publicaciones/<int:pk>/visita/', registrar_visita, name='registrar_visita'),
    path('publicaciones/<int:pk>/visitas/', ver_visitas, name='ver_visitas'),
    path('publicaciones/<int:pk>/negociar/', crear_negociacion, name='crear_negociacion'),
    path('publicaciones/<int:pk>/favorito/', agregar_favorito, name='agregar_favorito'),
    path('publicaciones/<int:pk>/editar/', editar_publicacion, name='editar_publicacion'),
    path('publicaciones/<int:pk>/eliminar/', eliminar_publicacion, name='eliminar_publicacion'),
    path('negociaciones/pendiente/', negociacion_pendiente, name='negociacion_pendiente'),  # ✅ NUEVO
    path('negociaciones/<int:pk>/confirmar/', confirmar_pago, name='confirmar_pago'),
    path('negociaciones/<int:pk>/cancelar/', cancelar_negociacion, name='cancelar_negociacion'),  # ✅ NUEVO
    path('negociaciones/<int:pk>/responder/', responder_negociacion, name='responder_negociacion'),
    path('negociaciones/agricultor/', negociaciones_agricultor, name='negociaciones_agricultor'),
    path('favoritos/', listar_favoritos, name='listar_favoritos'),
    path('favoritos/<int:pk>/eliminar/', eliminar_favorito, name='eliminar_favorito'),
    path('notificaciones/', listar_notificaciones, name='listar_notificaciones'),
    path('notificaciones/<int:pk>/leer/', marcar_leida, name='marcar_leida'),
    path('notificaciones/leer-todas/', marcar_todas_leidas, name='marcar_todas_leidas'),
    path('negociaciones/<int:pk>/estado/', estado_negociacion, name='estado_negociacion'),
    path('negociaciones/<int:pk>/cancelar/', cancelar_negociacion, name='cancelar_negociacion'),
]