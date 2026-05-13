from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion

class UserSerializer(serializers.ModelSerializer):
    telefono = serializers.CharField(write_only=True, required=False)
    rol = serializers.ChoiceField(choices=['Agricultor', 'Comerciante'], write_only=True)
    ubicacion = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'telefono', 'rol', 'ubicacion']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        telefono = validated_data.pop('telefono', None)
        rol = validated_data.pop('rol', 'Agricultor')
        ubicacion = validated_data.pop('ubicacion', None)

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )

        Perfil.objects.create(
            user=user,
            telefono=telefono,
            rol=rol,
            ubicacion=ubicacion
        )

        return user
from .models import Perfil, Publicacion

class PublicacionSerializer(serializers.ModelSerializer):
    vendedor_nombre = serializers.SerializerMethodField()
    vendedor_telefono = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Publicacion
        fields = ['id', 'vendedor', 'vendedor_nombre', 'vendedor_telefono', 'producto', 'descripcion', 'precio', 'unidad', 'stock', 'stock_unidad', 'ubicacion', 'imagen', 'imagen_url', 'creado_en']
        read_only_fields = ['vendedor', 'creado_en']

    def get_vendedor_nombre(self, obj):
        return f"{obj.vendedor.first_name} {obj.vendedor.last_name}".strip()

    def get_vendedor_telefono(self, obj):
        perfil = Perfil.objects.filter(user=obj.vendedor).first()
        return perfil.telefono if perfil else None

    def get_imagen_url(self, obj):
        if obj.imagen:
            return obj.imagen.url
        return None

class VisitaSerializer(serializers.ModelSerializer):
    comerciante_nombre = serializers.SerializerMethodField()
    comerciante_telefono = serializers.SerializerMethodField()
    comerciante_foto = serializers.SerializerMethodField()  # ✅ nuevo

    class Meta:
        model = VisitaPublicacion
        fields = ['id', 'comerciante', 'comerciante_nombre', 'comerciante_telefono', 'comerciante_foto', 'visitado_en']  # ✅ agregar aquí también

    def get_comerciante_nombre(self, obj):
        return f"{obj.comerciante.first_name} {obj.comerciante.last_name}".strip()

    def get_comerciante_telefono(self, obj):
        perfil = Perfil.objects.filter(user=obj.comerciante).first()
        return perfil.telefono if perfil else None

    def get_comerciante_foto(self, obj):  # ✅ nuevo método
        perfil = Perfil.objects.filter(user=obj.comerciante).first()
        if perfil and perfil.foto:
            request = self.context.get('request')
            return request.build_absolute_uri(perfil.foto.url) if request else perfil.foto.url
        return None
    
from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion

class NegociacionSerializer(serializers.ModelSerializer):
    publicacion_nombre = serializers.SerializerMethodField()
    comerciante_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Negociacion
        fields = ['id', 'publicacion', 'publicacion_nombre', 'comerciante', 'comerciante_nombre', 'cantidad', 'total', 'estado', 'referencia', 'creado_en']
        read_only_fields = ['comerciante', 'creado_en', 'referencia', 'estado']

    def get_publicacion_nombre(self, obj):
        return obj.publicacion.producto

    def get_comerciante_nombre(self, obj):
        return f"{obj.comerciante.first_name} {obj.comerciante.last_name}".strip()

from .models import Perfil, Publicacion, VisitaPublicacion, Negociacion, Favorito

class FavoritoSerializer(serializers.ModelSerializer):
    publicacion_detalle = PublicacionSerializer(source='publicacion', read_only=True)

    class Meta:
        model = Favorito
        fields = ['id', 'publicacion', 'publicacion_detalle', 'creado_en']
        read_only_fields = ['creado_en']