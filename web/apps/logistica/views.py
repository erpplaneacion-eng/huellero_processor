"""
Views para el área de Logística
"""

import os
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .processor import HuelleroProcessor


class IndexView(TemplateView):
    """Vista principal del área de Logística"""
    template_name = 'logistica/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['area'] = settings.AREAS_CONFIG.get('logistica', {})
        context['area_key'] = 'logistica'
        return context


@method_decorator(csrf_exempt, name='dispatch')
class ProcesarView(View):
    """API para procesar archivo de huellero"""

    def post(self, request):
        try:
            if 'archivo' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No se envió ningún archivo'}, status=400)

            archivo = request.FILES['archivo']

            if archivo.name == '':
                return JsonResponse({'success': False, 'error': 'No se seleccionó ningún archivo'}, status=400)

            if not archivo.name.lower().endswith(('.xls', '.xlsx')):
                return JsonResponse({'success': False, 'error': 'Formato no válido. Use .xls o .xlsx'}, status=400)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = os.path.splitext(archivo.name)[1]
            nombre_archivo = f"huellero_logistica_{timestamp}{extension}"
            ruta_archivo = settings.DATA_INPUT_DIR / nombre_archivo

            with open(ruta_archivo, 'wb+') as destino:
                for chunk in archivo.chunks():
                    destino.write(chunk)

            rutas_archivos = [str(ruta_archivo)]

            # Segundo archivo opcional
            archivo2 = request.FILES.get('archivo2')
            if archivo2:
                if not archivo2.name.lower().endswith(('.xls', '.xlsx')):
                    return JsonResponse({'success': False, 'error': 'Archivo 2: formato no válido. Use .xls o .xlsx'}, status=400)
                extension2 = os.path.splitext(archivo2.name)[1]
                nombre_archivo2 = f"huellero_logistica_{timestamp}_2{extension2}"
                ruta_archivo2 = settings.DATA_INPUT_DIR / nombre_archivo2
                with open(ruta_archivo2, 'wb+') as destino2:
                    for chunk in archivo2.chunks():
                        destino2.write(chunk)
                rutas_archivos.append(str(ruta_archivo2))

            usar_maestro = request.POST.get('usar_maestro', 'true').lower() == 'true'
            fecha_inicio_str = (request.POST.get('fecha_inicio') or '').strip()
            fecha_fin_str = (request.POST.get('fecha_fin') or '').strip()

            fecha_inicio = None
            fecha_fin = None
            if fecha_inicio_str:
                try:
                    fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Fecha inicio inválida. Use formato YYYY-MM-DD.'}, status=400)

            if fecha_fin_str:
                try:
                    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Fecha final inválida. Use formato YYYY-MM-DD.'}, status=400)

            if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
                return JsonResponse({'success': False, 'error': 'La fecha inicio no puede ser mayor que la fecha final.'}, status=400)

            processor = HuelleroProcessor(area='logistica')
            resultado = processor.procesar(
                rutas_archivos if len(rutas_archivos) > 1 else rutas_archivos[0],
                usar_maestro,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )

            return JsonResponse(resultado)

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error durante el procesamiento: {str(e)}'}, status=500)


class DescargarView(View):
    """Vista para descargar archivos generados"""

    def get(self, request, filename):
        ruta_archivo = settings.DATA_OUTPUT_DIR / filename

        if not ruta_archivo.exists():
            raise Http404('Archivo no encontrado')

        return FileResponse(open(ruta_archivo, 'rb'), as_attachment=True, filename=filename)


@csrf_exempt
def cron_sincronizar_planta(request):
    """
    GET/POST /logistica/cron/sincronizar-planta/?token=<WEBHOOK_SECRET_TOKEN>
    Ejecuta sincronizar_planta: copia registros nuevos de tabla_planta → maestro_empleado.
    """
    token_esperado = os.environ.get('WEBHOOK_SECRET_TOKEN', '')
    token_recibido = (
        request.GET.get('token') or
        request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    )
    if not token_esperado or token_recibido != token_esperado:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    import io
    from django.core.management import call_command

    buffer = io.StringIO()
    try:
        call_command('sincronizar_planta', stdout=buffer)
        return JsonResponse({'success': True, 'log': buffer.getvalue()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
