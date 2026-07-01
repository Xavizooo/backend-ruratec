from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.utils import timezone
from datetime import timedelta
import uuid
import requests

from .serializers import (
    UserSerializer, PublicacionSerializer, VisitaSerializer,
    NegociacionSerializer, FavoritoSerializer, NotificacionSerializer
)
from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion, Favorito, Notificacion
from .notificaciones import enviar_notificacion


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@api_view(['POST'])
def registrar_usuario(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Usuario creado correctamente"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        perfil = Perfil.objects.filter(user=user).first()
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'nombre': user.first_name if user.first_name else user.username,
            'rol': perfil.rol if perfil else "No definido",
            'ubicacion': perfil.ubicacion if perfil else "No definida"
        })


# ─────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────

@api_view(['GET', 'PUT'])
def perfil_usuario(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    user = request.user
    perfil = Perfil.objects.filter(user=user).first()

    if request.method == 'GET':
        return Response({
            'id': user.pk,
            'nombre': user.first_name,
            'apellido': user.last_name,
            'email': user.email,
            'telefono': perfil.telefono if perfil else None,
            'rol': perfil.rol if perfil else None,
            'ubicacion': perfil.ubicacion if perfil else None,
            'foto': request.build_absolute_uri(perfil.foto.url) if perfil and perfil.foto else None,
        })

    if request.method == 'PUT':
        user.first_name = request.data.get('nombre', user.first_name)
        user.last_name = request.data.get('apellido', user.last_name)
        user.save()
        if perfil:
            perfil.telefono = request.data.get('telefono', perfil.telefono)
            perfil.ubicacion = request.data.get('ubicacion', perfil.ubicacion)
            if 'foto' in request.FILES:
                perfil.foto = request.FILES['foto']
            perfil.save()
        return Response({"message": "Perfil actualizado correctamente"})


@api_view(['POST'])
def guardar_push_token(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    token = request.data.get('push_token')
    if not token:
        return Response({"error": "Token requerido"}, status=status.HTTP_400_BAD_REQUEST)
    perfil = Perfil.objects.filter(user=request.user).first()
    if perfil:
        perfil.push_token = token
        perfil.save()
    return Response({"message": "Token guardado"})


# ─────────────────────────────────────────────
# PUBLICACIONES
# ─────────────────────────────────────────────

@api_view(['POST'])
def crear_publicacion(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = PublicacionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(vendedor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def listar_publicaciones(request):
    publicaciones = Publicacion.objects.all().order_by('-creado_en')
    serializer = PublicacionSerializer(publicaciones, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def detalle_publicacion(request, pk):
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    serializer = PublicacionSerializer(publicacion, context={'request': request})
    return Response(serializer.data)


@api_view(['PUT'])
def editar_publicacion(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk, vendedor=request.user)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    if timezone.now() > publicacion.creado_en + timedelta(hours=24):
        return Response({"error": "Ya no puedes editar esta publicación, han pasado más de 24 horas"}, status=status.HTTP_403_FORBIDDEN)
    tiene_ventas = Negociacion.objects.filter(publicacion=publicacion, estado='pagado').exists()
    if tiene_ventas:
        return Response({"error": "No puedes editar esta publicación porque ya tiene ventas"}, status=status.HTTP_403_FORBIDDEN)
    serializer = PublicacionSerializer(publicacion, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def eliminar_publicacion(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk, vendedor=request.user)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    if timezone.now() > publicacion.creado_en + timedelta(hours=24):
        return Response({"error": "Ya no puedes eliminar esta publicación, han pasado más de 24 horas"}, status=status.HTTP_403_FORBIDDEN)
    tiene_ventas = Negociacion.objects.filter(publicacion=publicacion, estado='pagado').exists()
    if tiene_ventas:
        return Response({"error": "No puedes eliminar esta publicación porque ya tiene ventas"}, status=status.HTTP_403_FORBIDDEN)
    publicacion.delete()
    return Response({"message": "Publicación eliminada"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# VISITAS
# ─────────────────────────────────────────────

@api_view(['POST'])
def registrar_visita(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    if publicacion.vendedor == request.user:
        return Response({"message": "Es tu propia publicación"})
    VisitaPublicacion.objects.get_or_create(publicacion=publicacion, comerciante=request.user)
    return Response({"message": "Visita registrada"})


@api_view(['GET'])
def ver_visitas(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    if publicacion.vendedor != request.user:
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    visitas = VisitaPublicacion.objects.filter(publicacion=publicacion)
    serializer = VisitaSerializer(visitas, many=True, context={'request': request})
    return Response(serializer.data)


# ─────────────────────────────────────────────
# NEGOCIACIONES
# ─────────────────────────────────────────────

@api_view(['POST'])
def crear_negociacion(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)

    negociacion_existente = Negociacion.objects.filter(
        comerciante=request.user,
        publicacion=publicacion,
        estado='pendiente_agricultor'
    ).first()
    if negociacion_existente:
        serializer = NegociacionSerializer(negociacion_existente)
        return Response(serializer.data, status=status.HTTP_200_OK)

    cantidad = request.data.get('cantidad')
    if not cantidad:
        return Response({"error": "Cantidad requerida"}, status=status.HTTP_400_BAD_REQUEST)

    total = float(cantidad) * publicacion.precio
    referencia = f"RURATEC-{uuid.uuid4().hex[:10].upper()}"

    negociacion = Negociacion.objects.create(
        publicacion=publicacion,
        comerciante=request.user,
        cantidad=cantidad,
        total=total,
        referencia=referencia,
        estado='pendiente_agricultor',
    )

    Notificacion.objects.create(
        usuario=publicacion.vendedor,
        tipo='negociacion',
        titulo='Nueva negociación',
        mensaje=f'{request.user.first_name} quiere comprar {cantidad} {publicacion.unidad} de {publicacion.producto} por ${total:,.0f}.',
        negociacion=negociacion,
    )

    serializer = NegociacionSerializer(negociacion)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def estado_negociacion(request, pk):
    """Polling: el comerciante consulta el estado de su negociación."""
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        negociacion = Negociacion.objects.get(pk=pk, comerciante=request.user)
    except Negociacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    serializer = NegociacionSerializer(negociacion)
    return Response(serializer.data)


@api_view(['GET'])
def negociacion_activa_por_publicacion(request, pk):
    """
    Devuelve la negociación activa (pendiente de respuesta o ya aceptada)
    del comerciante para una publicación específica. Se usa al entrar al
    detalle para redirigir automáticamente a EsperandoPago o Pago.
    """
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    # ✅ FIX: 'esperando' no existe en Negociacion.ESTADOS — el estado real
    # mientras se espera respuesta del agricultor es 'pendiente_agricultor'.
    # Con el valor viejo, este filtro nunca encontraba nada y el auto-redirect
    # a EsperandoPagoScreen no se disparaba.
    negociacion = Negociacion.objects.filter(
        comerciante=request.user,
        publicacion_id=pk,
        estado__in=['pendiente_agricultor', 'aceptado']
    ).order_by('-creado_en').first()

    if negociacion:
        serializer = NegociacionSerializer(negociacion)
        return Response({"activa": True, "negociacion": serializer.data})
    return Response({"activa": False})


@api_view(['POST'])
def cancelar_negociacion(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        negociacion = Negociacion.objects.get(pk=pk, comerciante=request.user)
    except Negociacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    negociacion.estado = 'cancelado'
    negociacion.save()
    return Response({"message": "Negociación cancelada"})


@api_view(['PUT'])
def responder_negociacion(request, pk):
    """El agricultor acepta o rechaza."""
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        negociacion = Negociacion.objects.get(pk=pk, publicacion__vendedor=request.user)
    except Negociacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)

    accion = request.data.get('accion')

    if accion == 'aceptar':
        negociacion.estado = 'aceptado'
        negociacion.save()
        Notificacion.objects.create(
            usuario=negociacion.comerciante,
            tipo='aceptado',
            titulo='¡Negociación aceptada! 🎉',
            mensaje=f'El agricultor aceptó tu negociación de {negociacion.publicacion.producto}. Ya puedes proceder al pago.',
        )
        return Response({"message": "Negociación aceptada"})

    elif accion == 'rechazar':
        negociacion.estado = 'rechazado'
        negociacion.save()
        Notificacion.objects.create(
            usuario=negociacion.comerciante,
            tipo='rechazado',
            titulo='Negociación rechazada',
            mensaje=f'El agricultor rechazó tu negociación de {negociacion.publicacion.producto}.',
        )
        return Response({"message": "Negociación rechazada"})

    return Response({"error": "Acción inválida"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def negociaciones_agricultor(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    negociaciones = Negociacion.objects.filter(
        publicacion__vendedor=request.user
    ).order_by('-creado_en')
    serializer = NegociacionSerializer(negociaciones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def confirmar_pago(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        negociacion = Negociacion.objects.get(pk=pk, comerciante=request.user)
    except Negociacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)

    transaction_id = request.data.get('transaction_id')
    if not transaction_id:
        return Response({"error": "transaction_id requerido"}, status=status.HTTP_400_BAD_REQUEST)

    headers = {"Authorization": "Bearer prv_test_TU_LLAVE_PRIVADA"}
    wompi_response = requests.get(
        f"https://sandbox.wompi.co/v1/transactions/{transaction_id}",
        headers=headers
    )

    if wompi_response.status_code == 200:
        data = wompi_response.json()
        if data['data']['status'] == 'APPROVED':
            negociacion.estado = 'pagado'
            negociacion.save()
            return Response({"message": "Pago confirmado", "estado": "pagado"})

    return Response({"error": "Pago no aprobado"}, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
# FAVORITOS
# ─────────────────────────────────────────────

@api_view(['GET'])
def listar_favoritos(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    favoritos = Favorito.objects.filter(comerciante=request.user).order_by('-creado_en')
    serializer = FavoritoSerializer(favoritos, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
def agregar_favorito(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    favorito, created = Favorito.objects.get_or_create(comerciante=request.user, publicacion=publicacion)
    if created:
        return Response({"message": "Agregado a favoritos"}, status=status.HTTP_201_CREATED)
    return Response({"message": "Ya está en favoritos"}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def eliminar_favorito(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        favorito = Favorito.objects.get(pk=pk, comerciante=request.user)
    except Favorito.DoesNotExist:
        return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
    favorito.delete()
    return Response({"message": "Eliminado de favoritos"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# NOTIFICACIONES
# ─────────────────────────────────────────────

@api_view(['GET'])
def listar_notificaciones(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    notificaciones = Notificacion.objects.filter(usuario=request.user)
    serializer = NotificacionSerializer(notificaciones, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
def marcar_leida(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        notif = Notificacion.objects.get(pk=pk, usuario=request.user)
    except Notificacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    notif.leida = True
    notif.save()
    return Response({"message": "Marcada como leída"})


@api_view(['PUT'])
def marcar_todas_leidas(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return Response({"message": "Todas marcadas como leídas"})


# ─────────────────────────────────────────────
# CANASTA FAMILIAR
# ─────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def canasta_familiar(request):
    productos_referencia = [
        # ── TUBÉRCULOS ──────────────────────────────────────────
        {"producto": "papa_pastusa",     "nombre_display": "Papa pastusa",       "precio": 1500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papa_criolla",     "nombre_display": "Papa criolla",        "precio": 2500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papa_r12",         "nombre_display": "Papa R-12",           "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papa_capiro",      "nombre_display": "Papa capiro",         "precio": 1600,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papa_negra",       "nombre_display": "Papa negra",          "precio": 2000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "arracacha",        "nombre_display": "Arracacha",           "precio": 2300,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "yuca",             "nombre_display": "Yuca",                "precio": 1400,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "name",             "nombre_display": "Ñame",                "precio": 2200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "batata",           "nombre_display": "Batata",              "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        # ── CEREALES Y GRANOS ────────────────────────────────────
        {"producto": "arroz",            "nombre_display": "Arroz corriente",     "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "arroz_diana",      "nombre_display": "Arroz Diana",         "precio": 2200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "lenteja",          "nombre_display": "Lenteja",             "precio": 4200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "garbanzo",         "nombre_display": "Garbanzo",            "precio": 5500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "frijol_verde",     "nombre_display": "Fríjol verde",        "precio": 6000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "frijol_cargamanto","nombre_display": "Fríjol cargamanto",   "precio": 7000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "maiz",             "nombre_display": "Maíz amarillo",       "precio": 1200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cuchuco_trigo",    "nombre_display": "Cuchuco de trigo",    "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "harina_trigo",     "nombre_display": "Harina de trigo",     "precio": 2800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pasta",            "nombre_display": "Pasta",               "precio": 3800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        # ── HORTALIZAS ───────────────────────────────────────────
        {"producto": "zanahoria",        "nombre_display": "Zanahoria",           "precio": 1500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_blanca",   "nombre_display": "Cebolla blanca",      "precio": 1500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_roja",     "nombre_display": "Cebolla roja",        "precio": 1900,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_junca",    "nombre_display": "Cebolla junca",       "precio": 3333,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tomate_chonto",    "nombre_display": "Tomate chonto",       "precio": 2800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tomate_larga_vida","nombre_display": "Tomate larga vida",   "precio": 3200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mazorca",          "nombre_display": "Mazorca",             "precio": 1200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pepino_comun",     "nombre_display": "Pepino común",        "precio": 1600,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pepino_cohombro",  "nombre_display": "Pepino cohombro",     "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "auyama",           "nombre_display": "Auyama",              "precio": 1400,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "repollo",          "nombre_display": "Repollo",             "precio": 1200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "remolacha",        "nombre_display": "Remolacha",           "precio": 1300,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "espinaca",         "nombre_display": "Espinaca",            "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "lechuga",          "nombre_display": "Lechuga",             "precio": 2200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "habichuela",       "nombre_display": "Habichuela",          "precio": 5600,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "arveja_verde",     "nombre_display": "Arveja verde",        "precio": 6400,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cilantro",         "nombre_display": "Cilantro",            "precio": 6000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "acelga",           "nombre_display": "Acelga",              "precio": 2500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "apio",             "nombre_display": "Apio",                "precio": 2800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "coliflor",         "nombre_display": "Coliflor",            "precio": 3000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "brocoli",          "nombre_display": "Brócoli",             "precio": 3200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "ajo",              "nombre_display": "Ajo rosado",          "precio": 12000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "rabano",           "nombre_display": "Rábano rojo",         "precio": 1500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "alcachofa",        "nombre_display": "Alcachofa",           "precio": 4000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "haba_verde",       "nombre_display": "Haba verde",          "precio": 4500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pimenton",         "nombre_display": "Pimentón",            "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        # ── FRUTAS ───────────────────────────────────────────────
        {"producto": "platano_harton",   "nombre_display": "Plátano hartón",      "precio": 1400,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "platano_colicero", "nombre_display": "Plátano colicero",    "precio": 1200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "banano_uraba",     "nombre_display": "Banano Urabá",        "precio": 2200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "banano_criollo",   "nombre_display": "Banano criollo",      "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "limon_tahiti",     "nombre_display": "Limón Tahití",        "precio": 4000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "limon_comun",      "nombre_display": "Limón común",         "precio": 3850,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "naranja_valencia", "nombre_display": "Naranja Valencia",    "precio": 2600,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "naranja_armenia",  "nombre_display": "Naranja Armenia",     "precio": 2200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mandarina",        "nombre_display": "Mandarina arrayana",  "precio": 10000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tangelo",          "nombre_display": "Tangelo",             "precio": 4200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "aguacate_hass",    "nombre_display": "Aguacate Hass",       "precio": 7500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "aguacate_papelillo","nombre_display": "Aguacate papelillo", "precio": 10500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pina",             "nombre_display": "Piña",                "precio": 1800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papaya",           "nombre_display": "Papaya",              "precio": 2000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "gulupa",           "nombre_display": "Gulupa",              "precio": 5000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "maracuya",         "nombre_display": "Maracuyá",            "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mango_tommy",      "nombre_display": "Mango Tommy",         "precio": 3000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mango_comun",      "nombre_display": "Mango común",         "precio": 2000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "melon",            "nombre_display": "Melón",               "precio": 2500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "sandia",           "nombre_display": "Sandía",              "precio": 1500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "fresa",            "nombre_display": "Fresa",               "precio": 6000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "uva_isabela",      "nombre_display": "Uva Isabella",        "precio": 5000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mora",             "nombre_display": "Mora",                "precio": 5500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "feijoa",           "nombre_display": "Feijoa",              "precio": 4500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "lulo",             "nombre_display": "Lulo",                "precio": 4000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tomate_arbol",     "nombre_display": "Tomate de árbol",     "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "guanabana",        "nombre_display": "Guanábana",           "precio": 4000,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "curuba",           "nombre_display": "Curuba",              "precio": 3800,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "granadilla",       "nombre_display": "Granadilla",          "precio": 5500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pitahaya",         "nombre_display": "Pitahaya amarilla",   "precio": 15000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "coco",             "nombre_display": "Coco",                "precio": 3000,  "fecha": "Mayo 2026", "unidad": "und", "fuente": "Corabastos"},
        # ── PROTEÍNAS Y LÁCTEOS ──────────────────────────────────
        {"producto": "huevo",            "nombre_display": "Huevo rojo A",        "precio": 450,   "fecha": "Mayo 2026", "unidad": "und", "fuente": "Corabastos"},
        {"producto": "pollo",            "nombre_display": "Pollo entero",        "precio": 7200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "carne_res",        "nombre_display": "Carne de res",        "precio": 18000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pescado_mojarra",  "nombre_display": "Mojarra",             "precio": 12000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "leche",            "nombre_display": "Leche pasteurizada",  "precio": 3000,  "fecha": "Mayo 2026", "unidad": "lt", "fuente": "Corabastos"},
        {"producto": "queso",            "nombre_display": "Queso campesino",     "precio": 12000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "panela",           "nombre_display": "Panela",              "precio": 3500,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        # ── PROCESADOS ───────────────────────────────────────────
        {"producto": "aceite",           "nombre_display": "Aceite vegetal",      "precio": 9000,  "fecha": "Mayo 2026", "unidad": "lt", "fuente": "Corabastos"},
        {"producto": "azucar",           "nombre_display": "Azúcar blanca",       "precio": 3200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "sal",              "nombre_display": "Sal",                 "precio": 1200,  "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
    ]

    try:
        from .sipsa import consultar_precio_sipsa, PRODUCTOS_CANASTA
        resultados = []
        for nombre, clave in PRODUCTOS_CANASTA:
            data = consultar_precio_sipsa(clave)
            if data.get("precio"):
                data["nombre_display"] = nombre
                resultados.append(data)
            else:
                ref = next((p for p in productos_referencia if p["producto"] == clave), None)
                if ref:
                    resultados.append(ref)
    except Exception:
        resultados = productos_referencia

    return Response({
        "productos": resultados,
        "mercado": "Corabastos - Bogotá",
        "fecha_actualizacion": "Mayo 2026"
    })