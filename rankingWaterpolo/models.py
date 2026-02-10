from djongo import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    # --- NUEVOS CAMPOS ---
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
    # ---------------------

    equipos = models.ManyToManyField('Team', related_name='categorias_asignadas')

    def __str__(self):
        return self.nombre

# --- 2. EQUIPOS (Team) ---
class Team(models.Model):
    _id = models.ObjectIdField(primary_key=True)  # Asegúrate de que tenga primary_key=True para evitar líos
    nombre = models.CharField(max_length=100)
    escudo = models.URLField(max_length=500, blank=True, null=True)

    # Aquí también usamos 'Categoria' con comillas por coherencia
    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, related_name='equipos_originales', null=True)

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


# --- 3. VALORACIONES ---
class Valoracion(models.Model):
    _id = models.ObjectIdField(primary_key=True)

    # Aquí ya podemos usar Team sin comillas porque Team está definido arriba,
    # pero ponerlas tampoco hace daño.
    equipo = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='valoraciones')
    usuario_id = models.IntegerField()
    puntuacion = models.IntegerField(help_text="Puntuación del 1 al 10")
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valoración"

    def __str__(self):
        return f"Valoración de {self.equipo.nombre}: {self.puntuacion}"


# --- 4. RANKINGS ---
class Ranking(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Relación con Categoria
    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, null=True, blank=True)

    nombre = models.CharField(max_length=100, default="Mi Top 5")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Posiciones (Relación con Team)
    posicion_1 = models.ForeignKey('Team', related_name='r_pos1', on_delete=models.CASCADE)
    posicion_2 = models.ForeignKey('Team', related_name='r_pos2', on_delete=models.CASCADE)
    posicion_3 = models.ForeignKey('Team', related_name='r_pos3', on_delete=models.CASCADE)
    posicion_4 = models.ForeignKey('Team', related_name='r_pos4', on_delete=models.CASCADE)
    posicion_5 = models.ForeignKey('Team', related_name='r_pos5', on_delete=models.CASCADE)

    def __str__(self):
        cat_nombre = self.categoria.nombre if self.categoria else "General"
        return f"{self.user.username} - {cat_nombre}"