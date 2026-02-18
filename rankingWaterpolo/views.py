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

@login_required(login_url='login')
def home(request):
    # Detectamos en qué sección estamos (por defecto: categorias)
    section = request.GET.get('section', 'categorias')

    query = request.GET.get('q')
    if query:
        categorias = Categoria.objects.using('mongo_db').filter(nombre__icontains=query)
    else:
        categorias = Categoria.objects.using('mongo_db').all()

    equipos = Team.objects.using('mongo_db').all()
    todas_vals = Valoracion.objects.using('mongo_db').all()

    # Lógica de estadísticas
    total_valoraciones = todas_vals.count()
    mejor_equipo = None
    max_media = -1

    for equipo in equipos:
        vals_equipo = Valoracion.objects.using('mongo_db').filter(equipo=equipo)
        if vals_equipo.exists():
            promedio = sum(v.puntuacion for v in vals_equipo) / vals_equipo.count()
            equipo.media_puntos = round(promedio, 1)
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
        'section': section,  # <-- Pasamos la sección actual al HTML
    }
    return render(request, 'rankingWaterpolo/home.html', context)


# --- 3. RANKINGS (Nuevo sistema con Categorías) ---

# --- PEGA ESTO EN TU VIEWS.PY QUE TE FALTA ---

@login_required(login_url='login')
def crear_ranking(request, categoria_id=None):
    categoria_obj = None
    equipos = []

    if categoria_id:
        # 1. BUSCAR LA CATEGORÍA
        try:
            if ObjectId.is_valid(categoria_id):
                categoria_obj = Categoria.objects.using('mongo_db').filter(_id=ObjectId(categoria_id)).first()
            if not categoria_obj:
                categoria_obj = Categoria.objects.using('mongo_db').filter(id=categoria_id).first()
        except:
            pass

        if categoria_obj:
            # 1. Obtenemos los dos posibles IDs de la categoría en formato STRING limpio
            id_largo = str(getattr(categoria_obj, '_id', '')).strip()
            id_corto = str(getattr(categoria_obj, 'id', '')).strip()

            ids_validos = [id_largo, id_corto]
            print(f"🎯 Buscando equipos con ID en: {ids_validos}")

            # 2. FILTRADO QUIRÚRGICO
            todos = Team.objects.using('mongo_db').all()
            for e in todos:
                # Extraemos el valor de categoria_id tal cual está en la base de datos
                # Usamos el diccionario interno para evitar que Django lo transforme
                val_raw = e.__dict__.get('categoria_id', None)

                if val_raw is not None:
                    # Convertimos a string y quitamos posibles espacios o caracteres raros
                    val_str = str(val_raw).strip()

                    # Comparación: ¿Está el ID del equipo en nuestra lista de permitidos?
                    if val_str in ids_validos:
                        equipos.append(e)

            print(f"✅ Filtro aplicado. Coincidencias encontradas: {len(equipos)}")
            # 3. FILTRADO ULTRA-RESISTENTE
            todos = Team.objects.using('mongo_db').all()
            for e in todos:
                # Sacamos el valor crudo del equipo
                val_equipo = str(e.__dict__.get('categoria_id', '')).strip()

                # Comparación flexible: si el ID del equipo está en nuestra lista de IDs válidos
                if val_equipo in [id_largo, id_corto] and val_equipo not in ['', 'None', 'None']:
                    equipos.append(e)

            # --- PLAN B: SI EL FILTRO SIGUE DANDO 0, MUESTRA TODOS ---
            if not equipos:
                print("⚠️ El filtro falló de nuevo. Cargando todos los equipos por seguridad.")
                equipos = todos
        else:
            messages.error(request, "Categoría no encontrada.")
            return redirect('home')
    else:
        equipos = Team.objects.using('mongo_db').all()

    # --- LÓGICA POST (Guardar) ---
    if request.method == 'POST':
        p1 = request.POST.get('posicion_1')
        p2 = request.POST.get('posicion_2')
        p3 = request.POST.get('posicion_3')
        p4 = request.POST.get('posicion_4')
        p5 = request.POST.get('posicion_5')
        titulo = request.POST.get('titulo')

        if all([p1, p2, p3, p4, p5, titulo]):
            Ranking.objects.using('mongo_db').create(
                user_id=request.user.id,
                username=request.user.username,
                categoria=categoria_obj,
                nombre=titulo,
                posicion_1_id=p1, posicion_2_id=p2, posicion_3_id=p3,
                posicion_4_id=p4, posicion_5_id=p5
            )
            messages.success(request, "¡Ranking creado!")
            return redirect('mis_rankings')

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
    # Traemos todos los equipos para pintarlos en el HTML
    equipos_para_html = Team.objects.using('mongo_db').all()

    if request.method == 'POST':
        form = CategoriaForm(request.POST, request.FILES)

        # Validación flexible para 'equipos' (Djongo a veces falla validando M2M)
        es_valido = form.is_valid()
        if not es_valido and 'equipos' in form.errors and len(form.errors) == 1:
            es_valido = True

        if es_valido:
            try:
                # 1. Guardar la Categoría
                if form.is_valid():
                    categoria_guardada = form.save()
                else:
                    obj = form.save(commit=False)
                    obj.save(using='mongo_db')
                    categoria_guardada = obj

                print(f"✅ Categoría guardada: {categoria_guardada.nombre} (ID: {categoria_guardada.pk})")

                # 2. Asignar equipos MANUALMENTE (Actualizamos el ForeignKey del Equipo)
                ids_equipos_seleccionados = request.POST.getlist('equipos')
                conteo = 0

                if ids_equipos_seleccionados:
                    for id_str in ids_equipos_seleccionados:
                        try:
                            # Buscamos el equipo y le asignamos esta categoría
                            equipo = Team.objects.using('mongo_db').get(pk=ObjectId(id_str))
                            equipo.categoria = categoria_guardada
                            equipo.save(using='mongo_db')
                            conteo += 1
                        except Exception as e:
                            print(f"⚠️ Error asignando equipo {id_str}: {e}")

                messages.success(request, f"Categoría '{categoria_guardada.nombre}' creada con {conteo} equipos.")
                return redirect('home')

            except Exception as e:
                print(f"❌ Error crítico: {e}")
                messages.error(request, f"Error interno: {e}")
        else:
            messages.error(request, "Revisa el formulario (Nombre repetido o falta imagen).")
            print(form.errors)

    else:
        form = CategoriaForm()

    return render(request, 'rankingWaterpolo/crear_categoria.html', {
        'form': form,
        'equipos': equipos_para_html
    })


import csv
import io
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CSVImportForm


@staff_member_required(login_url='home')
def importar_equipos_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo_csv']

            # Leer el archivo
            data_set = archivo.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Saltamos la cabecera si la tiene

            conteo = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                # Estructura esperada del CSV:
                # nombre, escudo, liga, sexo, entrenador, piscina, ciudad, nombre_categoria
                try:
                    nombre_equipo = row[0]
                    # Buscamos si existe la categoría para enlazarla
                    cat_obj = None
                    if len(row) > 7 and row[7]:
                        cat_obj = Categoria.objects.using('mongo_db').filter(nombre=row[7]).first()

                    Team.objects.using('mongo_db').create(
                        nombre=nombre_equipo,
                        escudo=row[1] if row[1] else "",
                        liga=row[2],
                        sexo=row[3],
                        entrenador=row[4],
                        piscina=row[5],
                        ciudad=row[6],
                        categoria=cat_obj
                    )
                    conteo += 1
                except Exception as e:
                    print(f"Error en fila {nombre_equipo}: {e}")
                    continue

            messages.success(request, f"¡Éxito! Se han importado {conteo} equipos correctamente.")
            return redirect('home')

    return redirect('home')