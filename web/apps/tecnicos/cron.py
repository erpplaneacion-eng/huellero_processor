"""
Módulo de Tareas Cron para la app de Técnicos
Ejecuta tareas programadas como facturación diaria y generación de nómina
"""

import logging
import os
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Token secreto para validar requests (configurar en .env)
WEBHOOK_SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET_TOKEN', 'chvs-webhook-secret-2024')

def _validar_token_cron(request):
    """
    Valida el token de autenticación para endpoints cron.
    Acepta token via:
    - Header: Authorization: Bearer <token>
    - Query param: ?token=<token>
    """
    # Intentar obtener de header Authorization
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        if token == WEBHOOK_SECRET_TOKEN:
            return True

    # Intentar obtener de query param
    token = request.GET.get('token', '')
    if token == WEBHOOK_SECRET_TOKEN:
        return True

    return False


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cron_facturacion(request):
    """
    Endpoint para ejecutar facturación diaria para TODAS las sedes.
    URL: /supervision/cron/facturacion/?token=<token>
    """
    if not _validar_token_cron(request):
        logger.warning("Cron facturacion: token inválido")
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)

    try:
        from .facturacion_service import FacturacionService
        from .constantes import SEDES

        logger.info("Ejecutando facturación diaria via cron (todas las sedes)...")
        
        resultados_agg = []
        
        for sede_key in SEDES:
            logger.info(f"Procesando sede: {sede_key}")
            service = FacturacionService(sede=sede_key)
            resultado = service.ejecutar_facturacion_diaria()
            resultados_agg.append({
                'sede': sede_key,
                'resultado': resultado
            })

        logger.info(f"Facturación completada para {len(resultados_agg)} sedes")

        return JsonResponse({
            'success': True,
            'message': 'Proceso completado para todas las sedes',
            'data': resultados_agg
        })

    except Exception as e:
        logger.error(f"Error en cron_facturacion: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cron_nomina_cali(request):
    """
    Endpoint para ejecutar nómina diaria para TODAS las sedes.
    URL: /supervision/cron/nomina-cali/?token=<token>
    """
    if not _validar_token_cron(request):
        logger.warning("Cron nomina: token inválido")
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)

    try:
        from .nomina_cali_service import NominaCaliService
        from .constantes import SEDES

        logger.info("Ejecutando nómina diaria via cron (todas las sedes)...")
        
        resultados_agg = []
        
        for sede_key in SEDES:
            logger.info(f"Procesando sede: {sede_key}")
            service = NominaCaliService(sede=sede_key)
            resultado = service.ejecutar_nomina_diaria()
            resultados_agg.append({
                'sede': sede_key,
                'resultado': resultado
            })

        logger.info(f"Nómina completada para {len(resultados_agg)} sedes")

        return JsonResponse({
            'success': True,
            'message': 'Proceso completado para todas las sedes',
            'data': resultados_agg
        })

    except Exception as e:
        logger.error(f"Error en cron_nomina_cali: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cron_liquidacion(request):
    """
    Endpoint para ejecutar liquidación de nómina diaria + envío de email.
    Ejecuta para TODAS las sedes configuradas.
    URL: /supervision/cron/liquidacion/?token=<token>
    Param opcional: ?sin_email=1 para omitir el envío de correo
    """
    if not _validar_token_cron(request):
        logger.warning("Cron liquidacion: token inválido")
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)

    try:
        from .liquidacion_nomina_service import LiquidacionNominaService
        from .email_service import EmailService
        from .constantes import SEDES
        from datetime import date

        sin_email = request.GET.get('sin_email', '0') == '1'
        fecha = date.today()

        logger.info("Ejecutando liquidación de nómina via cron (todas las sedes)...")
        
        resultados_agg = []
        
        for sede_key in SEDES:
            logger.info(f"Procesando liquidación para: {sede_key}")
            
            # Ejecutar liquidación
            service = LiquidacionNominaService(sede=sede_key)
            registros_generados, msg = service.generar_liquidacion_dia(fecha)
            resultado = service.ejecutar_liquidacion_diaria()

            logger.info(f"Liquidación {sede_key} completada: {resultado['mensaje']}")

            # Enviar email si hay registros y no se desactivó
            email_enviado = False
            email_error = None

            if not sin_email and registros_generados:
                try:
                    email_service = EmailService()
                    resultado_email = email_service.enviar_reporte_liquidacion(
                        fecha=fecha,
                        registros=registros_generados,
                        resultado=resultado
                    )
                    email_enviado = resultado_email.get('exito', False)
                    if not email_enviado:
                        email_error = resultado_email.get('mensaje', 'Error desconocido')
                    else:
                        logger.info(f"Email de liquidación ({sede_key}) enviado correctamente")
                except Exception as e:
                    email_error = str(e)
                    logger.error(f"Error enviando email ({sede_key}): {e}")
            
            resultados_agg.append({
                'sede': sede_key,
                'resultado': resultado,
                'email': {
                    'enviado': email_enviado,
                    'error': email_error
                }
            })

        return JsonResponse({
            'success': True,
            'message': 'Proceso completado para todas las sedes',
            'data': resultados_agg
        })

    except Exception as e:
        logger.error(f"Error en cron_liquidacion: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
