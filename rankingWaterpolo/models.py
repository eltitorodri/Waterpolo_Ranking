from django.db import models

# 1. CATEGORIAS (Para agrupar tus equipos: ej. "División de Honor", "Liga Regional")
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

# 2. ELEMENTOS (Tus equipos que ya están en Mongo)
class Team(models.Model):
    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True)
    # Conectamos cada equipo con una categoría
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, related_name='equipos', null=True)
    liga = models.CharField(max_length=100)
    sexo = models.CharField(max_length=20)
    entrenador = models.CharField(max_length=100)
    piscina = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)

    class Meta:
        db_table = 'teams' # Forzamos a que use tu tabla de Mongo
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.nombre} ({self.liga})"

# 3. VALORACIONES (Lo que pide el maestro para puntuar los elementos/equipos)
class Valoracion(models.Model):
    equipo = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='valoraciones')
    puntuacion = models.IntegerField(help_text="Puntuación del 1 al 10")
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valoración"

# 4. RANKINGS (La tabla final que el profe quiere ver)
class Ranking(models.Model):
    nombre = models.CharField(max_length=100) # Ej: "Top Equipos Andalucía"
    equipos = models.ManyToManyField(Team, related_name='rankings')
    temporada = models.CharField(max_length=20, default="2025/2026")

    def __str__(self):
        return self.nombre