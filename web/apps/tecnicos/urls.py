from django.urls import path
from . import views

app_name = 'tecnicos'

urlpatterns = [
    path('', views.index, name='index'),
    path('liquidacion-nomina/', views.liquidacion_nomina, name='liquidacion_nomina'),
    path('nomina-cali/', views.nomina_cali, name='nomina_cali'),
    path('facturacion/', views.facturacion, name='facturacion'),
]