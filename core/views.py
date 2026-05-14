from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
from .models import Perfil
from .notificaciones import enviar_notificacion

@api_view(['POST'])
def registrar_usuario(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Usuario creado correctamente"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                        context={'request': request})
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
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer, PublicacionSerializer
from .models import Perfil, Publicacion

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

from .models import Perfil, Publicacion, VisitaPublicacion
from .serializers import UserSerializer, PublicacionSerializer, VisitaSerializer

@api_view(['POST'])
def registrar_visita(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)
    
    # No registrar si el comerciante es el mismo vendedor
    if publicacion.vendedor == request.user:
        return Response({"message": "Es tu propia publicación"})
    
    VisitaPublicacion.objects.get_or_create(
        publicacion=publicacion,
        comerciante=request.user
    )
    
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


from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion
from .serializers import UserSerializer, PublicacionSerializer, VisitaSerializer, NegociacionSerializer
import uuid
import requests

@api_view(['POST'])
def crear_negociacion(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        publicacion = Publicacion.objects.get(pk=pk)
    except Publicacion.DoesNotExist:
        return Response({"error": "No encontrada"}, status=status.HTTP_404_NOT_FOUND)

    cantidad = request.data.get('cantidad')
    if not cantidad:
        return Response({"error": "Cantidad requerida"}, status=status.HTTP_400_BAD_REQUEST)

    total = int(cantidad) * publicacion.precio
    referencia = f"RURATEC-{uuid.uuid4().hex[:10].upper()}"

    negociacion = Negociacion.objects.create(
        publicacion=publicacion,
        comerciante=request.user,
        cantidad=cantidad,
        total=total,
        referencia=referencia,
    )

    serializer = NegociacionSerializer(negociacion)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    # Verificar pago con Wompi
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
    
from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion, Favorito
from .serializers import UserSerializer, PublicacionSerializer, VisitaSerializer, NegociacionSerializer, FavoritoSerializer

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
    
    favorito, created = Favorito.objects.get_or_create(
        comerciante=request.user,
        publicacion=publicacion
    )
    
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

@api_view(['POST'])
def crear_publicacion(request):
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    print("FILES:", request.FILES)  # ✅ agrega esto
    print("DATA:", request.data)    # ✅ y esto
    
    serializer = PublicacionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(vendedor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .sipsa import consultar_precio_sipsa, PRODUCTOS_CANASTA
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def canasta_familiar(request):
    productos_referencia = [
        # Tubérculos
        {"producto": "papa", "nombre_display": "Papa pastusa", "precio": 1500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papa_criolla", "nombre_display": "Papa criolla", "precio": 2500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "arracacha", "nombre_display": "Arracacha", "precio": 2300, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},

        # Cereales y granos
        {"producto": "arroz", "nombre_display": "Arroz corriente", "precio": 1800, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "lenteja", "nombre_display": "Lenteja", "precio": 4200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "garbanzo", "nombre_display": "Garbanzo", "precio": 5500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "frijol", "nombre_display": "Fríjol verde", "precio": 6000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},

        # Hortalizas
        {"producto": "zanahoria", "nombre_display": "Zanahoria", "precio": 1500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_blanca", "nombre_display": "Cebolla cabezona blanca", "precio": 1500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_roja", "nombre_display": "Cebolla cabezona roja", "precio": 1900, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cebolla_junca", "nombre_display": "Cebolla junca", "precio": 3333, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tomate", "nombre_display": "Tomate chonto", "precio": 2800, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mazorca", "nombre_display": "Mazorca", "precio": 1200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pepino", "nombre_display": "Pepino cohombro", "precio": 1800, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "auyama", "nombre_display": "Auyama", "precio": 1400, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "repollo", "nombre_display": "Repollo", "precio": 1200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "remolacha", "nombre_display": "Remolacha", "precio": 1300, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "espinaca", "nombre_display": "Espinaca", "precio": 3500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "lechuga", "nombre_display": "Lechuga", "precio": 2200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "habichuela", "nombre_display": "Habichuela", "precio": 5600, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "arveja", "nombre_display": "Arveja verde", "precio": 6400, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "cilantro", "nombre_display": "Cilantro", "precio": 6000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},

        # Frutas
        {"producto": "platano", "nombre_display": "Plátano hartón", "precio": 1400, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "banano", "nombre_display": "Banano Urabá", "precio": 2200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "limon_tahiti", "nombre_display": "Limón Tahití", "precio": 4000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "limon_comun", "nombre_display": "Limón común", "precio": 1071, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "naranja_valencia", "nombre_display": "Naranja valencia", "precio": 2600, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "mandarina", "nombre_display": "Mandarina arrayana", "precio": 10000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "aguacate_hass", "nombre_display": "Aguacate Hass", "precio": 7500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "pina", "nombre_display": "Piña", "precio": 1800, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "papaya", "nombre_display": "Papaya", "precio": 2000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "gulupa", "nombre_display": "Gulupa", "precio": 5000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "tangelo", "nombre_display": "Tangelo", "precio": 4200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},

        # Proteínas y lácteos
        {"producto": "huevo", "nombre_display": "Huevo rojo A", "precio": 450, "fecha": "Mayo 2026", "unidad": "und", "fuente": "Corabastos"},
        {"producto": "pollo", "nombre_display": "Pollo entero", "precio": 7200, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "leche", "nombre_display": "Leche pasteurizada", "precio": 3000, "fecha": "Mayo 2026", "unidad": "lt", "fuente": "Corabastos"},
        {"producto": "queso", "nombre_display": "Queso", "precio": 12000, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
        {"producto": "panela", "nombre_display": "Panela", "precio": 3500, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},

        # Procesados
        {"producto": "aceite", "nombre_display": "Aceite vegetal", "precio": 9000, "fecha": "Mayo 2026", "unidad": "lt", "fuente": "Corabastos"},
        {"producto": "pasta", "nombre_display": "Pasta", "precio": 3800, "fecha": "Mayo 2026", "unidad": "kg", "fuente": "Corabastos"},
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

    return Response({"productos": resultados, "mercado": "Corabastos - Bogotá", "fecha_actualizacion": "Mayo 2026"})