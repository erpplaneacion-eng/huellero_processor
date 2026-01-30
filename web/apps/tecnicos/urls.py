from django.urls import path
from . import views

app_name = 'tecnicos'

urlpatterns = [
    path('', views.index, name='index'),
    path('liquidacion-nomina/', views.liquidacion_nomina, name='liquidacion_nomina'),
    path('nomina-cali/', views.nomina_cali, name='nomina_cali'),
    path('facturacion/', views.facturacion, name='facturacion'),

    # Webhooks para AppSheet
    path('api/webhook/novedad-nomina/', views.webhook_novedad_nomina, name='webhook_novedad_nomina'),

    # Endpoints CRON para tareas programadas
    # Usar con cron-job.org u otro servicio externo
    path('cron/facturacion/', views.cron_facturacion, name='cron_facturacion'),
    path('cron/nomina-cali/', views.cron_nomina_cali, name='cron_nomina_cali'),
    path('cron/liquidacion/', views.cron_liquidacion, name='cron_liquidacion'),
]