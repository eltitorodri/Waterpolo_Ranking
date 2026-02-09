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
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Team, Ranking  # Asegúrate de importar tus modelos


@login_required(login_url='login')
def crear_top5(request):
    # LÓGICA POST: Guardar
    if request.method == 'POST':
        nombre_ranking = request.POST.get('nombre_ranking')

        # 1. Ahora recibimos NOMBRES, no IDs
        raw_nombres = [
            request.POST.get('equipo_1'),
            request.POST.get('equipo_2'),
            request.POST.get('equipo_3'),
            request.POST.get('equipo_4'),
            request.POST.get('equipo_5')
        ]

        # 2. Limpiamos la lista
        nombres_seleccionados = [x for x in raw_nombres if x and x != 'None' and x != '']

        if nombres_seleccionados and nombre_ranking:
            try:
                # A) Crear Ranking
                nuevo_ranking = Ranking.objects.using('mongo_db').create(
                    nombre=nombre_ranking,
                    temporada="2025/2026"
                )

                # B) BUSCAR POR NOMBRE (__in funciona perfecto con strings)
                equipos_encontrados = list(Team.objects.using('mongo_db').filter(nombre__in=nombres_seleccionados))

                # C) Guardar relación
                nuevo_ranking.equipos.add(*equipos_encontrados)
                nuevo_ranking.save()

                messages.success(request, "¡Ranking guardado correctamente!")
                return redirect('mis_rankings')

            except Exception as e:
                print(f"ERROR AL GUARDAR: {e}")  # Mira la terminal si falla
                messages.error(request, "Hubo un error al guardar el ranking.")
        else:
            messages.error(request, "Faltan datos (título o equipos).")

    # LÓGICA GET: Mostrar formulario
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')
    return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})


# --- VER MIS RANKINGS (Muro) ---
@login_required(login_url='login')
def mis_rankings(request):
    # CAMBIO AQUÍ: Usa '-pk' en lugar de '-id'
    rankings = Ranking.objects.using('mongo_db').all().order_by('-pk')

    return render(request, 'rankingWaterpolo/mis_rankings.html', {'rankings': rankings})