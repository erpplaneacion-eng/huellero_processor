from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .views import _obtener_datos_filtrados

@login_required
def facturacion(request):
    """Vista para Facturación"""
    columnas = [
        'SEDE_EDUCATIVA', 'FECHA', 'DIA', 'SUPERVISOR',
        'COMPLEMENTO_AM_PM_PREPARADO', 'COMPLEMENTO_PM_PREPARADO',
        'ALMUERZO_JORNADA_UNICA', 'COMPLEMENTO_AM_PM_INDUSTRIALIZADO', 'NOVEDAD'
    ]
    context = _obtener_datos_filtrados(
        request,
        'facturacion',
        {
            'supervisor': ['SUPERVISOR'],
            'fecha': ['FECHA'],
            'sede': ['SEDE_EDUCATIVA', 'SEDE']
        },
        'Facturación',
        columnas_permitidas=columnas
    )
    return render(request, 'tecnicos/facturacion.html', context)
