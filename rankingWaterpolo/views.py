from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from bson import ObjectId
from .models import Team, Ranking, Categoria, Valoracion


# --- 1. AUTENTICACIÓN (Login, Registro, Logout) ---

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Bienvenido, {user.username}")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'rankingWaterpolo/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'rankingWaterpolo/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# --- 2. HOME (Con estadísticas) ---

def home(request):
    # Lógica de Búsqueda
    query = request.GET.get('q')
    if query:
        categorias = Categoria.objects.using('mongo_db').filter(
            Q(nombre__icontains=query)  # Quitamos descripción por si no existe campo
        )
    else:
        categorias = Categoria.objects.using('mongo_db').all()

    # Lógica de Estadísticas
    equipos = Team.objects.using('mongo_db').all()
    todas_vals = Valoracion.objects.using('mongo_db').all()

    total_valoraciones = todas_vals.count()
    mejor_equipo = None
    max_media = -1

    for equipo in equipos:
        vals_equipo = Valoracion.objects.using('mongo_db').filter(equipo=equipo)

        if vals_equipo.exists():
            promedio = sum(v.puntuacion for v in vals_equipo) / vals_equipo.count()
            equipo.media_puntos = round(promedio, 1)  # Redondeamos para que quede bonito

            if promedio > max_media:
                max_media = promedio
                mejor_equipo = equipo
        else:
            equipo.media_puntos = 0

    context = {
        'categorias': categorias,
        'query': query,
        'mejor_equipo': mejor_equipo,
        'total_valoraciones': total_valoraciones,
    }
    return render(request, 'rankingWaterpolo/home.html', context)


# --- 3. RANKINGS (Nuevo sistema con Categorías) ---

@login_required(login_url='login')
def crear_ranking(request, categoria_id=None):
    categoria_obj = None
    equipos = []

    if categoria_id:
        try:
            mongo_id = ObjectId(categoria_id)
            categoria_obj = Categoria.objects.using('mongo_db').get(_id=mongo_id)

            # --- ESTRATEGIA DE RECUPERACIÓN PARA MONGODB ---

            # Intento 1: Buscar equipos que tengan asignada esta categoría (ForeignKey)
            equipos_por_fk = Team.objects.using('mongo_db').filter(categoria=categoria_obj)

            # Intento 2: Buscar equipos asociados a través del ManyToMany de la categoría
            # Usamos list() para forzar a Djongo a traer los datos de la colección
            equipos_por_m2m = categoria_obj.equipos.all().using('mongo_db')

            # Combinamos ambos resultados y eliminamos duplicados
            # Convertimos a lista para que el template pueda iterar sin problemas
            equipos = list(set(list(equipos_por_fk) + list(equipos_por_m2m)))

            # Ordenamos por nombre para que no salgan aleatorios
            equipos.sort(key=lambda x: x.nombre)

        except Exception as e:
            print(f"Error recuperando equipos: {e}")
            messages.error(request, "Categoría no encontrada.")
            return redirect('home')
    else:
        # Esto es lo que te funcionaba bien (General)
        equipos = Team.objects.using('mongo_db').all().order_by('nombre')

    # ... El resto de tu lógica del POST se queda exactamente igual ...
    if request.method == 'POST':
        # (Mantén el código del POST que ya tienes aquí)
        p1 = request.POST.get('posicion_1')
        p2 = request.POST.get('posicion_2')
        p3 = request.POST.get('posicion_3')
        p4 = request.POST.get('posicion_4')
        p5 = request.POST.get('posicion_5')
        titulo = request.POST.get('titulo')

        if all([p1, p2, p3, p4, p5, titulo]):
            nuevo_ranking = Ranking.objects.using('mongo_db').create(
                user_id=request.user.id,
                username=request.user.username,
                categoria=categoria_obj,
                nombre=titulo,
                posicion_1_id=p1,
                posicion_2_id=p2,
                posicion_3_id=p3,
                posicion_4_id=p4,
                posicion_5_id=p5
            )
            messages.success(request, f"¡Ranking '{titulo}' creado con éxito!")
            return redirect('mis_rankings')
        else:
            messages.error(request, "Faltan datos para completar el ranking.")

    return render(request, 'rankingWaterpolo/crear_top5.html', {
        'equipos': equipos,
        'categoria': categoria_obj
    })

@login_required(login_url='login')
def mis_rankings(request):
    # Filtramos por user_id
    rankings = Ranking.objects.using('mongo_db') \
        .filter(user_id=request.user.id) \
        .order_by('-fecha_creacion')

    return render(request, 'rankingWaterpolo/mis_rankings.html', {
        'rankings': rankings
    })


# --- 4. VALORACIONES (Con corrección de ObjectId) ---

@login_required(login_url='login')
def valorar_equipos(request):
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        puntos = request.POST.get('puntuacion')
        comentario = request.POST.get('comentario')

        if team_id and puntos:
            try:
                mongo_id = ObjectId(team_id)
                equipo = Team.objects.using('mongo_db').get(_id=mongo_id)

                valoracion_existente = Valoracion.objects.using('mongo_db').filter(
                    equipo=equipo,
                    usuario_id=request.user.id
                ).first()

                if valoracion_existente:
                    valoracion_existente.puntuacion = int(puntos)
                    valoracion_existente.comentario = comentario
                    valoracion_existente.save()
                    messages.success(request, f"Actualizado: {equipo.nombre}")
                else:
                    Valoracion.objects.using('mongo_db').create(
                        equipo=equipo,
                        usuario_id=request.user.id,
                        puntuacion=int(puntos),
                        comentario=comentario
                    )
                    messages.success(request, f"Valorado: {equipo.nombre}")

            except Exception as e:
                messages.error(request, f"Error: {e}")

        return redirect('valorar_equipos')

    # Parte GET
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')

    for equipo in equipos:
        equipo.mi_valoracion = Valoracion.objects.using('mongo_db').filter(
            equipo=equipo,
            usuario_id=request.user.id
        ).first()

    return render(request, 'rankingWaterpolo/valorar_equipos.html', {'equipos': equipos})

from django.contrib.admin.views.decorators import staff_member_required
from .forms import CategoriaForm # Asegúrate de importar el form


@staff_member_required(login_url='home')
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 1. Guardar datos básicos de la categoría
                categoria = form.save(commit=False)
                categoria.save(using='mongo_db')

                # 2. Gestionar los equipos
                team_ids = form.cleaned_data.get('equipos')
                if team_ids:
                    # Buscamos los equipos reales en Mongo usando los IDs recibidos
                    equipos_qs = Team.objects.using('mongo_db').filter(pk__in=team_ids)
                    categoria.equipos.set(equipos_qs)

                messages.success(request, '¡Categoría creada con éxito!')
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Error al guardar: {e}")
        else:
            print(f"Errores del formulario: {form.errors}")
    else:
        form = CategoriaForm()

    return render(request, 'rankingWaterpolo/crear_categoria.html', {'form': form})