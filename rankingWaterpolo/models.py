from django.db import models

class Team(models.Model):
    # Django creará el _id automáticamente, pero si ya existe en Mongo, lo reconocerá.
    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True) # URL de la imagen
    liga = models.CharField(max_length=100)
    sexo = models.CharField(max_length=20) # Ejemplo: Masculino, Femenino, Mixto
    entrenador = models.CharField(max_length=100)
    piscina = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)

    class Meta:
        db_table = 'teams'  # MUY IMPORTANTE: Esto le dice a Django que use tu colección existente
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.nombre} - {self.liga}"