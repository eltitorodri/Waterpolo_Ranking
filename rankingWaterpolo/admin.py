from django.contrib import admin
from .models import Categoria, Team, Valoracion


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):

    list_display = ('nombre', 'liga', 'ciudad', 'sexo')


admin.site.register(Categoria)
admin.site.register(Valoracion)