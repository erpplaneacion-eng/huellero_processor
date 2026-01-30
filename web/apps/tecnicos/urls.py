from django.urls import path
from . import views, webhooks, cron

app_name = 'tecnicos'

urlpatterns = [
    path('', views.index, name='index'),
    path('liquidacion-nomina/', views.liquidacion_nomina, name='liquidacion_nomina'),
    path('nomina-cali/', views.nomina_cali, name='nomina_cali'),
    path('facturacion/', views.facturacion, name='facturacion'),

    # Webhooks para AppSheet
    path('api/webhook/novedad-nomina/', webhooks.webhook_novedad_nomina, name='webhook_novedad_nomina'),

    # Endpoints Cron (para tareas programadas)
    path('cron/facturacion/', cron.cron_facturacion, name='cron_facturacion'),
    path('cron/nomina-cali/', cron.cron_nomina_cali, name='cron_nomina_cali'),
    path('cron/liquidacion/', cron.cron_liquidacion, name='cron_liquidacion'),
]