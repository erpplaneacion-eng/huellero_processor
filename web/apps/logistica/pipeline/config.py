"""
Configuración del Sistema Procesador de Huellero
Corporación Hacia un Valle Solidario
"""

import os
from pathlib import Path

# ========== CONFIGURACIÓN DE ARCHIVOS ==========

# Directorio raíz del proyecto (huellero_processor/)
# pipeline/ → logistica/ → apps/ → web/ → huellero_processor/
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

# Rutas de directorios (rutas absolutas)
DIR_INPUT = BASE_DIR / "data" / "input"
DIR_OUTPUT = BASE_DIR / "data" / "output"
DIR_MAESTRO = BASE_DIR / "data" / "maestro"
DIR_LOGS = BASE_DIR / "logs"

# Crear directorios si no existen
for _dir in [DIR_INPUT, DIR_OUTPUT, DIR_MAESTRO, DIR_LOGS]:
    _dir.mkdir(parents=True, exist_ok=True)

# Nombres de archivos
ARCHIVO_MAESTRO = "empleados.xlsx"
PREFIJO_OUTPUT = "REPORTE_ASISTENCIA"

# ========== CONFIGURACIÓN DE PROCESAMIENTO ==========

# Umbrales de tiempo (en segundos)
UMBRAL_DUPLICADOS = 900  # 15 minutos - marcaciones más cercanas se consideran duplicadas
UMBRAL_MISMO_TURNO = 3600  # 1 hora - para agrupar marcaciones del mismo turno

# Validación de horas laboradas
HORAS_MINIMAS_TURNO = 4
HORAS_MAXIMAS_TURNO = 16
HORAS_NORMALES_MIN = 8
HORAS_NORMALES_MAX = 13
HORAS_LIMITE_JORNADA = 9.8  # Límite máximo de horas por jornada laboral

# ========== CONFIGURACIÓN DE TURNOS ==========

# Horarios para clasificación AM/PM
HORA_INICIO_AM = 6  # 06:00
HORA_FIN_AM = 12    # 11:59

HORA_INICIO_PM = 12  # 12:00
HORA_FIN_PM = 24     # 23:59

# Horarios para inferencia de estados (fallback cuando no hay horario de cargo)
# Si una marcación sin estado ocurre en estos rangos, se infiere como:
RANGO_INFERENCIA_ENTRADA = [(3, 11)]   # 03:00 a 11:00 -> probablemente ENTRADA
RANGO_INFERENCIA_SALIDA = [(14, 21)]   # 14:00 a 21:00 -> probablemente SALIDA

# Tolerancia para inferencia por horario de cargo (en minutos por extremo)
# Si la desviación del mejor turno supera este valor, se descarta la inferencia
# y se usa el fallback (rangos globales arriba)
TOLERANCIA_HORARIO_MIN = 90  # 1.5 horas por extremo

# Definición de turno nocturno (hora de inicio)
HORA_INICIO_TURNO_NOCTURNO = 19.0  # A partir de las 19:00 se considera inicio de nocturno
HORA_SALIDA_ESTANDAR_NOCTURNA = 6   # 06:00 AM como salida estándar si se olvida marcar

# ========== CONFIGURACIÓN DE OBSERVACIONES ==========

OBSERVACIONES = {
    'OK': 'Sin observaciones',
    'TURNO_NOCTURNO': 'Turno nocturno',
    'SALIDA_NR': 'Salida no registrada',
    'ENTRADA_NR': 'Entrada no registrada',
    'ESTADO_INFERIDO': 'Estado inferido por contexto',
    'DUPLICADOS_ELIM': 'Duplicados eliminados',
    'MULT_ENTRADAS': 'Múltiples entradas',
    'MULT_SALIDAS': 'Múltiples salidas',
    'TURNO_LARGO': 'ALERTA: Turno mayor a 14 horas',
    'TURNO_CORTO': 'ALERTA: Turno menor a 6 horas',
    'EXCEDE_JORNADA': 'ALERTA: Excede límite de jornada (9.8 horas)',
    'DATOS_CORRUPTOS': 'ALERTA: Datos empleado requieren corrección',
    'TRABAJO_DOMINICAL': 'Trabajo dominical',
    'REQUIERE_REVISION': 'Requiere revisión manual',
    'SIN_MARCACIONES': 'Sin marcaciones registradas',
    'SALIDA_CORREGIDA': 'Marcación de salida corregida - empleado registró Entrada en lugar de Salida',
    'NOCTURNO_PROSPECTIVO': 'Turno nocturno detectado por entrada PM y salida AM del día siguiente',
    'SALIDA_ESTANDAR_NOCTURNA': 'Turno nocturno | Salida Inferida Estándar (6 AM)',
    'CASTIGO_MARCACION_INCORRECTA_DIURNO': 'Castigo por marcación incorrecta: turno liquidado como diurno',
    'SIN_REGISTROS': 'SIN REGISTROS'
}

# ========== REGLA ESPECIAL VIGILANTES (CASTIGO) ==========
# Solo para estos códigos: si tienen marca AM + PM el mismo día,
# se liquida como turno diurno para castigar mala marcación.
VIGILANTE_CASTIGO_HABILITADO = True
VIGILANTE_CASTIGO_CODIGOS = [4, 129, 130, 135]
VIGILANTE_VENTANA_AM = (3.5, 6.0)   # 03:30 - 06:00
VIGILANTE_VENTANA_PM = (15.5, 18.0) # 15:30 - 18:00

# ========== CONFIGURACIÓN DE COLUMNAS EXCEL ==========

COLUMNAS_OUTPUT = [
    'CODIGO COLABORADOR',
    'NOMBRE COMPLETO DEL COLABORADOR',
    'DOCUMENTO DEL COLABORADOR',
    'FECHA',
    'DIA',
    '# MARCACIONES AM',
    '# MARCACIONES PM',
    'HORA DE INGRESO',
    'HORA DE SALIDA',
    'TOTAL HORAS LABORADAS',
    'LÍMITE HORAS DÍA',
    'OBSERVACION',
    'CARGO',
    'OBSERVACIONES_1'
]

# Columnas del archivo maestro (si existe)
COLUMNAS_MAESTRO = {
    'codigo': 'CODIGO',
    'nombre': 'NOMBRE',
    'documento': 'DOCUMENTO',
    'cargo': 'CARGO'  # opcional
}

# ========== CONFIGURACIÓN DE FORMATO EXCEL ==========

# Colores para formato condicional (RGB hex)
COLORES = {
    'VERDE': '#C6EFCE',      # OK
    'AMARILLO': '#FFEB9C',   # Advertencia
    'NARANJA': '#FFC7CE',    # Observaciones normales
    'ROJO': '#FF0000',       # Alertas críticas
    'AZUL': '#DDEBF7',       # Turno nocturno
    'MORADO': '#E1BEE7',     # Salida estándar nocturna (Violeta claro)
    'GRIS': '#D9D9D9'        # Sin datos
}

# Anchos de columna (en caracteres)
ANCHOS_COLUMNAS = {
    'CODIGO COLABORADOR': 18,
    'NOMBRE COMPLETO DEL COLABORADOR': 35,
    'DOCUMENTO DEL COLABORADOR': 20,
    'CARGO': 25,
    'FECHA': 12,
    'DIA': 12,
    '# MARCACIONES AM': 18,
    '# MARCACIONES PM': 18,
    'HORA DE INGRESO': 16,
    'HORA DE SALIDA': 16,
    'TOTAL HORAS LABORADAS': 20,
    'LÍMITE HORAS DÍA': 18,
    'OBSERVACION': 50,
    'OBSERVACIONES_1': 40
}

# ========== CONFIGURACIÓN DE FORMATO DE FECHAS ==========

FORMATO_FECHA_INPUT = '%d/%m/%Y %H:%M'  # Formato en archivo de entrada
FORMATO_FECHA_OUTPUT = '%d/%m/%Y'       # Formato en archivo de salida
FORMATO_HORA_OUTPUT = '%H:%M'           # Formato de hora en salida
FORMATO_ARCHIVO = '%Y%m%d_%H%M%S'       # Formato para nombres de archivo

# Nombres de días en español
DIAS_SEMANA = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado',
    6: 'Domingo'
}

# ========== CONFIGURACIÓN DE LOGGING ==========

LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# ========== CONFIGURACIÓN AVANZADA ==========

# Permitir inferencia de estados
PERMITIR_INFERENCIA = True

# Eliminar automáticamente duplicados
ELIMINAR_DUPLICADOS_AUTO = True

# Generar hoja de resumen en Excel
GENERAR_HOJA_RESUMEN = True

# Generar archivo de casos especiales
GENERAR_CASOS_ESPECIALES = True

# Validar datos de empleado (nombre igual a código)
VALIDAR_DATOS_EMPLEADO = True

# ========== MENSAJES DEL SISTEMA ==========

MENSAJES = {
    'inicio': '🕐 Iniciando procesamiento de archivo de huellero...',
    'carga_exitosa': '✅ Archivo cargado exitosamente',
    'limpieza_completa': '🧹 Limpieza de datos completada',
    'inferencia_completa': '🧠 Inferencia de estados completada',
    'turnos_construidos': '🔨 Turnos construidos exitosamente',
    'calculo_completo': '🔢 Cálculo de horas completado',
    'excel_generado': '📊 Archivo Excel generado',
    'proceso_completo': '✅ Procesamiento completado exitosamente',
    'error_archivo': '❌ Error al procesar archivo',
    'sin_datos': '⚠️ No se encontraron datos para procesar'
}
