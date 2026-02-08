from django.db import models

class Team(models.Model):
    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True)
    liga = models.CharField(max_length=100)
    sexo = models.CharField(max_length=20)
    entrenador = models.CharField(max_length=100)
    piscina = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)

    class Meta:
        db_table = 'teams'
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.nombre} - {self.liga}"