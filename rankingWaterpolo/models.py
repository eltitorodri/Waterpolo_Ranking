from djongo import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    temporada = models.CharField(
        max_length=50,
        default="2024/25",
        verbose_name="Temporada"
    )
    imagen = models.ImageField(
        upload_to='categorias/',
        null=True,
        blank=True,
        verbose_name="Logo/Imagen"
    )

    equipos = models.ManyToManyField('Team', related_name='categorias_asignadas', blank=True)

    def __str__(self):
        return self.nombre


class Team(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True)

    categoria = models.ForeignKey(
        'Categoria',
        on_delete=models.SET_NULL,
        related_name='equipos_originales',
        null=True,
        blank=True
    )

    liga = models.CharField(max_length=100)
    sexo = models.CharField(max_length=20)
    entrenador = models.CharField(max_length=100, blank=True, null=True)
    piscina = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'equipos'
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.nombre} ({self.liga})"


class Valoracion(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    equipo = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='valoraciones')

    usuario_id = models.IntegerField()
    puntuacion = models.IntegerField(help_text="Puntuación del 1 al 10")
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valoración"
        verbose_name_plural = "Valoraciones"

    def __str__(self):
        return f"Val: {self.puntuacion} - {self.equipo.nombre}"


class Ranking(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)

    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=100, default="Mi Top 5")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    posicion_1_id = models.CharField(max_length=24)
    posicion_2_id = models.CharField(max_length=24)
    posicion_3_id = models.CharField(max_length=24)
    posicion_4_id = models.CharField(max_length=24)
    posicion_5_id = models.CharField(max_length=24)

    def __str__(self):
        return f"{self.username} - {self.nombre}"