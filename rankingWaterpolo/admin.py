from django.contrib import admin
from .models import Categoria, Team, Valoracion

# 1. Registro de Team con su configuración especial
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    # Esto define qué columnas verás en la lista del admin
    list_display = ('nombre', 'liga', 'ciudad', 'sexo')

# 2. Registro de los demás modelos (SIN repetir Team)
admin.site.register(Categoria)
admin.site.register(Valoracion)