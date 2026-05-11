from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
from .models import Perfil

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
    serializer = VisitaSerializer(visitas, many=True)
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