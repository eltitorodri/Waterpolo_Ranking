from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from bson import ObjectId
import csv
import io

from .models import Team, Ranking, Categoria, Valoracion
from .forms import CategoriaForm, CSVImportForm, ValoracionForm



from django.contrib.auth.models import User


def registro(request):
    if request.method == 'POST':
        username_str = request.POST.get('username')
        email_str = request.POST.get('email')
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('confirm_password')


        if pass1 != pass2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'rankingWaterpolo/signup.html')

        if User.objects.filter(username=username_str).exists():
            messages.error(request, "Ese NICKNAME ya está pillado.")
            return render(request, 'rankingWaterpolo/signup.html')


        try:
            nuevo_usuario = User.objects.create_user(
                username=username_str,
                email=email_str,
                password=pass1
            )

            login(request, nuevo_usuario)
            messages.success(request, f"¡Bienvenido a la piscina, {nuevo_usuario.username}!")
            return redirect('home')

        except Exception as e:
            messages.error(request, f"Error al crear la cuenta: {e}")
            return render(request, 'rankingWaterpolo/signup.html')


    return render(request, 'rankingWaterpolo/signup.html')


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




@login_required(login_url='login')
def home(request):
    section = request.GET.get('section', 'categorias')
    query = request.GET.get('q')

    print(f"--- DEBUG HOME --- Seccion: {section}, Query: {query}")


    if query:
        categorias = Categoria.objects.using('mongo_db').filter(nombre__icontains=query)
    else:
        categorias = Categoria.objects.using('mongo_db').all()

    equipos = Team.objects.using('mongo_db').all()
    todas_vals = Valoracion.objects.using('mongo_db').all()


    total_valoraciones = todas_vals.count()
    mejor_equipo = None
    max_media = -1

    for equipo in equipos:

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


@staff_member_required(login_url='home')
def crear_categoria(request):
    equipos_para_html = Team.objects.using('mongo_db').all().order_by('nombre')

    if request.method == 'POST':
        print("--- INICIO CREAR CATEGORIA (RELOAD BY NAME) ---")
        form = CategoriaForm(request.POST, request.FILES)


        if not form.is_valid() and 'equipos' in form.errors and len(form.errors) == 1:
            pass


        if form.cleaned_data.get('nombre') and (form.is_valid() or ('equipos' in form.errors)):
            try:
                nombre_cat = form.cleaned_data.get('nombre')


                categoria_guardada = form.save(commit=False)

                categoria_guardada.save(using='mongo_db')
                print(f"DEBUG: Categoría '{nombre_cat}' guardada inicialmente.")


                try:
                    categoria_real = Categoria.objects.using('mongo_db').get(nombre=nombre_cat)
                    print(f"DEBUG: Recarga exitosa. ID Real: {categoria_real.pk}")
                except Exception as e:
                    print(f"DEBUG: Falló la recarga por nombre: {e}")
                    categoria_real = categoria_guardada


                ids_equipos_seleccionados = request.POST.getlist('equipos')
                conteo = 0

                if ids_equipos_seleccionados:
                    for id_str in ids_equipos_seleccionados:
                        try:

                            oid = ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str
                            equipo = Team.objects.using('mongo_db').get(pk=oid)

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
        'ranking_edit': ranking
    })


@staff_member_required(login_url='home')
def estadisticas_globales(request):

    todas_vals = list(Valoracion.objects.using('mongo_db').all())
    todos_equipos = list(Team.objects.using('mongo_db').all())
    todas_categorias = list(Categoria.objects.using('mongo_db').all())

    total_valoraciones = len(todas_vals)


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


    equipos_stats.sort(key=lambda x: x['media'], reverse=True)
    top_equipos = equipos_stats[:10]


    cat_stats = []
    for cat in todas_categorias:

        eqs_cat_ids = [eq.pk for eq in todos_equipos if eq.categoria_id == cat.pk]

        vals_cat = [v for v in todas_vals if v.equipo_id in eqs_cat_ids]

        if vals_cat:
            media_cat = sum(v.puntuacion for v in vals_cat) / len(vals_cat)
            cat_stats.append({
                'categoria': cat,
                'media': round(media_cat, 1),
                'total_votos': len(vals_cat),
                'total_equipos': len(eqs_cat_ids)
            })


    cat_stats.sort(key=lambda x: x['media'], reverse=True)

    return render(request, 'rankingWaterpolo/estadisticas.html', {
        'total_valoraciones': total_valoraciones,
        'top_equipos': top_equipos,
        'cat_stats': cat_stats
    })


@login_required(login_url='login')
def mis_rankings(request):
    print("🚀 Inicio de mis_rankings")


    try:
        if request.user.is_staff:
            print("👑 Usuario staff: cargando todos los rankings")
            rankings = list(Ranking.objects.using('mongo_db').all())
        else:
            print("👤 Usuario normal: cargando solo sus rankings")
            rankings = list(Ranking.objects.using('mongo_db').filter(user_id=request.user.id))


        rankings.sort(key=lambda r: r.fecha_creacion if r.fecha_creacion else 0, reverse=True)
        print(f"✅ {len(rankings)} rankings cargados")
    except Exception as e:
        print(f"❌ ERROR al cargar rankings: {e}")
        rankings = []


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




@login_required(login_url='login')
def valorar_equipos(request):
    if request.method == 'POST':

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


    equipos_list = list(Team.objects.using('mongo_db').all())
    equipos_list.sort(key=lambda x: x.nombre.lower())

    for equipo in equipos_list:

        if request.user.is_staff or request.user.is_superuser:
            vals_equipo = list(Valoracion.objects.using('mongo_db').filter(equipo_id=equipo.pk))
            equipo.todas_valoraciones = vals_equipo


            if len(vals_equipo) > 0:
                media = sum(v.puntuacion for v in vals_equipo) / len(vals_equipo)
                equipo.media_admin = round(media, 1)
            else:
                equipo.media_admin = 0.0

        else:

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
                    except Exception as e:
                        print(f"⚠️ Error en fila CSV: {e}")
                        continue

                messages.success(request, f"¡Éxito! {conteo} equipos importados.")
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {e}")
    return redirect('home')


@staff_member_required(login_url='home')
def editar_categoria(request, categoria_id):
    try:
        oid = ObjectId(categoria_id) if ObjectId.is_valid(categoria_id) else categoria_id
        categoria = Categoria.objects.using('mongo_db').get(pk=oid)
    except Exception as e:
        messages.error(request, "Categoría no encontrada.")
        return redirect('home')

    todos_los_equipos = list(Team.objects.using('mongo_db').all())
    todos_los_equipos.sort(key=lambda x: x.nombre.lower())

    equipos_actuales = Team.objects.using('mongo_db').filter(categoria=categoria)
    ids_actuales = [str(eq.pk) for eq in equipos_actuales]

    if request.method == 'POST':
        nuevo_nombre = request.POST.get('nombre')
        equipos_seleccionados = request.POST.getlist('equipos')


        if nuevo_nombre and nuevo_nombre != categoria.nombre:
            categoria.nombre = nuevo_nombre
            categoria.save(using='mongo_db')

        for equipo in equipos_actuales:
            if str(equipo.pk) not in equipos_seleccionados:
                equipo.categoria = None
                equipo.save(using='mongo_db')

        if equipos_seleccionados:
            for id_str in equipos_seleccionados:

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



@staff_member_required
def gestionar_usuarios(request):

    usuarios = User.objects.all().order_by('-is_superuser', '-is_active', 'username')
    return render(request, 'rankingWaterpolo/gestionar_usuarios.html', {'usuarios': usuarios})



@staff_member_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':

        usuario.username = request.POST.get('username')
        usuario.email = request.POST.get('email')


        usuario.is_active = request.POST.get('is_active') == 'on'
        usuario.is_staff = request.POST.get('is_staff') == 'on'
        usuario.is_superuser = request.POST.get('is_superuser') == 'on'

        usuario.save()
        messages.success(request, f'Usuario {usuario.username} actualizado correctamente.')
        return redirect('gestionar_usuarios')


    return render(request, 'rankingWaterpolo/editar_usuario.html', {'usuario_edit': usuario})


@staff_member_required
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)


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
        password = request.POST.get('password')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Error: El nombre de usuario ya está pillado.')
            return render(request, 'rankingWaterpolo/crear_usuario.html')

        nuevo_usuario = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        nuevo_usuario.is_active = is_active
        nuevo_usuario.is_staff = is_staff
        nuevo_usuario.is_superuser = is_superuser
        nuevo_usuario.save()

        messages.success(request, f'Usuario "{username}" creado correctamente.')
        return redirect('gestionar_usuarios')

    return render(request, 'rankingWaterpolo/crear_usuario.html')


from django.contrib.admin.views.decorators import staff_member_required
from bson import ObjectId


@staff_member_required(login_url='home')
def explorar_equipos(request):
    query = request.GET.get('q', '').strip()
    categoria_filtro = request.GET.get('categoria', '')

    todos_equipos = list(Team.objects.using('mongo_db').all())
    categorias = list(Categoria.objects.using('mongo_db').all())

    if query:
        todos_equipos = [eq for eq in todos_equipos if query.lower() in eq.nombre.lower()]

    if categoria_filtro:
        todos_equipos = [eq for eq in todos_equipos if str(eq.categoria_id) == str(categoria_filtro)]

    return render(request, 'rankingWaterpolo/explorar_equipos.html', {
        'equipos': todos_equipos,
        'categorias': categorias,
        'query': query,
        'categoria_filtro': str(categoria_filtro)
    })

@staff_member_required(login_url='home')
def eliminar_categoria(request, categoria_id):
    try:
        oid = ObjectId(categoria_id) if ObjectId.is_valid(categoria_id) else categoria_id
        categoria = Categoria.objects.using('mongo_db').get(pk=oid)
        nombre_cat = categoria.nombre

        categoria.delete(using='mongo_db')
        messages.success(request, f"🗑️ La categoría '{nombre_cat}' ha sido eliminada.")

    except Exception as e:
        messages.error(request, f"Error al eliminar la categoría: {e}")

    return redirect('/?section=gestion')