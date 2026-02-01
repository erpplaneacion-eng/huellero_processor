"""
Módulo de Webhooks para la app de Técnicos
Maneja notificaciones entrantes de servicios externos como AppSheet
"""

import json
import logging
import os
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .google_sheets import GoogleSheetsService
from .constantes import obtener_id_hoja
from .views import _parsear_hora

logger = logging.getLogger(__name__)

# Token secreto para validar requests (configurar en .env)
WEBHOOK_SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET_TOKEN', 'chvs-webhook-secret-2024')

@csrf_exempt
@require_http_methods(["POST"])
def webhook_novedad_nomina(request):
    """
    Webhook que recibe notificaciones de AppSheet cuando se marca NOVEDAD=SI
    en la hoja nomina_cali.

    Crea un registro en la hoja 'novedades_cali'.
    Soporta parámetro GET ?sede=CALI o ?sede=YUMBO
    """
    try:
        # Parsear JSON del body
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON inválido'
            }, status=400)

        # Validar token de seguridad
        token = payload.get('token', '')
        if token != WEBHOOK_SECRET_TOKEN:
            logger.warning(f"Webhook rechazado: token inválido")
            return JsonResponse({
                'success': False,
                'error': 'Token inválido'
            }, status=401)

        # Obtener datos del registro
        data = payload.get('data', {})
        if not data:
            return JsonResponse({
                'success': False,
                'error': 'No se recibieron datos'
            }, status=400)

        # Verificar que NOVEDAD sea SI
        novedad = str(data.get('NOVEDAD', '')).strip().upper()
        if novedad != 'SI':
            return JsonResponse({
                'success': False,
                'error': 'Solo se procesan registros con NOVEDAD=SI'
            }, status=400)

        # Determinar Sede (Default: Cali)
        sede_param = request.GET.get('sede', '').upper()
        if not sede_param:
            sede_param = payload.get('sede', 'CALI').upper()
            
        # Conectar a Google Sheets
        service = GoogleSheetsService()
        sheet_id = obtener_id_hoja(sede_param)
        libro = service.abrir_libro(sheet_id)

        # Obtener o crear la hoja novedades_cali
        nombre_hoja = 'novedades_cali'
        try:
            hoja_novedades = service.obtener_hoja(libro, nombre_hoja=nombre_hoja)
        except Exception:
            # La hoja no existe, crearla
            hoja_novedades = libro.add_worksheet(title=nombre_hoja, rows=1000, cols=20)
            # Agregar headers
            headers = [
                'ID', 'FECHA_REGISTRO', 'SUPERVISOR', 'SEDE', 'TIPO TIEMPO LABORADO',
                'CEDULA', 'NOMBRE_COLABORADOR', 'FECHA', 'DIA', 'HORA_INICIAL',
                'HORA_FINAL', 'TOTAL_HORAS', 'FECHA FINAL', 'DIA FINAL',
                'OBSERVACIONES', 'OBSERVACION', 'ESTADO', 'PROCESADO_POR'
            ]
            hoja_novedades.update(values=[headers], range_name='A1:R1')
            logger.info(f"Hoja '{nombre_hoja}' creada exitosamente")

        # Preparar la fila a insertar
        fecha_registro = datetime.now().strftime('%d/%m/%Y %H:%M')

        # Calcular total de horas
        h_ini_str = data.get('HORA_INICIAL', '')
        h_fin_str = data.get('HORA_FINAL', '')
        total_horas = ''
        try:
            t1 = _parsear_hora(h_ini_str)
            t2 = _parsear_hora(h_fin_str)
            if t1 and t2:
                diff = t2 - t1
                # Manejar turnos nocturnos (salida al día siguiente)
                if diff.total_seconds() < 0:
                    diff += timedelta(days=1)
                total_horas = f"{diff.total_seconds() / 3600:.2f}"
        except Exception:
            total_horas = '-'

        nueva_fila = [
            data.get('ID', ''),  # ID original de nomina_cali
            fecha_registro,
            data.get('SUPERVISOR', ''),
            data.get('DESCRIPCION_PROYECTO', data.get('SEDE', '')),
            data.get('TIPO_TIEMPO_LABORADO', data.get('TIPO TIEMPO LABORADO', '')),
            data.get('CEDULA', ''),
            data.get('NOMBRE_COLABORADOR', ''),
            data.get('FECHA', ''),
            data.get('DIA', ''),
            data.get('HORA_INICIAL', ''),
            data.get('HORA_FINAL', ''),
            total_horas,
            data.get('FECHA_FINAL', data.get('FECHA FINAL', '')),  # FECHA FINAL
            data.get('DIA_FINAL', data.get('DIA FINAL', '')),      # DIA FINAL
            data.get('OBSERVACIONES', ''),                          # OBSERVACIONES
            data.get('OBSERVACION', ''),
            'PENDIENTE',  # Estado inicial
            'AppSheet'    # Procesado por
        ]

        # Insertar la fila
        service.agregar_fila(hoja_novedades, nueva_fila)

        logger.info(f"Novedad registrada: {data.get('NOMBRE_COLABORADOR', 'N/A')} - {data.get('FECHA', 'N/A')}")

        return JsonResponse({
            'success': True,
            'message': 'Novedad registrada exitosamente',
            'data': {
                'colaborador': data.get('NOMBRE_COLABORADOR', ''),
                'fecha': data.get('FECHA', ''),
                'sede': data.get('DESCRIPCION_PROYECTO', data.get('SEDE', ''))
            }
        })

    except Exception as e:
        logger.error(f"Error en webhook_novedad_nomina: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
