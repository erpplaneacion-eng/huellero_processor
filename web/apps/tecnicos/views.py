from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .google_sheets import GoogleSheetsService
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Opciones para el select de meses
MESES = [
    ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'),
    ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
    ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Septiembre'),
    ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
]

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
                
                # Mapa de headers a índices para acceso rápido
                headers_dict = {h.upper(): i for i, h in enumerate(raw_headers)}
                
                # Mapeo de índices para filtros
                def buscar_idx(claves):
                    for clave in claves:
                        if clave.upper() in headers_dict:
                            return headers_dict[clave.upper()]
                    return -1

                idx_supervisor = buscar_idx(columnas_map.get('supervisor', []))
                idx_fecha = buscar_idx(columnas_map.get('fecha', []))
                idx_sede = buscar_idx(columnas_map.get('sede', []))

                # Definir Headers de Salida
                if headers_manuales:
                    headers = headers_manuales
                elif columnas_permitidas:
                    # Usar el nombre exacto solicitado por el usuario, buscando su índice en la hoja
                    headers = []
                    indices_salida = []
                    for cp in columnas_permitidas:
                        idx = headers_dict.get(cp.upper(), -1)
                        if idx != -1:
                            headers.append(cp)
                            indices_salida.append(idx)
                        else:
                            # Si no existe, lo agregamos como header pero marcará vacío
                            headers.append(cp)
                            indices_salida.append(-1)
                else:
                    headers = raw_headers

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
            idx = headers_dict.get(col, -1)
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