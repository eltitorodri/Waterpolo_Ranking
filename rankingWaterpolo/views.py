from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# --- SIGNUP (REGISTRO) ---
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Capturamos los datos exactos de tu HTML
        nick = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('confirm_password')

        # Validaciones
        if pass1 != pass2:
            messages.error(request, "Las contraseñas no coinciden")
            return render(request, 'rankingWaterpolo/signup.html')

        if User.objects.filter(username=nick).exists():
            messages.error(request, "El usuario ya existe")
            return render(request, 'rankingWaterpolo/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado")
            return render(request, 'rankingWaterpolo/signup.html')

        # Crear Usuario
        try:
            user = User.objects.create_user(username=nick, email=email, password=pass1)
            user.save()
            # Loguear automáticamente tras registrarse
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
        # IMPORTANTE: Ahora el HTML manda 'username', así que lo leemos así:
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
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .models import Categoria, Team, Valoracion

@login_required(login_url='login')
def home(request):
    query = request.GET.get('q', '')

    # Filtrado de categorías
    if query:
        categorias = Categoria.objects.filter(nombre__icontains=query)
    else:
        categorias = Categoria.objects.all()

    # Lógica para "Mejor Valorado":
    # Calculamos la media de 'puntuacion' de la tabla Valoracion para cada equipo
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