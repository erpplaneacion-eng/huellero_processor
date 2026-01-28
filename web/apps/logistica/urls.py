"""
URLs para el área de Logística
"""

from django.urls import path
from . import views

app_name = 'logistica'

urlpatterns = [
    # Página principal del área
    path('', views.IndexView.as_view(), name='index'),

    # API
    path('api/procesar/', views.ProcesarView.as_view(), name='procesar'),
    path('api/descargar/<str:filename>/', views.DescargarView.as_view(), name='descargar'),
]
