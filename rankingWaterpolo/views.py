from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from bson import ObjectId  # Importante para MongoDB
import csv
import io

# Importamos tus modelos y formularios
from .models import Team, Ranking, Categoria, Valoracion
from .forms import CategoriaForm, CSVImportForm


# --- 1. AUTENTICACIÓN ---

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


# --- 2. HOME (Gestión y Visualización) ---

@login_required(login_url='login')
def home(request):
    section = request.GET.get('section', 'categorias')
    query = request.GET.get('q')

    # Filtro de categorías
    if query:
        categorias = Categoria.objects.using('mongo_db').filter(nombre__icontains=query)
    else:
        categorias = Categoria.objects.using('mongo_db').all()

    equipos = Team.objects.using('mongo_db').all()
    todas_vals = Valoracion.objects.using('mongo_db').all()

    # Estadísticas
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
        'section': section,
    }
    return render(request, 'rankingWaterpolo/home.html', context)


# --- 3. GESTIÓN DE CATEGORÍAS (DEBUGGING INTENSO) ---

@staff_member_required(login_url='home')
def crear_categoria(request):
    equipos_para_html = Team.objects.using('mongo_db').all().order_by('nombre')

    if request.method == 'POST':
        print("--- INICIO CREAR CATEGORIA (RELOAD BY NAME) ---")
        form = CategoriaForm(request.POST, request.FILES)

        # Validación especial: Si falla solo por 'equipos', lo ignoramos
        if not form.is_valid() and 'equipos' in form.errors and len(form.errors) == 1:
            pass  # Ignoramos error de equipos porque lo hacemos manual

        # Verificamos si el nombre es válido (lo más importante)
        if form.cleaned_data.get('nombre') and (form.is_valid() or ('equipos' in form.errors)):
            try:
                nombre_cat = form.cleaned_data.get('nombre')

                # 1. Guardamos la categoría (sin commit si es necesario para asignar user)
                categoria_guardada = form.save(commit=False)
                if hasattr(categoria_guardada, 'user'):
                    categoria_guardada.user = request.user

                categoria_guardada.save(using='mongo_db')
                print(f"DEBUG: Categoría guardada inicialmente.")

                # --- 2. EL CAMBIO CLAVE: RECARGA SEGURA ---
                # En lugar de refresh_from_db(), la buscamos por su NOMBRE único.
                # Esto nos da el ObjectId real (6995...) sin fallar.
                try:
                    categoria_real = Categoria.objects.using('mongo_db').get(nombre=nombre_cat)
                    print(f"DEBUG: Recarga exitosa. ID Real: {categoria_real.pk}")
                except Exception as e:
                    # Si falla esto, es gravísimo, pero usaremos lo que tengamos
                    print(f"DEBUG: Falló la recarga por nombre: {e}")
                    categoria_real = categoria_guardada

                # 3. Vincular Equipos
                ids_equipos_seleccionados = request.POST.getlist('equipos')
                conteo = 0

                if ids_equipos_seleccionados:
                    for id_str in ids_equipos_seleccionados:
                        try:
                            # Buscamos equipo por ID
                            if ObjectId.is_valid(id_str):
                                equipo = Team.objects.using('mongo_db').get(pk=ObjectId(id_str))
                            else:
                                equipo = Team.objects.using('mongo_db').get(pk=id_str)

                            # Asignamos la categoría RECARGADA (la que tiene el ID bueno)
                            equipo.categoria = categoria_real
                            equipo.save(using='mongo_db')
                            conteo += 1
                        except Exception as e:
                            print(f"DEBUG: Error asignando equipo {id_str}: {e}")

                messages.success(request, f"Categoría '{categoria_real.nombre}' creada y {conteo} equipos vinculados.")
                return redirect('home')

            except Exception as e:
                print(f"DEBUG: ERROR CRÍTICO GUARDANDO: {e}")
                messages.error(request, f"Error del sistema: {e}")
        else:
            print(f"DEBUG: Formulario inválido: {form.errors}")
            # Mensaje específico si el nombre ya existe
            if 'nombre' in form.errors:
                messages.error(request, f"Error: {form.errors['nombre'][0]}")
            else:
                messages.error(request, "Revisa los datos del formulario.")

    else:
        form = CategoriaForm()

    return render(request, 'rankingWaterpolo/crear_categoria.html', {
        'form': form,
        'equipos': equipos_para_html
    })

# --- 4. RANKINGS (SOLUCIÓN FORENSE / MANUAL) ---

@login_required(login_url='login')
def crear_ranking(request, categoria_id=None):
    categoria_objetivo = None
    equipos = []

    # --- FASE 1: OBTENER EQUIPOS ---
    if categoria_id:
        # A) Buscar la Categoría Objetivo
        try:
            if ObjectId.is_valid(categoria_id):
                categoria_objetivo = Categoria.objects.using('mongo_db').filter(_id=ObjectId(categoria_id)).first()

            if not categoria_objetivo:
                # Intento secundario por ID normal
                categoria_objetivo = Categoria.objects.using('mongo_db').filter(pk=categoria_id).first()
        except Exception as e:
            print(f"Error buscando categoría: {e}")

        if categoria_objetivo:
            target_name = categoria_objetivo.nombre

            # B) Cargar TODO para evitar errores de "Identidad Disociada" de Mongo/Django
            # Esto es necesario porque algunos equipos pueden tener ID numérico (31) y otros ObjectId.
            todas_las_cats = list(Categoria.objects.using('mongo_db').all())
            todos_los_equipos = Team.objects.using('mongo_db').all()

            for e in todos_los_equipos:
                try:
                    # Obtenemos el ID crudo saltándonos a Django
                    raw_cat_id = e.__dict__.get('categoria_id')

                    if not raw_cat_id:
                        continue

                        # Buscamos manualmente la categoría padre de este equipo
                    cat_del_equipo = None
                    for cat in todas_las_cats:
                        # Comprobamos si coincide con el ObjectId o con el ID int
                        if str(cat.pk) == str(raw_cat_id) or (hasattr(cat, 'id') and str(cat.id) == str(raw_cat_id)):
                            cat_del_equipo = cat
                            break

                    # Si encontramos al padre, verificamos si es la categoría que estamos viendo (por nombre)
                    if cat_del_equipo and cat_del_equipo.nombre == target_name:
                        equipos.append(e)

                except Exception as ex:
                    continue

            if not equipos:
                messages.warning(request, f"Categoría '{target_name}' encontrada, pero no tiene equipos vinculados.")
        else:
            messages.error(request, "Categoría no encontrada.")
            return redirect('home')
    else:
        # Si no hay ID, mostramos todos (Ranking General)
        equipos = Team.objects.using('mongo_db').all()

    # --- FASE 2: GUARDAR RANKING (POST) ---
    if request.method == 'POST':
        p1 = request.POST.get('posicion_1')
        p2 = request.POST.get('posicion_2')
        p3 = request.POST.get('posicion_3')
        p4 = request.POST.get('posicion_4')
        p5 = request.POST.get('posicion_5')
        titulo = request.POST.get('titulo')

        if all([p1, p2, p3, p4, p5, titulo]):
            try:
                Ranking.objects.using('mongo_db').create(
                    user_id=request.user.id,
                    username=request.user.username,
                    categoria=categoria_objetivo,  # Puede ser None si es general
                    nombre=titulo,
                    posicion_1_id=p1, posicion_2_id=p2, posicion_3_id=p3,
                    posicion_4_id=p4, posicion_5_id=p5
                )
                messages.success(request, "¡Ranking creado con éxito!")
                return redirect('mis_rankings')
            except Exception as e:
                messages.error(request, f"Error al guardar: {e}")
        else:
            messages.error(request, "Por favor, completa todos los campos.")

    return render(request, 'rankingWaterpolo/crear_top5.html', {
        'equipos': equipos,
        'categoria': categoria_objetivo
    })

@login_required(login_url='login')
def mis_rankings(request):
    rankings = Ranking.objects.using('mongo_db') \
        .filter(user_id=request.user.id) \
        .order_by('-fecha_creacion')

    for ranking in rankings:
        ranking.lista_equipos = []
        ids = [ranking.posicion_1_id, ranking.posicion_2_id, ranking.posicion_3_id, ranking.posicion_4_id,
               ranking.posicion_5_id]

        for id_str in ids:
            if not id_str: continue
            eq = None
            try:
                if ObjectId.is_valid(id_str):
                    eq = Team.objects.using('mongo_db').filter(pk=ObjectId(id_str)).first()
                if not eq:
                    eq = Team.objects.using('mongo_db').filter(nombre=id_str).first()
            except:
                pass

            if eq: ranking.lista_equipos.append(eq)

    return render(request, 'rankingWaterpolo/mis_rankings.html', {'rankings': rankings})


# --- 5. OTRAS FUNCIONES ---

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

                val = Valoracion.objects.using('mongo_db').filter(equipo=equipo, usuario_id=request.user.id).first()
                if val:
                    val.puntuacion = int(puntos)
                    val.comentario = comentario
                    val.save()
                else:
                    Valoracion.objects.using('mongo_db').create(
                        equipo=equipo, usuario_id=request.user.id, puntuacion=int(puntos), comentario=comentario
                    )
                messages.success(request, f"Valorado: {equipo.nombre}")
            except Exception as e:
                messages.error(request, f"Error: {e}")
        return redirect('valorar_equipos')

    equipos = Team.objects.using('mongo_db').all().order_by('nombre')
    for equipo in equipos:
        equipo.mi_valoracion = Valoracion.objects.using('mongo_db').filter(equipo=equipo,
                                                                           usuario_id=request.user.id).first()

    return render(request, 'rankingWaterpolo/valorar_equipos.html', {'equipos': equipos})


@staff_member_required(login_url='home')
def importar_equipos_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo_csv']
            data_set = archivo.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)

            conteo = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                try:
                    nombre_equipo = row[0]
                    cat_obj = None
                    if len(row) > 7 and row[7]:
                        cat_obj = Categoria.objects.using('mongo_db').filter(nombre=row[7]).first()

                    Team.objects.using('mongo_db').create(
                        nombre=nombre_equipo,
                        escudo=row[1] if row[1] else "",
                        liga=row[2] if len(row) > 2 else "",
                        sexo=row[3] if len(row) > 3 else "",
                        entrenador=row[4] if len(row) > 4 else "",
                        piscina=row[5] if len(row) > 5 else "",
                        ciudad=row[6] if len(row) > 6 else "",
                        categoria=cat_obj
                    )
                    conteo += 1
                except:
                    continue

            messages.success(request, f"¡Éxito! {conteo} equipos importados.")
            return redirect('home')
    return redirect('home')