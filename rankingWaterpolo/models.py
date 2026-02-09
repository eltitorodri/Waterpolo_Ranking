from djongo import models  # <--- IMPORTANTE: Usamos djongo, no django.db


# 1. CATEGORIAS
class Categoria(models.Model):
    _id = models.ObjectIdField(primary_key=True)  # <--- Añadido para Mongo
    nombre = models.CharField(max_length=100, unique=True)

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


# 3. VALORACIONES
class Valoracion(models.Model):
    _id = models.ObjectIdField()  # <--- Añadido para Mongo
    equipo = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='valoraciones')
    puntuacion = models.IntegerField(help_text="Puntuación del 1 al 10")
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valoración"


# 4. RANKINGS
class Ranking(models.Model):
    _id = models.ObjectIdField()  # <--- Añadido para Mongo
    nombre = models.CharField(max_length=100)
    # Las relaciones M2M necesitan que los modelos tengan el _id definido
    equipos = models.ManyToManyField(Team, related_name='rankings')
    temporada = models.CharField(max_length=20, default="2025/2026")

    def __str__(self):
        return self.nombre