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


def _parsear_hora_a_minutos(hora_str):
    """
    Parsea una hora en varios formatos y retorna minutos desde medianoche.
    Soporta: HH:MM, HH:MM:SS, "5:30:00 a. m.", "1:30:00 p. m.", etc.
    Retorna None si no puede parsear.
    """
    import re

    if not hora_str or hora_str == '-':
        return None

    hora_str = str(hora_str).strip().lower()

    # Detectar AM/PM con regex para formatos: pm, p.m, p.m., p. m., p. m
    es_pm = False
    es_am = False

    if re.search(r'p\.?\s?m\.?', hora_str):
        es_pm = True
        hora_str = re.sub(r'p\.?\s?m\.?', '', hora_str).strip()
    elif re.search(r'a\.?\s?m\.?', hora_str):
        es_am = True
        hora_str = re.sub(r'a\.?\s?m\.?', '', hora_str).strip()

    # Separar por :
    partes = hora_str.split(':')
    if len(partes) < 2:
        return None

    try:
        horas = int(partes[0])
        minutos = int(partes[1])
    except ValueError:
        return None

    # Convertir 12h a 24h si es necesario
    if es_pm and horas < 12:
        horas += 12
    elif es_am and horas == 12:
        horas = 0

    return horas * 60 + minutos


def _calcular_horas_desde_rango(hora_ini, hora_fin):
    """
    Calcula la diferencia de horas entre hora inicial y final.
    Retorna el valor en horas decimales (ej: 5.5).
    Maneja turnos nocturnos (cuando hora_fin < hora_ini).
    """
    min_ini = _parsear_hora_a_minutos(hora_ini)
    min_fin = _parsear_hora_a_minutos(hora_fin)

    if min_ini is None or min_fin is None:
        return 0.0

    diff = min_fin - min_ini

    # Manejar turnos nocturnos (salida al día siguiente)
    if diff < 0:
        diff += 24 * 60  # Agregar 24 horas

    return diff / 60.0  # Convertir a horas


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
