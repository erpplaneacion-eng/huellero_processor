from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .google_sheets import GoogleSheetsService
import logging
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Opciones para el select de meses
MESES = [
    ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'),
    ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
    ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Septiembre'),
    ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
]

def _parsear_hora(valor):
    """Intenta convertir un string de hora a objeto datetime."""
    formatos = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']
    valor = str(valor).strip()
    if not valor:
        return None
    
    for fmt in formatos:
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None

def _safe_float(val):
    """Convierte a float de forma segura, retornando 0.0 si falla."""
    try:
        # Reemplazar comas por puntos si es necesario y limpiar espacios
        limpio = str(val).replace(',', '.').strip()
        if not limpio: return 0.0
        return float(limpio)
    except (ValueError, TypeError):
        return 0.0


def _parsear_horas_formato(val):
    """
    Convierte formato de horas HH:MM o H:MM a horas decimales.
    Ej: "5:30" -> 5.5, "10:15" -> 10.25, "" -> 0.0
    También acepta números directos.
    """
    try:
        val_str = str(val).strip()
        if not val_str:
            return 0.0

        # Si contiene ":", es formato HH:MM
        if ':' in val_str:
            partes = val_str.split(':')
            horas = int(partes[0]) if partes[0] else 0
            minutos = int(partes[1]) if len(partes) > 1 and partes[1] else 0
            return horas + (minutos / 60.0)

        # Intentar como número directo
        return float(val_str.replace(',', '.'))
    except (ValueError, TypeError, IndexError):
        return 0.0

@login_required
def index(request):
    """
    Vista principal del área de supervisión/técnicos.
    """
    context = {
        'titulo': 'Panel de Supervisión',
        'usuario': request.user,
    }
    return render(request, 'tecnicos/index.html', context)


def _obtener_datos_filtrados(request, nombre_hoja, columnas_map, titulo_vista, columnas_permitidas=None, procesador_fila=None, headers_manuales=None):
    """
    Función auxiliar para obtener, filtrar y preparar datos de Google Sheets.
    """
    data = []
    headers = []
    error_message = None
    
    # Obtener parámetros de filtro
    filtro_supervisor = request.GET.get('supervisor', '').strip().lower()
    filtro_mes = request.GET.get('mes', '')
    filtro_sede = request.GET.get('sede', '').strip().lower()

    try:
        service = GoogleSheetsService()
        libro = service.abrir_libro()
        
        try:
            hoja = service.obtener_hoja(libro, nombre_hoja=nombre_hoja)
        except Exception:
            hoja = None

        if not hoja:
            for h in libro.worksheets():
                if nombre_hoja.lower() in h.title.lower():
                    hoja = h
                    break
        
        if not hoja:
             error_message = f"No se encontró la hoja '{nombre_hoja}'."
        else:
            raw_data = service.leer_datos(hoja)
            
            if raw_data:
                raw_headers = [str(h).strip() for h in raw_data[0]]
                filas = raw_data[1:]
                
                # Función para normalizar claves (quitar espacios y _ para comparar)
                def normalizar(txt):
                    return str(txt).upper().replace(' ', '').replace('_', '').replace('.', '').strip()

                # Mapa de headers normalizado
                headers_dict = {normalizar(h): i for i, h in enumerate(raw_headers)}
                
                def buscar_idx(claves):
                    for clave in claves:
                        c_norm = normalizar(clave)
                        if c_norm in headers_dict:
                            return headers_dict[c_norm]
                    # Búsqueda parcial si falla exacta
                    for h_norm, idx in headers_dict.items():
                        for clave in claves:
                            if normalizar(clave) in h_norm:
                                return idx
                    return -1

                idx_supervisor = buscar_idx(columnas_map.get('supervisor', []))
                idx_fecha = buscar_idx(columnas_map.get('fecha', []))
                idx_sede = buscar_idx(columnas_map.get('sede', []))

                if headers_manuales:
                    headers = headers_manuales
                elif columnas_permitidas:
                    headers = []
                    indices_salida = []
                    for cp in columnas_permitidas:
                        idx = -1
                        c_norm = normalizar(cp)
                        
                        # Búsqueda directa normalizada
                        if c_norm in headers_dict:
                            idx = headers_dict[c_norm]
                        
                        # Búsqueda parcial normalizada (fallback)
                        if idx == -1:
                            for h_norm, idx_real in headers_dict.items():
                                if c_norm in h_norm or h_norm in c_norm:
                                    idx = idx_real
                                    break
                        
                        if idx != -1:
                            headers.append(cp)
                            indices_salida.append(idx)
                        else:
                            headers.append(cp)
                            indices_salida.append(-1)
                else:
                    headers = raw_headers
                    indices_salida = list(range(len(raw_headers)))

                # Procesar filas
                for fila in filas:
                    cumple_filtros = True
                            
                    if filtro_supervisor and idx_supervisor != -1:
                        val = str(fila[idx_supervisor]).lower() if len(fila) > idx_supervisor else ''
                        if filtro_supervisor not in val:
                            cumple_filtros = False
                            
                    if cumple_filtros and filtro_sede and idx_sede != -1:
                        val = str(fila[idx_sede]).lower() if len(fila) > idx_sede else ''
                        if filtro_sede not in val:
                            cumple_filtros = False
                            
                    if cumple_filtros and filtro_mes and idx_fecha != -1:
                        val_fecha = str(fila[idx_fecha]) if len(fila) > idx_fecha else ''
                        mes_fila = ''
                        try:
                            if '/' in val_fecha:
                                parts = val_fecha.split('/')
                                if len(parts) >= 2: mes_fila = parts[1]
                            elif '-' in val_fecha:
                                parts = val_fecha.split('-')
                                if len(parts) >= 2: mes_fila = parts[1]
                        except: pass
                        
                        if mes_fila.lstrip('0') != filtro_mes.lstrip('0'):
                            cumple_filtros = False

                    if cumple_filtros:
                        if procesador_fila:
                            fila_final = procesador_fila(fila, headers_dict)
                            data.append(fila_final)
                        elif columnas_permitidas:
                            fila_final = []
                            for idx in indices_salida:
                                val = fila[idx] if idx != -1 and len(fila) > idx else ''
                                fila_final.append(val)
                            data.append(fila_final)
                        else:
                            data.append(fila)
            else:
                error_message = "La hoja está vacía."

    except Exception as e:
        logger.error(f"Error accediendo a Google Sheets ({nombre_hoja}): {e}")
        error_message = f"Error al cargar los datos: {str(e)}"

    return {
        'headers': headers,
        'rows': data,
        'error_message': error_message,
        'titulo': titulo_vista,
        'filtros': {'supervisor': filtro_supervisor, 'mes': filtro_mes, 'sede': filtro_sede},
        'meses': MESES
    }

def _obtener_novedades_hoja(service, libro, nombre_hoja, filtro_mes='', filtro_supervisor='', filtro_sede='', col_supervisor='SUPERVISOR', col_sede='SEDE'):
    """
    Obtiene las novedades de una hoja específica.
    Retorna un dict con 'cantidad' y 'fechas' (lista de fechas únicas con novedad).

    Args:
        service: GoogleSheetsService instance
        libro: Spreadsheet object
        nombre_hoja: Nombre de la hoja a consultar
        filtro_mes: Filtro por mes (01-12)
        filtro_supervisor: Filtro por supervisor (búsqueda parcial)
        filtro_sede: Filtro por sede (búsqueda parcial)
        col_supervisor: Nombre de la columna de supervisor en esta hoja
        col_sede: Nombre de la columna de sede en esta hoja
    """
    resultado = {'cantidad': 0, 'fechas': []}

    try:
        hoja = None
        try:
            hoja = service.obtener_hoja(libro, nombre_hoja=nombre_hoja)
        except Exception:
            for h in libro.worksheets():
                if nombre_hoja.lower() in h.title.lower():
                    hoja = h
                    break

        if not hoja:
            return resultado

        raw_data = service.leer_datos(hoja)
        if not raw_data or len(raw_data) < 2:
            return resultado

        raw_headers = [str(h).strip() for h in raw_data[0]]
        filas = raw_data[1:]

        # Normalizar headers
        def normalizar(txt):
            return str(txt).upper().replace(' ', '').replace('_', '').replace('.', '').strip()

        headers_dict = {normalizar(h): i for i, h in enumerate(raw_headers)}

        # Buscar índices de columnas necesarias
        idx_novedad = headers_dict.get('NOVEDAD', -1)
        idx_fecha = headers_dict.get('FECHA', -1)
        idx_supervisor = headers_dict.get(normalizar(col_supervisor), -1)
        idx_sede = headers_dict.get(normalizar(col_sede), -1)

        if idx_novedad == -1:
            return resultado

        fechas_con_novedad = set()
        cantidad = 0

        for fila in filas:
            if len(fila) <= idx_novedad:
                continue

            novedad_val = str(fila[idx_novedad]).strip().upper()

            # Verificar si tiene novedad (SI, S, 1, TRUE, o cualquier valor no vacío distinto de NO/N/0/FALSE)
            tiene_novedad = novedad_val and novedad_val not in ('', 'NO', 'N', '0', 'FALSE')

            if not tiene_novedad:
                continue

            # Aplicar filtro por supervisor
            if filtro_supervisor and idx_supervisor != -1:
                val_sup = str(fila[idx_supervisor]).lower() if len(fila) > idx_supervisor else ''
                if filtro_supervisor not in val_sup:
                    continue

            # Aplicar filtro por sede
            if filtro_sede and idx_sede != -1:
                val_sede = str(fila[idx_sede]).lower() if len(fila) > idx_sede else ''
                if filtro_sede not in val_sede:
                    continue

            # Aplicar filtro por mes
            if filtro_mes and idx_fecha != -1 and len(fila) > idx_fecha:
                val_fecha = str(fila[idx_fecha])
                mes_fila = ''
                try:
                    if '/' in val_fecha:
                        parts = val_fecha.split('/')
                        if len(parts) >= 2: mes_fila = parts[1]
                    elif '-' in val_fecha:
                        parts = val_fecha.split('-')
                        if len(parts) >= 2: mes_fila = parts[1]
                except:
                    pass

                if mes_fila.lstrip('0') != filtro_mes.lstrip('0'):
                    continue

            # Pasó todos los filtros, contar
            cantidad += 1
            if idx_fecha != -1 and len(fila) > idx_fecha:
                fecha = str(fila[idx_fecha]).strip()
                if fecha:
                    fechas_con_novedad.add(fecha)

        resultado['cantidad'] = cantidad
        resultado['fechas'] = sorted(list(fechas_con_novedad))

    except Exception as e:
        logger.error(f"Error obteniendo novedades de {nombre_hoja}: {e}")

    return resultado


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

@login_required
def nomina_cali(request):
    """Vista para Nómina Cali con cálculo de horas"""
    headers_salida = [
        'SUPERVISOR', 'DESCRIPCION PROYECTO', 'TIPO TIEMPO LABORADO', 
        'CEDULA', 'NOMBRE COLABORADOR', 'FECHA', 'DIA', 
        'HORA INICIAL', 'HORA FINAL', 'total_horas', 'NOVEDAD'
    ]

    def procesar_fila_cali(fila, headers_dict):
        fila_nueva = []
        def get_val(col):
            # Normalizar el nombre de columna para que coincida con headers_dict
            col_norm = col.upper().replace(' ', '').replace('_', '').replace('.', '').strip()
            idx = headers_dict.get(col_norm, -1)
            return fila[idx] if idx != -1 and len(fila) > idx else ''

        fila_nueva.extend([
            get_val('SUPERVISOR'), get_val('DESCRIPCION PROYECTO'), 
            get_val('TIPO TIEMPO LABORADO'), get_val('CEDULA'), 
            get_val('NOMBRE COLABORADOR'), get_val('FECHA'), get_val('DIA'),
            get_val('HORA INICIAL'), get_val('HORA FINAL')
        ])

        h_ini_str, h_fin_str = get_val('HORA INICIAL'), get_val('HORA FINAL')
        try:
            t1, t2 = _parsear_hora(h_ini_str), _parsear_hora(h_fin_str)
            if t1 and t2:
                diff = t2 - t1
                if diff.total_seconds() < 0: diff += timedelta(days=1)
                fila_nueva.append(f"{diff.total_seconds() / 3600:.2f}")
            else:
                fila_nueva.append('-')
        except:
            fila_nueva.append('Error')

        fila_nueva.append(get_val('NOVEDAD'))
        return fila_nueva

    context = _obtener_datos_filtrados(
        request,
        'nomina_cali',
        {
            'supervisor': ['SUPERVISOR'],
            'fecha': ['FECHA'],
            'sede': ['DESCRIPCION PROYECTO']
        },
        'Nómina Cali',
        procesador_fila=procesar_fila_cali,
        headers_manuales=headers_salida
    )

    # Calcular días reportados por supervisor
    # Estructura de fila: [SUPERVISOR, DESC_PROY, TIPO, CEDULA, NOMBRE, FECHA, DIA, H_INI, H_FIN, TOT_HORAS, NOVEDAD]
    rows = context.get('rows', [])
    supervisores_dias = defaultdict(set)  # supervisor -> set de fechas únicas
    supervisores_registros = defaultdict(int)  # supervisor -> total registros

    for row in rows:
        if len(row) > 5:
            supervisor = row[0] or 'Sin Supervisor'
            fecha = row[5]
            if fecha:
                supervisores_dias[supervisor].add(fecha)
            supervisores_registros[supervisor] += 1

    # Convertir a lista ordenada por cantidad de días (descendente)
    stats_supervisores = []
    for sup, fechas in supervisores_dias.items():
        stats_supervisores.append({
            'nombre': sup,
            'dias': len(fechas),
            'registros': supervisores_registros[sup]
        })

    stats_supervisores.sort(key=lambda x: (-x['dias'], x['nombre']))

    context['stats_supervisores'] = stats_supervisores
    context['total_supervisores'] = len(stats_supervisores)
    context['total_registros'] = len(rows)

    return render(request, 'tecnicos/nomina_cali.html', context)

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


# =============================================================================
# WEBHOOK PARA APPSHEET - NOVEDADES
# =============================================================================

# Token secreto para validar requests (configurar en .env)
WEBHOOK_SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET_TOKEN', 'chvs-webhook-secret-2024')


@csrf_exempt
@require_http_methods(["POST"])
def webhook_novedad_nomina(request):
    """
    Webhook que recibe notificaciones de AppSheet cuando se marca NOVEDAD=SI
    en la hoja nomina_cali.

    Crea un registro en la hoja 'novedades_cali'.

    Esperamos un JSON con la estructura:
    {
        "token": "secret-token",
        "data": {
            "SUPERVISOR": "...",
            "DESCRIPCION_PROYECTO": "...",
            "CEDULA": "...",
            "NOMBRE_COLABORADOR": "...",
            "FECHA": "...",
            "DIA": "...",
            "HORA_INICIAL": "...",
            "HORA_FINAL": "...",
            "NOVEDAD": "SI",
            "OBSERVACION": "..."
        }
    }
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

        # Conectar a Google Sheets
        service = GoogleSheetsService()
        libro = service.abrir_libro()

        # Obtener o crear la hoja novedades_cali
        nombre_hoja = 'novedades_cali'
        try:
            hoja_novedades = service.obtener_hoja(libro, nombre_hoja=nombre_hoja)
        except Exception:
            # La hoja no existe, crearla
            hoja_novedades = libro.add_worksheet(title=nombre_hoja, rows=1000, cols=15)
            # Agregar headers
            headers = [
                'FECHA_REGISTRO', 'SUPERVISOR', 'SEDE', 'CEDULA',
                'NOMBRE_COLABORADOR', 'FECHA', 'DIA', 'HORA_INICIAL',
                'HORA_FINAL', 'OBSERVACION', 'ESTADO', 'PROCESADO_POR'
            ]
            hoja_novedades.update('A1:L1', [headers])
            logger.info(f"Hoja '{nombre_hoja}' creada exitosamente")

        # Preparar la fila a insertar
        fecha_registro = datetime.now().strftime('%d/%m/%Y %H:%M')
        nueva_fila = [
            fecha_registro,
            data.get('SUPERVISOR', ''),
            data.get('DESCRIPCION_PROYECTO', data.get('SEDE', '')),
            data.get('CEDULA', ''),
            data.get('NOMBRE_COLABORADOR', ''),
            data.get('FECHA', ''),
            data.get('DIA', ''),
            data.get('HORA_INICIAL', ''),
            data.get('HORA_FINAL', ''),
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