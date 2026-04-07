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

            usar_maestro = request.POST.get('usar_maestro', 'true').lower() == 'true'

            processor = HuelleroProcessor(area='logistica')
            resultado = processor.procesar(str(ruta_archivo), usar_maestro)

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
