from django.urls import path
from . import views
# --- NUEVAS IMPORTACIONES PARA IMÁGENES ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('home/', views.home, name='home'),
    path('', views.home, name='index'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro, name='registro'),

    path('crear-ranking/', views.crear_ranking, name='crear_top5'),
    path('crear-ranking/<str:categoria_id>/', views.crear_ranking, name='crear_ranking_categoria'),

    path('mis-rankings/', views.mis_rankings, name='mis_rankings'),
    path('valorar-equipos/', views.valorar_equipos, name='valorar_equipos'),
    path('crear-categoria/', views.crear_categoria, name='crear_categoria'),
    path('importar-equipos-csv/', views.importar_equipos_csv, name='importar_equipos_csv'),
    path('editar-categoria/<str:categoria_id>/', views.editar_categoria, name='editar_categoria'),

    path('gestionar-usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('editar-usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('eliminar-usuario/<int:usuario_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('crear-usuario/', views.crear_usuario, name='crear_usuario'),

    path('estadisticas/', views.estadisticas_globales, name='estadisticas'),
    path('editar-ranking/<str:ranking_id>/', views.editar_ranking, name='editar_ranking'),

    path('explorar/', views.explorar_equipos, name='explorar_equipos'),
    path('categoria/eliminar/<str:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)