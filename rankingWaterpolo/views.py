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
from .forms import CategoriaForm, CSVImportForm, ValoracionForm


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

    print(f"--- DEBUG HOME --- Seccion: {section}, Query: {query}")

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
        # Usamos equipo.pk o _id para filtrar valoraciones en Mongo
        vals_equipo = Valoracion.objects.using('mongo_db').filter(equipo_id=equipo.pk)
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
            pass

            # Verificamos si el nombre es válido
        if form.cleaned_data.get('nombre') and (form.is_valid() or ('equipos' in form.errors)):
            try:
                nombre_cat = form.cleaned_data.get('nombre')

                # 1. Guardamos la categoría
                categoria_guardada = form.save(commit=False)
                # No asignamos user si el modelo Categoria no tiene campo 'user'
                categoria_guardada.save(using='mongo_db')
                print(f"DEBUG: Categoría '{nombre_cat}' guardada inicialmente.")

                # --- 2. RECARGA SEGURA POR NOMBRE ---
                try:
                    categoria_real = Categoria.objects.using('mongo_db').get(nombre=nombre_cat)
                    print(f"DEBUG: Recarga exitosa. ID Real: {categoria_real.pk}")
                except Exception as e:
                    print(f"DEBUG: Falló la recarga por nombre: {e}")
                    categoria_real = categoria_guardada

                # 3. Vincular Equipos
                ids_equipos_seleccionados = request.POST.getlist('equipos')
                conteo = 0

                if ids_equipos_seleccionados:
                    for id_str in ids_equipos_seleccionados:
                        try:
                            # Buscamos equipo por ID manejando ObjectId
                            oid = ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str
                            equipo = Team.objects.using('mongo_db').get(pk=oid)

                            # Asignamos la categoría RECARGADA
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
    if request.user.is_staff:
        messages.warning(request, "Los administradores no pueden crear rankings, solo supervisarlos.")
        return redirect('home')

    categoria_objetivo = None
    equipos = []

    if categoria_id:
        try:
            oid = ObjectId(categoria_id) if ObjectId.is_valid(categoria_id) else categoria_id
            categoria_objetivo = Categoria.objects.using('mongo_db').filter(pk=oid).first()

            if categoria_objetivo:
                # COMPROBACIÓN: ¿Ya tiene un ranking en esta categoría?
                ranking_existente = Ranking.objects.using('mongo_db').filter(
                    user_id=request.user.id,
                    categoria_id=categoria_objetivo.pk
                ).first()

                if ranking_existente:
                    messages.info(request, "Ya tienes un ranking en esta categoría. Puedes editarlo aquí.")
                    return redirect('editar_ranking', ranking_id=str(ranking_existente.pk))

                equipos = list(Team.objects.using('mongo_db').filter(categoria_id=categoria_objetivo.pk))
        except Exception as e:
            pass
    else:
        equipos = list(Team.objects.using('mongo_db').all())

    if request.method == 'POST':
        p1, p2, p3, p4, p5 = [request.POST.get(f'posicion_{i}') for i in range(1, 6)]
        titulo = request.POST.get('titulo')

        if all([p1, p2, p3, p4, p5, titulo]):
            try:
                ranking_nuevo = Ranking(
                    user_id=request.user.id,
                    username=request.user.username,
                    categoria_id=categoria_objetivo.pk if categoria_objetivo else None,
                    nombre=titulo,
                    posicion_1_id=str(p1), posicion_2_id=str(p2),
                    posicion_3_id=str(p3), posicion_4_id=str(p4), posicion_5_id=str(p5),
                )
                ranking_nuevo.save(using='mongo_db')
                messages.success(request, "¡Ranking creado con éxito!")
                return redirect('mis_rankings')
            except Exception as e:
                messages.error(request, f"Error al guardar ranking: {e}")
        else:
            messages.error(request, "Por favor, completa todos los campos.")

    return render(request, 'rankingWaterpolo/crear_top5.html', {
        'equipos': equipos,
        'categoria': categoria_objetivo
    })

@login_required(login_url='login')
def editar_ranking(request, ranking_id):
    if request.user.is_staff:
        return redirect('home')

    try:
        oid = ObjectId(ranking_id) if ObjectId.is_valid(ranking_id) else ranking_id
        ranking = Ranking.objects.using('mongo_db').get(pk=oid)
    except Exception:
        messages.error(request, "Ranking no encontrado.")
        return redirect('mis_rankings')

    # Seguridad: solo el dueño puede editarlo
    if ranking.user_id != request.user.id:
        messages.error(request, "No tienes permiso para editar este ranking.")
        return redirect('mis_rankings')

    categoria_objetivo = ranking.categoria
    if categoria_objetivo:
        equipos = list(Team.objects.using('mongo_db').filter(categoria_id=categoria_objetivo.pk))
    else:
        equipos = list(Team.objects.using('mongo_db').all())

    if request.method == 'POST':
        p1, p2, p3, p4, p5 = [request.POST.get(f'posicion_{i}') for i in range(1, 6)]
        titulo = request.POST.get('titulo')

        if all([p1, p2, p3, p4, p5, titulo]):
            ranking.nombre = titulo
            ranking.posicion_1_id = str(p1)
            ranking.posicion_2_id = str(p2)
            ranking.posicion_3_id = str(p3)
            ranking.posicion_4_id = str(p4)
            ranking.posicion_5_id = str(p5)
            ranking.save(using='mongo_db')
            messages.success(request, "¡Ranking actualizado correctamente!")
            return redirect('mis_rankings')
        else:
            messages.error(request, "Completa todos los campos.")

    return render(request, 'rankingWaterpolo/crear_top5.html', {
        'equipos': equipos,
        'categoria': categoria_objetivo,
        'ranking_edit': ranking # Pasamos el ranking para precargar los datos
    })


@staff_member_required(login_url='home')
def estadisticas_globales(request):
    # 1. Obtenemos todos los datos crudos en listas de Python para evitar fallos de Mongo/Djongo
    todas_vals = list(Valoracion.objects.using('mongo_db').all())
    todos_equipos = list(Team.objects.using('mongo_db').all())
    todas_categorias = list(Categoria.objects.using('mongo_db').all())

    total_valoraciones = len(todas_vals)

    # 2. Calcular Equipos Más Valorados (Media y Cantidad)
    equipos_stats = []
    for eq in todos_equipos:
        vals = [v for v in todas_vals if v.equipo_id == eq.pk]
        if vals:
            media = sum(v.puntuacion for v in vals) / len(vals)
            equipos_stats.append({
                'equipo': eq,
                'media': round(media, 1),
                'num_vals': len(vals)
            })

    # Ordenar por media de mayor a menor y quedarnos con el TOP 10
    equipos_stats.sort(key=lambda x: x['media'], reverse=True)
    top_equipos = equipos_stats[:10]

    # 3. Promedio por Categoría
    cat_stats = []
    for cat in todas_categorias:
        # Equipos que pertenecen a esta categoría
        eqs_cat_ids = [eq.pk for eq in todos_equipos if eq.categoria_id == cat.pk]
        # Valoraciones de esos equipos
        vals_cat = [v for v in todas_vals if v.equipo_id in eqs_cat_ids]

        if vals_cat:
            media_cat = sum(v.puntuacion for v in vals_cat) / len(vals_cat)
            cat_stats.append({
                'categoria': cat,
                'media': round(media_cat, 1),
                'total_votos': len(vals_cat),
                'total_equipos': len(eqs_cat_ids)
            })

    # Ordenar categorías por puntuación
    cat_stats.sort(key=lambda x: x['media'], reverse=True)

    return render(request, 'rankingWaterpolo/estadisticas.html', {
        'total_valoraciones': total_valoraciones,
        'top_equipos': top_equipos,
        'cat_stats': cat_stats
    })


@login_required(login_url='login')
def mis_rankings(request):
    print("🚀 Inicio de mis_rankings")

    # 1. LOGICA DE PERMISOS
    try:
        if request.user.is_staff:
            print("👑 Usuario staff: cargando todos los rankings")
            rankings = list(Ranking.objects.using('mongo_db').all())
        else:
            print("👤 Usuario normal: cargando solo sus rankings")
            rankings = list(Ranking.objects.using('mongo_db').filter(user_id=request.user.id))

        # Ordenación manual por fecha
        rankings.sort(key=lambda r: r.fecha_creacion if r.fecha_creacion else 0, reverse=True)
        print(f"✅ {len(rankings)} rankings cargados")
    except Exception as e:
        print(f"❌ ERROR al cargar rankings: {e}")
        rankings = []

    # 2. HIDRATAR LOS RANKINGS (Cargar objetos Team desde los IDs guardados)
    for ranking in rankings:
        print(f"🔹 Procesando ranking: {ranking.nombre}")
        ranking.lista_equipos = []
        ids_guardados = [
            ranking.posicion_1_id, ranking.posicion_2_id,
            ranking.posicion_3_id, ranking.posicion_4_id,
            ranking.posicion_5_id
        ]

        for i, id_str in enumerate(ids_guardados, start=1):
            if not id_str: continue

            equipo_encontrado = None
            try:
                oid = ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str
                equipo_encontrado = Team.objects.using('mongo_db').filter(pk=oid).first()
            except Exception as e:
                print(f"❌ ERROR buscando equipo {id_str}: {e}")

            if equipo_encontrado:
                ranking.lista_equipos.append(equipo_encontrado)

    print("🏁 Fin de mis_rankings")
    return render(request, 'rankingWaterpolo/mis_rankings.html', {
        'rankings': rankings
    })


# --- 5. OTRAS FUNCIONES ---

@login_required(login_url='login')
def valorar_equipos(request):
    if request.method == 'POST':
        # ... (el código del POST se queda igual)
        team_id = request.POST.get('team_id')
        puntos = request.POST.get('puntuacion')
        comentario = request.POST.get('comentario')
        if team_id and puntos:
            try:
                oid = ObjectId(team_id) if ObjectId.is_valid(team_id) else team_id
                equipo = Team.objects.using('mongo_db').get(pk=oid)
                val, created = Valoracion.objects.using('mongo_db').update_or_create(
                    equipo_id=equipo.pk,
                    usuario_id=request.user.id,
                    defaults={'puntuacion': int(puntos), 'comentario': comentario}
                )
                messages.success(request, f"Valorado: {equipo.nombre}")
            except Exception as e:
                print(f"❌ ERROR valoración: {e}")
        return redirect('valorar_equipos')

    # --- CAMBIO AQUÍ: Quitamos el .order_by() de la base de datos ---
    equipos_list = list(Team.objects.using('mongo_db').all())
    # Ordenamos con Python para que Djongo no explote
    equipos_list.sort(key=lambda x: x.nombre.lower())

    for equipo in equipos_list:
        # LÓGICA DIVIDIDA POR ROLES
        if request.user.is_staff or request.user.is_superuser:
            # 1. MODO ADMIN: Obtener todas las valoraciones de este equipo
            vals_equipo = list(Valoracion.objects.using('mongo_db').filter(equipo_id=equipo.pk))
            equipo.todas_valoraciones = vals_equipo

            # Calcular la media manualmente por seguridad en Mongo
            if len(vals_equipo) > 0:
                media = sum(v.puntuacion for v in vals_equipo) / len(vals_equipo)
                equipo.media_admin = round(media, 1)
            else:
                equipo.media_admin = 0.0

        else:
            # 2. MODO USUARIO NORMAL: Obtener solo la suya
            equipo.mi_valoracion = Valoracion.objects.using('mongo_db').filter(
                equipo_id=equipo.pk,
                usuario_id=request.user.id
            ).first()

    return render(request, 'rankingWaterpolo/valorar_equipos.html', {'equipos': equipos_list})


@staff_member_required(login_url='home')
def importar_equipos_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo_csv']
            try:
                data_set = archivo.read().decode('UTF-8')
                io_string = io.StringIO(data_set)
                next(io_string)  # Saltar cabecera

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
                    except Exception as e:
                        print(f"⚠️ Error en fila CSV: {e}")
                        continue

                messages.success(request, f"¡Éxito! {conteo} equipos importados.")
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {e}")
    return redirect('home')


@staff_member_required(login_url='home')
def editar_categoria(request, categoria_id):
    # 1. Buscar la categoría por su ObjectId de Mongo
    try:
        oid = ObjectId(categoria_id) if ObjectId.is_valid(categoria_id) else categoria_id
        categoria = Categoria.objects.using('mongo_db').get(pk=oid)
    except Exception as e:
        messages.error(request, "Categoría no encontrada.")
        return redirect('home')

    # 2. Cargar todos los equipos y los que ya pertenecen a esta categoría
    # (Al estar en Django 3.1, ordenamos con Python por seguridad)
    todos_los_equipos = list(Team.objects.using('mongo_db').all())
    todos_los_equipos.sort(key=lambda x: x.nombre.lower())

    equipos_actuales = Team.objects.using('mongo_db').filter(categoria=categoria)
    ids_actuales = [str(eq.pk) for eq in equipos_actuales]

    # 3. Procesar el formulario cuando el admin le da a Guardar
    if request.method == 'POST':
        nuevo_nombre = request.POST.get('nombre')
        equipos_seleccionados = request.POST.getlist('equipos')  # IDs que el admin ha marcado

        # Actualizamos el nombre si ha cambiado
        if nuevo_nombre and nuevo_nombre != categoria.nombre:
            categoria.nombre = nuevo_nombre
            categoria.save(using='mongo_db')

        # A) Desvincular equipos que el admin ha desmarcado
        for equipo in equipos_actuales:
            if str(equipo.pk) not in equipos_seleccionados:
                equipo.categoria = None
                equipo.save(using='mongo_db')

        # B) Vincular los equipos que el admin ha marcado
        if equipos_seleccionados:
            for id_str in equipos_seleccionados:
                # Solo actualizamos si no estaba ya en la categoría para ahorrar consultas
                if id_str not in ids_actuales:
                    try:
                        eq_oid = ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str
                        equipo_a_vincular = Team.objects.using('mongo_db').get(pk=eq_oid)
                        equipo_a_vincular.categoria = categoria
                        equipo_a_vincular.save(using='mongo_db')
                    except Exception as e:
                        print(f"⚠️ Error vinculando equipo {id_str}: {e}")

        messages.success(request, f"Categoría '{categoria.nombre}' actualizada con éxito.")
        return redirect('home')

    return render(request, 'rankingWaterpolo/editar_categoria.html', {
        'categoria': categoria,
        'todos_los_equipos': todos_los_equipos,
        'equipos_actuales_ids': ids_actuales
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required


# 1. Ver la lista de usuarios
@staff_member_required  # Esto protege la vista para que solo entre el staff/admin
def gestionar_usuarios(request):
    # Traemos todos los usuarios, ordenados para que los superadmins salgan primero
    usuarios = User.objects.all().order_by('-is_superuser', '-is_active', 'username')
    return render(request, 'rankingWaterpolo/gestionar_usuarios.html', {'usuarios': usuarios})


# 2. Editar un usuario
@staff_member_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':
        # Recogemos los datos del formulario a mano (es más rápido que crear un forms.py)
        usuario.username = request.POST.get('username')
        usuario.email = request.POST.get('email')

        # Los checkboxes en HTML devuelven 'on' si están marcados
        usuario.is_active = request.POST.get('is_active') == 'on'
        usuario.is_staff = request.POST.get('is_staff') == 'on'
        usuario.is_superuser = request.POST.get('is_superuser') == 'on'

        usuario.save()
        messages.success(request, f'Usuario {usuario.username} actualizado correctamente.')
        return redirect('gestionar_usuarios')

    # Le pasamos el usuario a la plantilla con el nombre 'usuario_edit'
    return render(request, 'rankingWaterpolo/editar_usuario.html', {'usuario_edit': usuario})


# 3. Eliminar un usuario
@staff_member_required
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)

    # Doble check de seguridad: no te puedes borrar a ti mismo
    if request.user.id != usuario.id:
        usuario.delete()
        messages.success(request, 'Usuario eliminado para siempre.')
    else:
        messages.error(request, '¡Ey! No puedes eliminarte a ti mismo.')

    return redirect('gestionar_usuarios')


@staff_member_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')  # ¡Campo nuevo!
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'

        # Validación básica: comprobar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Error: El nombre de usuario ya está pillado.')
            return render(request, 'rankingWaterpolo/crear_usuario.html')

        # Crear el usuario con contraseña encriptada
        nuevo_usuario = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Asignar permisos y estado
        nuevo_usuario.is_active = is_active
        nuevo_usuario.is_staff = is_staff
        nuevo_usuario.is_superuser = is_superuser
        nuevo_usuario.save()

        messages.success(request, f'Usuario "{username}" creado correctamente.')
        return redirect('gestionar_usuarios')

    return render(request, 'rankingWaterpolo/crear_usuario.html')