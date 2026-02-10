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
# views.py

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
        # Limpiamos espacios y vacíos
        nombres_limpios = [x.strip() for x in raw_nombres if x and x.strip() != '']

        # --- VALIDACIÓN DE SEGURIDAD ---
        # Si falta el título O no hay 5 equipos, paramos aquí.
        if not nombre_ranking or len(nombres_limpios) != 5:
            messages.error(request, "⚠️ Error: Faltan datos. Asegúrate de poner título y elegir 5 equipos.")
            equipos = Team.objects.using('mongo_db').all().order_by('nombre')
            return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})

        # Buscamos los equipos en la DB
        equipos_db = list(Team.objects.using('mongo_db').filter(nombre__in=nombres_limpios))

        if len(equipos_db) != 5:
            messages.error(request, "Error: Algunos equipos seleccionados no existen en la base de datos.")
            return redirect('crear_top5')

        try:
            # --- GUARDADO VINCULADO AL USUARIO ---
            # Buscamos si ESTE usuario (por su ID) ya tiene un ranking con ese nombre
            ranking_existente = Ranking.objects.using('mongo_db').filter(
                nombre=nombre_ranking,
                usuario_id=request.user.id  # <--- USAMOS EL ID DE SQLITE
            ).first()

            if ranking_existente:
                # Actualizar existente
                ranking_existente.equipos.set(equipos_db)
                ranking_existente.temporada = "2025/2026"
                ranking_existente.save()
                messages.success(request, f"¡Has actualizado tu ranking '{nombre_ranking}'!")
            else:
                # Crear nuevo
                nuevo_ranking = Ranking.objects.using('mongo_db').create(
                    nombre=nombre_ranking,
                    temporada="2025/2026",
                    usuario_id=request.user.id  # <--- GUARDAMOS EL DUEÑO
                )
                nuevo_ranking.equipos.set(equipos_db)
                nuevo_ranking.save()
                messages.success(request, "¡Ranking creado correctamente!")

            return redirect('mis_rankings')

        except Exception as e:
            print(f"Error al guardar: {e}")
            messages.error(request, "Error interno al guardar el ranking.")
            return redirect('crear_top5')

    # GET
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')
    return render(request, 'rankingWaterpolo/crear_top5.html', {'equipos': equipos})


# --- MIS RANKINGS ---
@login_required(login_url='login')
def mis_rankings(request):
    # --- FILTRO DE PRIVACIDAD ---
    # Solo traemos los rankings donde el usuario_id coincide con el del usuario conectado
    rankings = Ranking.objects.using('mongo_db').filter(usuario_id=request.user.id).order_by('-pk')

    return render(request, 'rankingWaterpolo/mis_rankings.html', {'rankings': rankings})


# views.py
# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Team, Valoracion
from bson import ObjectId  # <--- 1. AÑADE ESTA LÍNEA AL PRINCIPIO


@login_required(login_url='login')
def valorar_equipos(request):
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        puntos = request.POST.get('puntuacion')
        comentario = request.POST.get('comentario')

        if team_id and puntos:
            try:
                # 2. CONVERTIMOS EL TEXTO A ID DE MONGO AQUÍ:
                mongo_id = ObjectId(team_id)

                # Buscamos usando _id y el objeto convertido
                equipo = Team.objects.using('mongo_db').get(_id=mongo_id)

                # El resto sigue igual...
                valoracion_existente = Valoracion.objects.using('mongo_db').filter(
                    equipo=equipo,
                    usuario_id=request.user.id
                ).first()

                if valoracion_existente:
                    valoracion_existente.puntuacion = int(puntos)
                    valoracion_existente.comentario = comentario
                    valoracion_existente.save()
                    messages.success(request, f"Has actualizado tu valoración para {equipo.nombre}")
                else:
                    Valoracion.objects.using('mongo_db').create(
                        equipo=equipo,
                        usuario_id=request.user.id,
                        puntuacion=int(puntos),
                        comentario=comentario
                    )
                    messages.success(request, f"Valoración enviada para {equipo.nombre}")

            except Exception as e:
                # Esto te ayudará a ver el error real si pasa algo más
                messages.error(request, f"Error al guardar: {e}")

        return redirect('valorar_equipos')

    # Parte GET (sin cambios, solo asegúrate de importar Team y Valoracion)
    equipos = Team.objects.using('mongo_db').all().order_by('nombre')

    for equipo in equipos:
        equipo.mi_valoracion = Valoracion.objects.using('mongo_db').filter(
            equipo=equipo,
            usuario_id=request.user.id
        ).first()

        if request.user.is_superuser:
            equipo.todas_valoraciones = Valoracion.objects.using('mongo_db').filter(equipo=equipo)
            notas = [v.puntuacion for v in equipo.todas_valoraciones]
            equipo.media_admin = sum(notas) / len(notas) if notas else 0

    return render(request, 'rankingWaterpolo/valorar_equipos.html', {'equipos': equipos})