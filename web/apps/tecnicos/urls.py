from django.urls import path
from . import views

app_name = 'tecnicos'

urlpatterns = [
    path('', views.index, name='index'),
    path('liquidacion-nomina/', views.liquidacion_nomina, name='liquidacion_nomina'),
]
