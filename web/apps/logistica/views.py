"""
Views para el área de Logística
"""

import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import RegistroAsistencia
from .processor import HuelleroProcessor


@method_decorator(login_required, name='dispatch')
class IndexView(TemplateView):
    """Vista principal del área de Logística"""
    template_name = 'logistica/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['area'] = settings.AREAS_CONFIG.get('logistica', {})
        context['area_key'] = 'logistica'
        return context


@method_decorator([login_required, csrf_exempt], name='dispatch')
class ProcesarView(View):
    """API para procesar archivo de huellero"""

    def post(self, request):
        try:
            # Validar que se envió un archivo
            if 'archivo' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No se envió ningún archivo'
                }, status=400)

            archivo = request.FILES['archivo']

            if archivo.name == '':
                return JsonResponse({
                    'success': False,
                    'error': 'No se seleccionó ningún archivo'
                }, status=400)

            # Validar extensión
            if not archivo.name.lower().endswith(('.xls', '.xlsx')):
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de archivo no válido. Use .xls o .xlsx'
                }, status=400)

            # Guardar archivo temporalmente
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = os.path.splitext(archivo.name)[1]
            nombre_archivo = f"huellero_logistica_{timestamp}{extension}"
            ruta_archivo = settings.DATA_INPUT_DIR / nombre_archivo

            # Guardar el archivo
            with open(ruta_archivo, 'wb+') as destino:
                for chunk in archivo.chunks():
                    destino.write(chunk)

            # Obtener opción de maestro
            usar_maestro = request.POST.get('usar_maestro', 'true').lower() == 'true'

            # Procesar archivo
            processor = HuelleroProcessor(area='logistica')
            resultado = processor.procesar(str(ruta_archivo), usar_maestro)

            return JsonResponse(resultado)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error durante el procesamiento: {str(e)}'
            }, status=500)


@method_decorator([login_required, csrf_exempt], name='dispatch')
class GuardarObs1View(View):
    """
    Guarda el valor de OBSERVACIONES_1 seleccionado por el usuario en el dashboard.
    POST /logistica/api/registros/obs1/
    Body JSON: {"registro_id": 5, "obs1": "texto seleccionado"}
    """

    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
            registro_id = int(data.get('registro_id', 0))
            obs1 = str(data.get('obs1', '')).strip()

            registro = RegistroAsistencia.objects.get(pk=registro_id)
            registro.observaciones_1 = obs1
            registro.save(update_fields=['observaciones_1', 'actualizado_en'])

            return JsonResponse({'ok': True})

        except RegistroAsistencia.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class ListarRegistrosView(View):
    """
    Devuelve todos los registros guardados en BD con el mismo formato
    que usa el dashboard, sin necesidad de procesar un Excel.
    GET /logistica/api/registros/
    """

    def get(self, request):
        try:
            from apps.logistica.models import Concepto

            processor = HuelleroProcessor(area='logistica')
            codigos_excluidos = processor._cargar_codigos_excluidos()

            registros_qs = RegistroAsistencia.objects.exclude(
                codigo__in=codigos_excluidos
            ).order_by('codigo', 'fecha', 'hora_ingreso')

            horarios_por_codigo = processor._cargar_horarios_por_codigo()

            def _best_fit_turno(codigo_int, hora_ingreso_str):
                turnos_raw = horarios_por_codigo.get(codigo_int, [])
                if not turnos_raw or not hora_ingreso_str or ':' not in hora_ingreso_str:
                    return ''
                try:
                    parts = hora_ingreso_str.split(':')
                    ingreso_min = int(parts[0]) * 60 + int(parts[1])
                    e, s = min(turnos_raw, key=lambda t: abs(t[0] - ingreso_min))
                    return f"{e//60:02d}:{e%60:02d}-{s//60:02d}:{s%60:02d}"
                except Exception:
                    return ''

            empleados = {}
            for r in registros_qs:
                codigo = str(r.codigo)
                if codigo not in empleados:
                    empleados[codigo] = {
                        'codigo':    codigo,
                        'nombre':    r.nombre,
                        'documento': r.documento,
                        'cargo':     r.cargo,
                        'registros': [],
                    }
                empleados[codigo]['registros'].append({
                    'id':          r.id,
                    'fecha':       r.fecha.strftime('%d/%m/%Y'),
                    'dia':         r.dia,
                    'am':          r.marcaciones_am,
                    'pm':          r.marcaciones_pm,
                    'ingreso':     r.hora_ingreso,
                    'salida':      r.hora_salida,
                    'horas':       r.total_horas,
                    'limite':      r.limite_horas_dia,
                    'observacion': r.observacion,
                    'obs1':        r.observaciones_1,
                    'turno':       _best_fit_turno(r.codigo, r.hora_ingreso),
                })

            datos = list(empleados.values())
            conceptos = list(
                Concepto.objects.values_list('observaciones', flat=True).order_by('observaciones')
            )

            return JsonResponse({
                'success':       True,
                'datos':         datos,
                'conceptos':     conceptos,
                'archivo':       None,
                'archivo_casos': None,
                'desde_db':      True,
                'stats': {
                    'empleados_unicos':      len(datos),
                    'total_registros':       registros_qs.count(),
                    'turnos_completos':      0,
                    'turnos_incompletos':    0,
                    'duplicados_eliminados': 0,
                    'estados_inferidos':     0,
                },
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class DescargarView(View):
    """Vista para descargar archivos generados"""

    def get(self, request, filename):
        ruta_archivo = settings.DATA_OUTPUT_DIR / filename

        if not ruta_archivo.exists():
            raise Http404('Archivo no encontrado')

        return FileResponse(
            open(ruta_archivo, 'rb'),
            as_attachment=True,
            filename=filename
        )
