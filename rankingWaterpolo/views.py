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
@login_required(login_url='login')
def crear_top5(request):
    if request.method == 'POST':
        nombre_ranking = request.POST.get('nombre_ranking')
        ids_seleccionados = [
            request.POST.get('equipo_1'),
            request.POST.get('equipo_2'),
            request.POST.get('equipo_3'),
            request.POST.get('equipo_4'),
            request.POST.get('equipo_5'),
        ]

        # Creamos el Ranking en Mongo
        nuevo_ranking = Ranking.objects.using('mongo_db').create(
            nombre=nombre_ranking,
            temporada="2025/2026"
        )

        # Filtramos los equipos de Mongo y los añadimos a la relación ManyToMany
        equipos_objetos = Team.objects.using('mongo_db').filter(id__in=ids_seleccionados)
        nuevo_ranking.equipos.add(*equipos_objetos)

        messages.success(request, "¡Tu Top 5 ha sido guardado en MongoDB!")
        return redirect('home')

    # Equipos de Mongo para los selects
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')
    return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})