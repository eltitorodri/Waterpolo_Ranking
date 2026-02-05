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
