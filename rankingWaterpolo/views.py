from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .models import Categoria, Team, Valoracion, Ranking


# --- SIGNUP (REGISTRO) ---
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        nick = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('confirm_password')

        if pass1 != pass2:
            messages.error(request, "Las contraseñas no coinciden")
            return render(request, 'rankingWaterpolo/signup.html')

        if User.objects.filter(username=nick).exists():
            messages.error(request, "El usuario ya existe")
            return render(request, 'rankingWaterpolo/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado")
            return render(request, 'rankingWaterpolo/signup.html')

        try:
            user = User.objects.create_user(username=nick, email=email, password=pass1)
            user.save()
            login(request, user)
            return redirect('home')
        except:
            messages.error(request, "Error desconocido al crear la cuenta")
            return render(request, 'rankingWaterpolo/signup.html')

    return render(request, 'rankingWaterpolo/signup.html')


# --- LOGIN ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        nombre_usuario = request.POST.get('username')
        clave = request.POST.get('password')
        user = authenticate(request, username=nombre_usuario, password=clave)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'rankingWaterpolo/login.html')


# --- LOGOUT ---
def logout_view(request):
    logout(request)
    return redirect('login')


# --- HOME ---
@login_required(login_url='login')
def home(request):
    query = request.GET.get('q', '')
    if query:
        categorias = Categoria.objects.filter(nombre__icontains=query)
    else:
        categorias = Categoria.objects.all()

    mejor_equipo = Team.objects.annotate(
        media_puntos=Avg('valoraciones__puntuacion')
    ).order_by('-media_puntos').first()

    total_valoraciones = Valoracion.objects.count()

    context = {
        'categorias': categorias,
        'query': query,
        'mejor_equipo': mejor_equipo,
        'total_valoraciones': total_valoraciones,
    }
    return render(request, 'rankingWaterpolo/home.html', context)


# --- CREAR RANKING TOP 5 ---
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Team, Ranking

@login_required(login_url='login')
def crear_top5(request):
    if request.method == 'POST':
        nombre_ranking = request.POST.get('nombre_ranking')

        # Recogemos los nombres de los equipos
        raw_nombres = [
            request.POST.get('equipo_1'),
            request.POST.get('equipo_2'),
            request.POST.get('equipo_3'),
            request.POST.get('equipo_4'),
            request.POST.get('equipo_5')
        ]
        nombres_limpios = [x.strip() for x in raw_nombres if x and x.strip() != '']

        # Validaciones previas
        if not nombre_ranking or len(nombres_limpios) != 5:
            messages.error(request, "Debes seleccionar 5 equipos y poner un título.")
            equipos = Team.objects.using('mongo_db').all().order_by('nombre')
            return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})

        # Buscamos los equipos exactos en la DB
        equipos_db = list(Team.objects.using('mongo_db').filter(nombre__in=nombres_limpios))

        # Validación: que existan los 5 equipos
        if len(equipos_db) != 5:
            messages.error(request, "Error crítico: Algunos equipos seleccionados no existen en la base de datos.")
            equipos = Team.objects.using('mongo_db').all().order_by('nombre')
            return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})

        try:
            # --- CREAR O ACTUALIZAR --- #
            ranking_existente = Ranking.objects.using('mongo_db').filter(nombre=nombre_ranking).first()

            if ranking_existente:
                # Actualizamos ranking existente
                ranking_existente.equipos.set(equipos_db)
                ranking_existente.temporada = "2025/2026"
                ranking_existente.save()
            else:
                # Creamos uno nuevo
                nuevo_ranking = Ranking.objects.using('mongo_db').create(
                    nombre=nombre_ranking,
                    temporada="2025/2026"
                )
                nuevo_ranking.equipos.set(equipos_db)
                nuevo_ranking.save()

            messages.success(request, "¡Tu Top 5 se ha publicado correctamente!")
            return redirect('mis_rankings')

        except Exception as e:
            messages.error(request, f"Ocurrió un error al guardar el ranking: {e}")
            equipos = Team.objects.using('mongo_db').all().order_by('nombre')
            return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})

    # --- GET --- #
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')
    return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})


@login_required(login_url='login')
def mis_rankings(request):
    rankings = Ranking.objects.using('mongo_db').all().order_by('-pk')
    return render(request, 'rankingWaterpolo/mis_rankings.html', {'rankings': rankings})
