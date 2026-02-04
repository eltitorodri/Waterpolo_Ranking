from django.contrib import admin
from .models import Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    # Esto define qué columnas verás en la lista del admin
    list_display = ('nombre', 'liga', 'ciudad', 'sexo')
