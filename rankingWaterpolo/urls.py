from django.urls import path
from . import views

urlpatterns = [
    # --- HOME ---
    # Esta es la que te estaba fallando: restauramos 'home/'
    path('home/', views.home, name='home'),
    # Dejo esta también para que si entran a 127.0.0.1:8000 directo, les lleve al home
    path('', views.home, name='index'),

    # --- AUTENTICACIÓN ---
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro, name='registro'),

    # --- RANKINGS (Con la lógica nueva de categorías) ---
    # URL 1: La general (ej: crear-top5/)
    path('crear-ranking/', views.crear_ranking, name='crear_top5'),

    # URL 2: La específica por categoría (ej: crear-ranking/ID_DE_MONGO/)
    path('crear-ranking/<str:categoria_id>/', views.crear_ranking, name='crear_ranking_categoria'),

    # --- RESTO ---
    path('mis-rankings/', views.mis_rankings, name='mis_rankings'),
    path('valorar-equipos/', views.valorar_equipos, name='valorar_equipos'),
    path('crear-categoria/', views.crear_categoria, name='crear_categoria'),
]