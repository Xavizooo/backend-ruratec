from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField


class Perfil(models.Model):
    ROLES = [
        ('Agricultor', 'Agricultor'),
        ('Comerciante', 'Comerciante'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='Agricultor')
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    foto = CloudinaryField('foto', blank=True, null=True)
    push_token = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user.username} - {self.rol}"


class Publicacion(models.Model):
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.IntegerField()
    unidad = models.CharField(max_length=50)
    ubicacion = models.CharField(max_length=100)
    imagen = CloudinaryField('imagen', blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    stock = models.IntegerField(default=0)
    stock_unidad = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.producto} - {self.vendedor.username}"


class VisitaPublicacion(models.Model):
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='visitas')
    comerciante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visitas')
    visitado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('publicacion', 'comerciante')

    def __str__(self):
        return f"{self.comerciante.username} vio {self.publicacion.producto}"


class Negociacion(models.Model):
    ESTADOS = [
        ('pendiente_agricultor', 'Pendiente Agricultor'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
        ('pendiente', 'Pendiente de pago'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='negociaciones')
    comerciante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='negociaciones')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente_agricultor')
    referencia = models.CharField(max_length=100, unique=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.comerciante.username} - {self.publicacion.producto} - {self.estado}"


class Favorito(models.Model):
    comerciante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='favoritos')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comerciante', 'publicacion')

    def __str__(self):
        return f"{self.comerciante.username} ❤️ {self.publicacion.producto}"


class Notificacion(models.Model):
    TIPOS = [
        ('visita', 'Visita'),
        ('negociacion', 'Negociación'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
        ('pago', 'Pago'),
        ('expiracion', 'Expiración'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    negociacion = models.ForeignKey(
        Negociacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones'
    )

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.usuario.username} - {self.titulo}"