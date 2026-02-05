from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Team

@login_required
def home(request):
    equipos = Team.objects.all()
    return render(request, 'rankingWaterpolo/lista_equipos.html', {'equipos': equipos})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')  # si ya está logueado, va directo a home

    if request.method == 'POST':
        nombre_usuario = request.POST.get('nickname')
        clave = request.POST.get('password')

        user = authenticate(request, username=nombre_usuario, password=clave)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'rankingWaterpolo/login.html')


from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages


def signup_view(request):
    if request.method == 'POST':
        # Capturamos los datos del formulario (los "name" del HTML)
        nick = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('confirm_password')

        # Validación básica
        if pass1 != pass2:
            messages.error(request, "LAS CONTRASEÑAS NO COINCIDEN")
            return render(request, 'ranking/signup.html')

        if User.objects.filter(username=nick).exists():
            messages.error(request, "EL NICKNAME YA ESTÁ EN USO")
            return render(request, 'ranking/signup.html')

        # Crear usuario
        user = User.objects.create_user(username=nick, email=email, password=pass1)
        user.save()

        messages.success(request, "¡REGISTRO COMPLETADO!")
        return redirect('login')  # Te manda al login tras registrarte

    return render(request, 'rankingWaterpolo/signup.html')