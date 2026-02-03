from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .google_sheets import GoogleSheetsService
from .nomina_cali_service import NominaCaliService
import logging
from datetime import datetime
from collections import defaultdict
from .views import (
    MESES,
    _parsear_fecha,
    _calcular_horas_desde_rango,
    _parsear_horas_formato
)

logger = logging.getLogger(__name__)

@login_required
def nomina_cali(request):
    """Vista para Nómina Cali con calendario y novedades de ambas hojas"""
    import calendar
    from datetime import date
    from .constantes import obtener_id_hoja

    # Obtener filtros
    filtro_mes = request.GET.get('mes', '')
    filtro_supervisor = request.GET.get('supervisor', '')
    filtro_sede = request.GET.get('sede', '')
    filtro_ubicacion = request.GET.get('ubicacion', 'CALI').upper()
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
        'titulo': f'Nómina {filtro_ubicacion.capitalize()}',
        'filtros': {
            'mes': filtro_mes,
            'supervisor': filtro_supervisor,
            'sede': filtro_sede,
            'dias': dias_seleccionados,
            'ubicacion': filtro_ubicacion
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
        'dias_con_nomina': set(),
        'dias_con_facturacion': set(),
        'error_message': None,
        'asistencia_data': {}  # Valor por defecto dict vacío
    }

    # Inicializar variables para evitar NameError
    datos_nomina = None
    datos_novedades = None

    try:
        service = GoogleSheetsService()
        sheet_id = obtener_id_hoja(filtro_ubicacion)
        libro = service.abrir_libro(sheet_id)

        # ========== 0. OBTENER HORARIOS DE SEDE (NUEVO) ==========
        horarios_map = {}
        try:
            # Usamos NominaCaliService para reutilizar su lógica de lectura de horarios
            nomina_service = NominaCaliService(sede=filtro_ubicacion)
            raw_horarios = nomina_service.obtener_horarios()
            
            # Aplanar horarios para visualización fácil: "A: 07:00 - 15:00 / B: ..."
            for sede_nm, turnos in raw_horarios.items():
                desc_turnos = []
                for t in turnos:
                    # Formato: "A: 07:00-15:00" o solo "07:00-15:00" si solo hay uno
                    h_str = f"{t.get('hora_entrada', '')}-{t.get('hora_salida', '')}"
                    if len(turnos) > 1:
                        desc_turnos.append(f"{t.get('turno', '')}: {h_str}")
                    else:
                        desc_turnos.append(h_str)
                
                horarios_map[sede_nm] = " / ".join(desc_turnos)
        except Exception as e:
            logger.error(f"Error cargando horarios: {e}")


        # ========== 1. NOVEDADES DE NOMINA_CALI (NOVEDAD=SI) - AGRUPADAS ==========
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
                idx_cedula = headers_dict.get('CEDULA', -1)
                idx_observaciones = headers_dict.get('OBSERVACIONES', -1)
                idx_total_horas = headers_dict.get('TOTALHORAS', -1)

                # Diccionario para agrupar novedades por (cedula, tipo, observacion)
                novedades_agrupadas = {}

                for fila in datos_nomina[1:]:
                    if len(fila) <= max(idx_fecha, idx_novedad):
                        continue

                    fecha_str = fila[idx_fecha] if idx_fecha != -1 else ''
                    dia, mes, año = _parsear_fecha(fecha_str)

                    # Filtrar por mes global (para marcar el calendario)
                    if not dia or not mes:
                        continue
                    if mes != filtro_mes:
                        continue

                    # Agregar día a conjunto de nómina (hay registro ese día)
                    context['dias_con_nomina'].add(int(dia))

                    novedad_val = str(fila[idx_novedad] if idx_novedad != -1 else '').strip().upper()
                    if novedad_val != 'SI':
                        continue

                    # Agregar día a novedades del calendario
                    context['dias_con_novedades'].add(int(dia))

                    # Obtener datos para filtros y agrupación
                    sup_val = str(fila[idx_supervisor] if idx_supervisor != -1 else '').strip()
                    sede_val = str(fila[idx_desc_proy] if idx_desc_proy != -1 else '').strip()
                    cedula = str(fila[idx_cedula] if idx_cedula != -1 else '').strip()
                    tipo_tiempo = str(fila[idx_tipo] if idx_tipo != -1 else '').strip()
                    observaciones = str(fila[idx_observaciones] if idx_observaciones != -1 else '').strip()
                    nombre = str(fila[idx_nombre] if idx_nombre != -1 else '').strip()

                    # Filtrar por supervisor
                    if filtro_supervisor:
                        if filtro_supervisor.upper() not in sup_val.upper():
                            continue

                    # Filtrar por sede
                    if filtro_sede:
                        if filtro_sede.upper() not in sede_val.upper():
                            continue

                    # Filtrar por días seleccionados
                    if dias_seleccionados:
                        dia_normalizado = str(int(dia))  # "05" -> "5"
                        if dia_normalizado not in dias_seleccionados:
                            continue

                    # Obtener hora inicial y final
                    hora_ini = str(fila[idx_h_ini]).strip() if idx_h_ini != -1 and len(fila) > idx_h_ini else ''
                    hora_fin = str(fila[idx_h_fin]).strip() if idx_h_fin != -1 and len(fila) > idx_h_fin else ''

                    # Calcular horas de este registro dinámicamente desde HORA_INICIAL y HORA_FINAL
                    horas_registro = _calcular_horas_desde_rango(hora_ini, hora_fin)

                    # Clave de agrupación: (cedula, tipo_tiempo, observaciones)
                    # Esto agrupa todos los días de una misma novedad
                    clave_grupo = (cedula, tipo_tiempo, observaciones)

                    if clave_grupo not in novedades_agrupadas:
                        novedades_agrupadas[clave_grupo] = {
                            'nombre': nombre,
                            'descripcion_proyecto': sede_val,
                            'tipo_tiempo': tipo_tiempo,
                            'observaciones': observaciones,
                            'fechas': [],
                            'dias': [],
                            'horas_totales': 0.0,
                            'hora_inicial': '',
                            'hora_final': ''
                        }

                    # Agregar fecha y horas al grupo
                    novedades_agrupadas[clave_grupo]['fechas'].append(fecha_str)
                    novedades_agrupadas[clave_grupo]['dias'].append(int(dia))
                    novedades_agrupadas[clave_grupo]['horas_totales'] += horas_registro

                    # Guardar hora inicial/final del primer registro con horas
                    if hora_ini and not novedades_agrupadas[clave_grupo]['hora_inicial']:
                        novedades_agrupadas[clave_grupo]['hora_inicial'] = hora_ini
                    if hora_fin and not novedades_agrupadas[clave_grupo]['hora_final']:
                        novedades_agrupadas[clave_grupo]['hora_final'] = hora_fin

                # Tipos que deben mostrar 0 horas en el frontend
                TIPOS_SIN_HORAS = ['DIAS NO CLASE', 'NO ASISTENCIA', 'PERMISO NO REMUNERADO']

                # Convertir grupos a lista de tarjetas
                for clave, grupo in novedades_agrupadas.items():
                    dias_ordenados = sorted(grupo['dias'])
                    fechas_ordenadas = sorted(grupo['fechas'])

                    # Determinar rango de fechas
                    if len(fechas_ordenadas) == 1:
                        rango_fechas = fechas_ordenadas[0]
                    else:
                        rango_fechas = f"{fechas_ordenadas[0]} - {fechas_ordenadas[-1]}"

                    # Aplicar regla: mostrar 0 horas para ciertos tipos
                    horas_mostrar = grupo['horas_totales']
                    if grupo['tipo_tiempo'].upper() in [t.upper() for t in TIPOS_SIN_HORAS]:
                        horas_mostrar = 0.0
                    
                    # Buscar horario oficial de la sede
                    horario_oficial = horarios_map.get(grupo['descripcion_proyecto'].upper(), '')

                    context['novedades_nomina'].append({
                        'nombre': grupo['nombre'],
                        'descripcion_proyecto': grupo['descripcion_proyecto'],
                        'tipo_tiempo': grupo['tipo_tiempo'],
                        'observaciones': grupo['observaciones'],
                        'fecha': rango_fechas,
                        'cantidad_dias': len(dias_ordenados),
                        'horas_totales': horas_mostrar,
                        'hora_inicial': grupo['hora_inicial'],
                        'hora_final': grupo['hora_final'],
                        'horario_sede': horario_oficial
                    })
                
                # Ordenar alfabéticamente por nombre
                context['novedades_nomina'].sort(key=lambda x: x['nombre'])

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
                idx_fecha_final = headers_dict.get('FECHAFINAL', -1)
                idx_sede = headers_dict.get('SEDE', -1)
                idx_nombre = headers_dict.get('NOMBRECOLABORADOR', -1)
                idx_h_ini = headers_dict.get('HORAINICIAL', -1)
                idx_h_fin = headers_dict.get('HORAFINAL', -1)
                idx_total = headers_dict.get('TOTALHORAS', -1)
                idx_supervisor = headers_dict.get('SUPERVISOR', -1)
                idx_tipo = headers_dict.get('TIPOTIEMPOLABORADO', -1)
                idx_observaciones = headers_dict.get('OBSERVACIONES', headers_dict.get('OBSERVACION', -1))

                from datetime import timedelta

                for fila in datos_novedades[1:]:
                    if len(fila) <= idx_fecha:
                        continue

                    # Obtener Fechas Crudas
                    fecha_inicio_str = fila[idx_fecha] if idx_fecha != -1 else ''
                    fecha_final_str = str(fila[idx_fecha_final]).strip() if idx_fecha_final != -1 and len(fila) > idx_fecha_final else ''
                    
                    # Parsear rango de fechas completo
                    dt_inicio = None
                    dt_fin = None
                    
                    try:
                        # Intentar parsear inicio
                        # Nota: _parsear_fecha devuelve (dia_str, mes_str, año_str)
                        d, m, a = _parsear_fecha(fecha_inicio_str)
                        if d and m and a:
                            dt_inicio = datetime(int(a), int(m), int(d))
                        
                        # Intentar parsear fin (si no existe o falla, es igual al inicio)
                        if fecha_final_str:
                            d_f, m_f, a_f = _parsear_fecha(fecha_final_str)
                            if d_f and m_f and a_f:
                                dt_fin = datetime(int(a_f), int(m_f), int(d_f))
                        
                        if not dt_fin:
                            dt_fin = dt_inicio

                    except Exception:
                        continue # Si no podemos parsear fechas, saltamos

                    if not dt_inicio:
                        continue

                    # Determinar string de rango para visualización (se mantiene estático para todas las tarjetas generadas)
                    rango_visual = fecha_inicio_str
                    if dt_fin > dt_inicio:
                        rango_visual = f"{fecha_inicio_str} - {fecha_final_str}"

                    # Filtrar por Supervisor y Sede (se aplica al registro general)
                    if filtro_supervisor:
                        sup_val = str(fila[idx_supervisor] if idx_supervisor != -1 else '').upper()
                        if filtro_supervisor.upper() not in sup_val:
                            continue

                    if filtro_sede:
                        sede_val = str(fila[idx_sede] if idx_sede != -1 else '').upper()
                        if filtro_sede.upper() not in sede_val:
                            continue

                    # =======================================================
                    # ITERACIÓN: Expandir el rango día por día
                    # =======================================================
                    curr_dt = dt_inicio
                    while curr_dt <= dt_fin:
                        dia_actual_str = str(curr_dt.day)
                        mes_actual_str = f"{curr_dt.month:02d}" # "02"
                        
                        # 1. Filtro de Mes (Global de la vista)
                        if mes_actual_str != filtro_mes:
                            curr_dt += timedelta(days=1)
                            continue

                        # 2. Agregar al calendario de puntos (independiente del filtro de día)
                        context['dias_con_novedades'].add(curr_dt.day)

                        # 3. Filtro de Días Seleccionados (Checkbox/Clic en calendario)
                        if dias_seleccionados:
                            if str(curr_dt.day) not in dias_seleccionados:
                                curr_dt += timedelta(days=1)
                                continue
                        
                        # Si pasa filtros, agregamos la tarjeta para este día específico
                        sede_actual = str(fila[idx_sede] if idx_sede != -1 else '').strip()
                        horario_oficial = horarios_map.get(sede_actual.upper(), '')

                        context['novedades_cali'].append({
                            'sede': sede_actual,
                            'nombre': fila[idx_nombre] if idx_nombre != -1 else '',
                            'hora_inicial': fila[idx_h_ini] if idx_h_ini != -1 else '',
                            'hora_final': fila[idx_h_fin] if idx_h_fin != -1 else '',
                            'total_horas': fila[idx_total] if idx_total != -1 else '',
                            'fecha': curr_dt.strftime('%d/%m/%Y'), # Fecha específica de este día expandido
                            'rango_fechas': rango_visual,          # Rango original completo (contexto)
                            'tipo_tiempo': fila[idx_tipo] if idx_tipo != -1 and len(fila) > idx_tipo else '',
                            'observaciones': fila[idx_observaciones] if idx_observaciones != -1 and len(fila) > idx_observaciones else '',
                            'horario_sede': horario_oficial
                        })

                        curr_dt += timedelta(days=1)

                # Ordenar alfabéticamente por nombre
                context['novedades_cali'].sort(key=lambda x: x['nombre'])
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

        # Calcular conjuntos para la leyenda
        dias_con_novedades = context['dias_con_novedades']
        dias_con_nomina = context['dias_con_nomina']
        
        context['dias_mixtos'] = list(dias_con_nomina & dias_con_novedades)
        context['dias_solo_nomina'] = list(dias_con_nomina - dias_con_novedades)
        context['dias_solo_novedad'] = list(dias_con_novedades - dias_con_nomina)

        # Convertir sets a listas para el template
        context['dias_con_novedades'] = list(dias_con_novedades)
        context['dias_con_nomina'] = list(dias_con_nomina)
        context['dias_con_facturacion'] = list(context['dias_con_facturacion'])

        # ========== 4. PREPARAR DATOS DETALLADOS PARA EL FRONTEND ==========
        # Diccionario maestro: { cedula_o_nombre: { nombre, sede, registros: [], resumen: {} } }
        # Usaremos la cédula como clave preferida, o el nombre si no hay cédula
        asistencia_map = defaultdict(lambda: {
            'nombre': '', 
            'sede': '', 
            'cedula': '',
            'registros': [],
            'resumen': {'dias_trabajados': 0, 'total_horas': 0.0, 'dias_novedad': 0}
        })

        def _procesar_fuente_para_detalle(datos, headers_d, tipo_fuente):
            """Helper para procesar cada hoja y agregarla al mapa maestro"""
            if not datos or len(datos) < 2: return

            # Detectar índices dinámicamente
            idx_ced = headers_d.get('CEDULA', -1)
            # En facturación a veces no hay cédula, usamos nombre como fallback clave
            idx_nom = headers_d.get('NOMBRECOLABORADOR', -1)
            if idx_nom == -1: idx_nom = headers_d.get('NOMBRE', -1) # Facturación suele tener NOMBRE

            idx_sede = headers_d.get('DESCRIPCIONPROYECTO', -1)
            if idx_sede == -1: idx_sede = headers_d.get('SEDE', -1)
            if idx_sede == -1: idx_sede = headers_d.get('SEDE_EDUCATIVA', -1)

            idx_fecha = headers_d.get('FECHA', -1)
            
            # Específicos
            idx_horas = headers_d.get('TOTALHORAS', -1) # Nomina y Novedades
            idx_novedad = headers_d.get('NOVEDAD', -1)
            idx_tipo = headers_d.get('TIPOTIEMPOLABORADO', -1)
            
            # Horas Inicio/Fin para cálculo dinámico
            idx_h_ini = headers_d.get('HORAINICIAL', -1)
            idx_h_fin = headers_d.get('HORAFINAL', -1)

            for fila in datos[1:]:
                # Obtener clave única (Cédula o Nombre Limpio)
                cedula_raw = str(fila[idx_ced]).strip() if idx_ced != -1 and len(fila) > idx_ced else ''
                # Normalizar cédula para evitar duplicados (quitar puntos, comas, espacios)
                cedula = cedula_raw.replace('.', '').replace(',', '').replace(' ', '')
                
                nombre = str(fila[idx_nom]).strip() if idx_nom != -1 and len(fila) > idx_nom else ''
                
                if not cedula and not nombre: continue
                
                # Clave principal: Cédula. Si no hay, usar Nombre como "cédula temporal"
                clave = cedula if cedula else nombre

                # Validar fecha y mes
                fecha_str = fila[idx_fecha] if idx_fecha != -1 and len(fila) > idx_fecha else ''
                dia, mes, año = _parsear_fecha(fecha_str)
                if not mes or mes != filtro_mes: continue

                # Datos básicos
                sede = str(fila[idx_sede]).strip() if idx_sede != -1 and len(fila) > idx_sede else ''
                
                # Datos numéricos (Horas ya calculadas en hoja)
                horas = 0.0
                if idx_horas != -1 and len(fila) > idx_horas:
                    h_val = str(fila[idx_horas])
                    # Si viene con formato HH:MM (Nómina) o Decimal (Novedades)
                    horas = _parsear_horas_formato(h_val)

                # Obtener horas crudas para recálculo dinámico en frontend
                h_ini = str(fila[idx_h_ini]).strip() if idx_h_ini != -1 and len(fila) > idx_h_ini else ''
                h_fin = str(fila[idx_h_fin]).strip() if idx_h_fin != -1 and len(fila) > idx_h_fin else ''

                # Novedad
                novedad_val = 'NO'
                tipo_val = ''
                if tipo_fuente == 'nomina':
                    if idx_novedad != -1 and len(fila) > idx_novedad:
                        novedad_val = str(fila[idx_novedad]).strip().upper()
                    if idx_tipo != -1 and len(fila) > idx_tipo:
                        tipo_val = str(fila[idx_tipo]).strip()
                elif tipo_fuente == 'novedades':
                    novedad_val = 'SI' # Por definición es novedad
                    if idx_tipo != -1 and len(fila) > idx_tipo:
                        tipo_val = str(fila[idx_tipo]).strip()
                    else:
                        tipo_val = 'Novedad AppSheet' # Fallback
                elif tipo_fuente == 'facturacion':
                    # En facturación asumimos asistencia normal si no dice novedad
                    pass

                # Actualizar Mapa Maestro
                obj = asistencia_map[clave]
                if not obj['nombre'] and nombre: obj['nombre'] = nombre
                if not obj['cedula'] and cedula_raw: obj['cedula'] = cedula_raw # Guardar la visual (con puntos si venía así)
                if not obj['sede'] and sede: obj['sede'] = sede

                # Evitar duplicados exactos de fecha si ya existen (prioridad Nomina > Novedades > Facturacion)
                # Pero aquí simplemente agregamos todo y el frontend decide cómo mostrarlo
                obj['registros'].append({
                    'fuente': tipo_fuente,
                    'fecha': fecha_str,
                    'dia': int(dia),
                    'horas': horas,
                    'hora_ini': h_ini,
                    'hora_fin': h_fin,
                    'novedad': novedad_val,
                    'tipo': tipo_val
                })

                # Actualizar resumen (solo sumar de Nómina para no duplicar stats)
                if tipo_fuente == 'nomina':
                    # Contar días con novedad (independiente de horas)
                    if novedad_val == 'SI':
                        obj['resumen']['dias_novedad'] += 1
                    # Contar días/horas trabajadas (independiente de novedad)
                    # Así un día con accidente que trabajó 11h cuenta en AMBOS
                    if horas > 0:
                        obj['resumen']['dias_trabajados'] += 1
                        obj['resumen']['total_horas'] += horas

        # 1. Procesar Nómina
        try:
            if datos_nomina and len(datos_nomina) > 0:
                # Recalcular headers dict localmente para esta función
                h_dict = {str(h).upper().replace(' ', '').replace('_', '').replace('.', '').strip(): i for i, h in enumerate(datos_nomina[0])}
                _procesar_fuente_para_detalle(datos_nomina, h_dict, 'nomina')
        except Exception as e:
            logger.error(f"Error procesando datos_nomina para detalle: {e}")

        # 2. Procesar Novedades Cali
        try:
            if datos_novedades and len(datos_novedades) > 0:
                h_dict = {str(h).upper().replace(' ', '').replace('_', '').replace('.', '').strip(): i for i, h in enumerate(datos_novedades[0])}
                _procesar_fuente_para_detalle(datos_novedades, h_dict, 'novedades')
        except Exception as e:
            logger.error(f"Error procesando datos_novedades para detalle: {e}")

        # Pasar dict al template (json_script lo serializa automáticamente)
        context['asistencia_data'] = dict(asistencia_map)

        # Debug: log cantidad de colaboradores en el mapa
        logger.info(f"nomina_cali: asistencia_map tiene {len(asistencia_map)} colaboradores")

    except Exception as e:
        logger.error(f"Error en nomina_cali: {e}")
        context['error_message'] = f"Error al conectar con Google Sheets: {str(e)}"

    return render(request, 'tecnicos/nomina_cali.html', context)
