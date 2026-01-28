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
