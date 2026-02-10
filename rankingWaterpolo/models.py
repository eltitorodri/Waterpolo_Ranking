from djongo import models
from .models import Team # Asegúrate de importar Team

# 1. CATEGORIAS (Modificado)
class Categoria(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    # AÑADIDO: Relación muchos a muchos. Una categoría tiene muchos equipos.
    equipos = models.ManyToManyField(Team, related_name='categorias_asignadas')

    def __str__(self):
        return self.nombre


# 2. ELEMENTOS (Tus equipos)
class Team(models.Model):
    # Definimos explícitamente el ID de Mongo para que Django lo reconozca
    _id = models.ObjectIdField()

    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, related_name='equipos', null=True)
    liga = models.CharField(max_length=100)
    sexo = models.CharField(max_length=20)
    entrenador = models.CharField(max_length=100)
    piscina = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)

    class Meta:
        db_table = 'equipos'
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.nombre} ({self.liga})"


# models.py
from djongo import models
from .models import Team  # Asegúrate de importar Team


class Valoracion(models.Model):
    _id = models.ObjectIdField(primary_key=True)

    # Vinculamos al equipo
    equipo = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='valoraciones')

    # Vinculamos al usuario (Usamos ID numérico para evitar líos entre SQLite y Mongo)
    usuario_id = models.IntegerField()

    puntuacion = models.IntegerField(help_text="Puntuación del 1 al 10")
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valoración"

    def __str__(self):
        return f"Valoración de {self.equipo.nombre}: {self.puntuacion}"


# models.py

import uuid  # <--- 1. AÑADE ESTA IMPORTACIÓN ARRIBA DEL TODO
from djongo import models
from django.contrib.auth.models import User


# ... (Categoria y Team déjalos EXACTAMENTE COMO ESTABAN, con su ObjectId) ...
# Solo cambiamos el Ranking

# 4. RANKINGS
class Ranking(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # AÑADIDO: Para saber de qué es este ranking (puede ser null si es un ranking general)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)

    nombre = models.CharField(max_length=100, default="Mi Top 5")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Tus campos de posiciones...
    posicion_1 = models.ForeignKey(Team, related_name='r_pos1', on_delete=models.CASCADE)
    posicion_2 = models.ForeignKey(Team, related_name='r_pos2', on_delete=models.CASCADE)
    posicion_3 = models.ForeignKey(Team, related_name='r_pos3', on_delete=models.CASCADE)
    posicion_4 = models.ForeignKey(Team, related_name='r_pos4', on_delete=models.CASCADE)
    posicion_5 = models.ForeignKey(Team, related_name='r_pos5', on_delete=models.CASCADE)

    def __str__(self):
        cat_nombre = self.categoria.nombre if self.categoria else "General"
        return f"{self.user.username} - {cat_nombre}"