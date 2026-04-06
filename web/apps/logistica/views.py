"""
Views para el area de Logistica
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
    """Vista principal del area de Logistica"""
    template_name = 'logistica/index.html'


@method_decorator(csrf_exempt, name='dispatch')
class ProcesarView(View):
    """API para procesar archivo de huellero"""

    def post(self, request):
        try:
            if 'archivo' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No se envio ningun archivo'}, status=400)

            archivo = request.FILES['archivo']
            if archivo.name == '':
                return JsonResponse({'success': False, 'error': 'No se selecciono ningun archivo'}, status=400)

            if not archivo.name.lower().endswith(('.xls', '.xlsx')):
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de archivo no valido. Use .xls o .xlsx'
                }, status=400)

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
            return JsonResponse({
                'success': False,
                'error': f'Error durante el procesamiento: {str(e)}'
            }, status=500)


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
