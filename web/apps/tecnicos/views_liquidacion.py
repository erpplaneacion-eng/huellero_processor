from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .google_sheets import GoogleSheetsService
import logging
from .views import (
    _obtener_datos_filtrados,
    _obtener_novedades_hoja,
    _safe_float,
    _parsear_horas_formato
)

logger = logging.getLogger(__name__)

@login_required
def liquidacion_nomina(request):
    """Vista para Liquidación Nómina"""
    columnas = [
        'SUPERVISOR', 'SEDE', 'FECHA', 'DIA', 'CANT. MANIPULADORAS',
        'TOTAL HORAS', 'HUBO_RACIONES', 'TOTAL RACIONES', 'OBSERVACION', 'NOVEDAD'
    ]
    context = _obtener_datos_filtrados(
        request,
        'liquidacion_nomina',
        {
            'supervisor': ['SUPERVISOR'],
            'fecha': ['FECHA'],
            'sede': ['SEDE', 'CENTRO COSTO']
        },
        'Liquidación Nómina',
        columnas_permitidas=columnas
    )

    rows_raw = context.get('rows', [])
    rows_processed = [] # Lista de diccionarios con metadatos

    stats = {
        'dias_nomina': 0,
        'dias_raciones': 0,
        'inconsistencias': 0
    }

    # Obtener novedades de nomina_cali y facturacion
    filtro_mes = request.GET.get('mes', '')
    filtro_supervisor = request.GET.get('supervisor', '').strip().lower()
    filtro_sede = request.GET.get('sede', '').strip().lower()
    novedades_nomina = {'cantidad': 0, 'fechas': []}
    novedades_facturacion = {'cantidad': 0, 'fechas': []}

    try:
        service = GoogleSheetsService()
        libro = service.abrir_libro()
        # nomina_cali usa SUPERVISOR y DESCRIPCION PROYECTO
        novedades_nomina = _obtener_novedades_hoja(
            service, libro, 'nomina_cali',
            filtro_mes=filtro_mes,
            filtro_supervisor=filtro_supervisor,
            filtro_sede=filtro_sede,
            col_supervisor='SUPERVISOR',
            col_sede='DESCRIPCION PROYECTO'
        )
        # facturacion usa SUPERVISOR y SEDE_EDUCATIVA
        novedades_facturacion = _obtener_novedades_hoja(
            service, libro, 'facturacion',
            filtro_mes=filtro_mes,
            filtro_supervisor=filtro_supervisor,
            filtro_sede=filtro_sede,
            col_supervisor='SUPERVISOR',
            col_sede='SEDE_EDUCATIVA'
        )
    except Exception as e:
        logger.error(f"Error obteniendo novedades: {e}")

    if rows_raw:
        # Mapeo de columnas por nombre para mayor robustez
        # columnas = ['SUPERVISOR', 'SEDE', 'FECHA', 'DIA', 'CANT. MANIPULADORAS',
        #             'TOTAL HORAS', 'HUBO_RACIONES', 'TOTAL RACIONES', 'OBSERVACION', 'NOVEDAD']
        idx_cant_man = 4      # CANT. MANIPULADORAS
        idx_tot_horas = 5     # TOTAL HORAS (formato HH:MM)
        idx_tot_rac = 7       # TOTAL RACIONES

        for r in rows_raw:
            # Obtener valores con manejo seguro de índices
            cant_man = _safe_float(r[idx_cant_man]) if len(r) > idx_cant_man else 0.0
            # TOTAL HORAS viene en formato "HH:MM", usar parser especial
            horas = _parsear_horas_formato(r[idx_tot_horas]) if len(r) > idx_tot_horas else 0.0
            raciones = _safe_float(r[idx_tot_rac]) if len(r) > idx_tot_rac else 0.0

            # Metrica 1: Días con Nómina
            if horas > 0:
                stats['dias_nomina'] += 1

            # Metrica 2: Días con Raciones
            if raciones > 0:
                stats['dias_raciones'] += 1

            # Metrica 3: Inconsistencias (Cruce)
            tiene_alerta = False
            tipo_alerta = ""

            # Solo marcar alerta si hay datos significativos (evitar 0 vs 0)
            if raciones > 0 and horas == 0:
                tiene_alerta = True
                stats['inconsistencias'] += 1
                tipo_alerta = "Producción sin horas registradas"
            elif horas > 0 and raciones == 0:
                tiene_alerta = True
                stats['inconsistencias'] += 1
                tipo_alerta = "Horas registradas sin producción"

            # Empaquetar fila
            rows_processed.append({
                'cells': r,
                'alert': tiene_alerta,
                'alert_msg': tipo_alerta
            })

    # Reemplazar rows planos por rows procesados
    context['rows'] = rows_processed
    context['stats'] = stats
    context['novedades_nomina'] = novedades_nomina
    context['novedades_facturacion'] = novedades_facturacion
    return render(request, 'tecnicos/liquidacion_nomina.html', context)
