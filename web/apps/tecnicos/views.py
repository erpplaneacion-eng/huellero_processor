from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .google_sheets import GoogleSheetsService
import logging
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


def _parsear_fecha(fecha_str):
    """
    Parsea una fecha en formato DD/MM/YYYY o YYYY-MM-DD.
    Retorna tupla (dia, mes, año) como strings, o (None, None, None) si falla.
    El mes se retorna con cero leading (01, 02, etc.) para comparar con filtros.
    """
    if not fecha_str:
        return None, None, None

    fecha_str = str(fecha_str).strip()

    try:
        if '-' in fecha_str:
            # Formato YYYY-MM-DD
            partes = fecha_str.split('-')
            if len(partes) >= 3:
                año, mes, dia = partes[0], partes[1], partes[2]
                return dia, mes, año
        elif '/' in fecha_str:
            # Formato DD/MM/YYYY
            partes = fecha_str.split('/')
            if len(partes) >= 3:
                dia, mes, año = partes[0], partes[1], partes[2]
                return dia, mes, año
    except:
        pass

    return None, None, None


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
    """Vista para Nómina Cali con calendario y novedades de ambas hojas"""
    import calendar
    from datetime import date

    # Obtener filtros
    filtro_mes = request.GET.get('mes', '')
    filtro_supervisor = request.GET.get('supervisor', '')
    filtro_sede = request.GET.get('sede', '')
    dias_seleccionados = request.GET.getlist('dias')  # Múltiples días

    # Si no hay mes seleccionado, usar el mes actual
    if not filtro_mes:
        filtro_mes = datetime.now().strftime('%m')

    año_actual = datetime.now().year
    mes_num = int(filtro_mes)

    # Generar estructura del calendario
    cal = calendar.Calendar(firstweekday=0)  # Lunes = 0
    dias_mes = []
    for semana in cal.monthdayscalendar(año_actual, mes_num):
        dias_mes.append(semana)

    context = {
        'titulo': 'Nómina Cali',
        'filtros': {
            'mes': filtro_mes,
            'supervisor': filtro_supervisor,
            'sede': filtro_sede,
            'dias': dias_seleccionados
        },
        'meses': MESES,
        'calendario': {
            'mes': mes_num,
            'mes_nombre': MESES[mes_num - 1][1],
            'año': año_actual,
            'semanas': dias_mes,
            'dias_semana': ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do']
        },
        'novedades_nomina': [],
        'novedades_cali': [],
        'dias_con_novedades': set(),
        'dias_con_facturacion': set(),
        'error_message': None
    }

    try:
        service = GoogleSheetsService()
        libro = service.abrir_libro()

        # ========== 1. NOVEDADES DE NOMINA_CALI (NOVEDAD=SI) ==========
        try:
            hoja_nomina = service.obtener_hoja(libro, nombre_hoja='nomina_cali')
            datos_nomina = service.leer_datos(hoja_nomina)

            if datos_nomina and len(datos_nomina) > 0:
                headers = datos_nomina[0]
                headers_dict = {}
                for i, h in enumerate(headers):
                    h_norm = str(h).upper().replace(' ', '').replace('_', '').replace('.', '').strip()
                    headers_dict[h_norm] = i

                # Índices de columnas
                idx_fecha = headers_dict.get('FECHA', -1)
                idx_novedad = headers_dict.get('NOVEDAD', -1)
                idx_desc_proy = headers_dict.get('DESCRIPCIONPROYECTO', -1)
                idx_tipo = headers_dict.get('TIPOTIEMPOLABORADO', -1)
                idx_nombre = headers_dict.get('NOMBRECOLABORADOR', -1)
                idx_h_ini = headers_dict.get('HORAINICIAL', -1)
                idx_h_fin = headers_dict.get('HORAFINAL', -1)
                idx_supervisor = headers_dict.get('SUPERVISOR', -1)

                for fila in datos_nomina[1:]:
                    if len(fila) <= max(idx_fecha, idx_novedad):
                        continue

                    novedad_val = str(fila[idx_novedad] if idx_novedad != -1 else '').strip().upper()
                    if novedad_val != 'SI':
                        continue

                    fecha_str = fila[idx_fecha] if idx_fecha != -1 else ''
                    dia, mes, año = _parsear_fecha(fecha_str)

                    # Filtrar por mes
                    if not dia or not mes:
                        continue
                    if mes != filtro_mes:
                        continue

                    # Agregar día a novedades del calendario
                    context['dias_con_novedades'].add(int(dia))

                    # Filtrar por supervisor
                    if filtro_supervisor:
                        sup_val = str(fila[idx_supervisor] if idx_supervisor != -1 else '').upper()
                        if filtro_supervisor.upper() not in sup_val:
                            continue

                    # Filtrar por sede
                    if filtro_sede:
                        sede_val = str(fila[idx_desc_proy] if idx_desc_proy != -1 else '').upper()
                        if filtro_sede.upper() not in sede_val:
                            continue

                    # Filtrar por días seleccionados
                    if dias_seleccionados:
                        dia_normalizado = str(int(dia))  # "05" -> "5"
                        if dia_normalizado not in dias_seleccionados:
                            continue

                    # Agregar novedad
                    context['novedades_nomina'].append({
                        'descripcion_proyecto': fila[idx_desc_proy] if idx_desc_proy != -1 else '',
                        'tipo_tiempo': fila[idx_tipo] if idx_tipo != -1 else '',
                        'nombre': fila[idx_nombre] if idx_nombre != -1 else '',
                        'hora_inicial': fila[idx_h_ini] if idx_h_ini != -1 else '',
                        'hora_final': fila[idx_h_fin] if idx_h_fin != -1 else '',
                        'fecha': fecha_str
                    })
        except Exception as e:
            logger.error(f"Error leyendo nomina_cali: {e}")

        # ========== 2. NOVEDADES DE NOVEDADES_CALI ==========
        try:
            hoja_novedades = service.obtener_hoja(libro, nombre_hoja='novedades_cali')
            datos_novedades = service.leer_datos(hoja_novedades)

            if datos_novedades and len(datos_novedades) > 0:
                headers = datos_novedades[0]
                headers_dict = {}
                for i, h in enumerate(headers):
                    h_norm = str(h).upper().replace(' ', '').replace('_', '').replace('.', '').strip()
                    headers_dict[h_norm] = i

                idx_fecha = headers_dict.get('FECHA', -1)
                idx_sede = headers_dict.get('SEDE', -1)
                idx_nombre = headers_dict.get('NOMBRECOLABORADOR', -1)
                idx_h_ini = headers_dict.get('HORAINICIAL', -1)
                idx_h_fin = headers_dict.get('HORAFINAL', -1)
                idx_total = headers_dict.get('TOTALHORAS', -1)
                idx_supervisor = headers_dict.get('SUPERVISOR', -1)

                for fila in datos_novedades[1:]:
                    if len(fila) <= idx_fecha:
                        continue

                    fecha_str = fila[idx_fecha] if idx_fecha != -1 else ''
                    dia, mes, año = _parsear_fecha(fecha_str)

                    # Filtrar por mes
                    if not dia or not mes:
                        continue
                    if mes != filtro_mes:
                        continue

                    # Agregar día a novedades del calendario
                    context['dias_con_novedades'].add(int(dia))

                    # Filtrar por supervisor
                    if filtro_supervisor:
                        sup_val = str(fila[idx_supervisor] if idx_supervisor != -1 else '').upper()
                        if filtro_supervisor.upper() not in sup_val:
                            continue

                    # Filtrar por sede
                    if filtro_sede:
                        sede_val = str(fila[idx_sede] if idx_sede != -1 else '').upper()
                        if filtro_sede.upper() not in sede_val:
                            continue

                    # Filtrar por días seleccionados
                    if dias_seleccionados:
                        dia_normalizado = str(int(dia))  # "05" -> "5"
                        if dia_normalizado not in dias_seleccionados:
                            continue

                    context['novedades_cali'].append({
                        'sede': fila[idx_sede] if idx_sede != -1 else '',
                        'nombre': fila[idx_nombre] if idx_nombre != -1 else '',
                        'hora_inicial': fila[idx_h_ini] if idx_h_ini != -1 else '',
                        'hora_final': fila[idx_h_fin] if idx_h_fin != -1 else '',
                        'total_horas': fila[idx_total] if idx_total != -1 else '',
                        'fecha': fecha_str
                    })
        except Exception as e:
            logger.error(f"Error leyendo novedades_cali: {e}")

        # ========== 3. DÍAS CON FACTURACIÓN ==========
        try:
            hoja_fact = service.obtener_hoja(libro, nombre_hoja='facturacion')
            datos_fact = service.leer_datos(hoja_fact)

            if datos_fact and len(datos_fact) > 0:
                headers = datos_fact[0]
                headers_dict = {}
                for i, h in enumerate(headers):
                    h_norm = str(h).upper().replace(' ', '').replace('_', '').replace('.', '').strip()
                    headers_dict[h_norm] = i

                idx_fecha = headers_dict.get('FECHA', -1)

                for fila in datos_fact[1:]:
                    if len(fila) <= idx_fecha or idx_fecha == -1:
                        continue

                    fecha_str = fila[idx_fecha]
                    dia, mes, año = _parsear_fecha(fecha_str)

                    if dia and mes and mes == filtro_mes:
                        context['dias_con_facturacion'].add(int(dia))
        except Exception as e:
            logger.error(f"Error leyendo facturacion: {e}")

        # Convertir sets a listas para el template
        context['dias_con_novedades'] = list(context['dias_con_novedades'])
        context['dias_con_facturacion'] = list(context['dias_con_facturacion'])

    except Exception as e:
        logger.error(f"Error en nomina_cali: {e}")
        context['error_message'] = f"Error al conectar con Google Sheets: {str(e)}"

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