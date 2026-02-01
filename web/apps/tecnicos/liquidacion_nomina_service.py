"""
Servicio de Liquidación de Nómina
Cruza nomina_cali con facturacion para generar liquidación de pagos
Agrupado por SEDE (no por manipuladora)
Corporación Hacia un Valle Solidario
"""

import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from apps.tecnicos.google_sheets import GoogleSheetsService
from apps.tecnicos.constantes import obtener_id_hoja


class LiquidacionNominaService:
    """Servicio para generar liquidación de nómina agrupada por sede"""

    DIAS_SEMANA = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    NOMBRE_HOJA = 'liquidacion_nomina'

    # Encabezados de la hoja (agrupado por sede)
    HEADERS = [
        'ID',
        'SUPERVISOR',
        'SEDE',
        'FECHA',
        'DIA',
        'CANT. MANIPULADORAS',
        'TOTAL HORAS',
        'HUBO_RACIONES',
        'COMPLEMENTO AM/PM',
        'COMPLEMENTO PM',
        'ALMUERZO JU',
        'INDUSTRIALIZADO',
        'TOTAL RACIONES',
        'OBSERVACION',
        'NOVEDAD'
    ]

    def __init__(self, sede='CALI'):
        self.sede = sede
        self.sheets_service = GoogleSheetsService()
        self.sheet_id = obtener_id_hoja(sede)
        self.libro = self.sheets_service.abrir_libro(self.sheet_id)

    def obtener_nomina_cali(self, fecha=None):
        """Obtiene los registros de nomina_cali para una fecha específica"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'nomina_cali')
        datos = hoja.get_all_records()

        if fecha:
            fecha_str = fecha.strftime('%Y-%m-%d')
            datos = [d for d in datos if d.get('FECHA') == fecha_str]

        return datos

    def obtener_facturacion(self, fecha=None):
        """Obtiene los registros de facturacion para una fecha específica"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'facturacion')
        datos = hoja.get_all_records()

        if fecha:
            fecha_str = fecha.strftime('%Y-%m-%d')
            datos = [d for d in datos if d.get('FECHA') == fecha_str]

        # Crear diccionario por sede para búsqueda rápida
        facturacion_por_sede = {}
        for reg in datos:
            # La columna se llama SEDE_EDUCATIVA en facturacion
            sede = reg.get('SEDE_EDUCATIVA', '').strip().upper()
            if sede:
                facturacion_por_sede[sede] = {
                    'complemento_ampm': reg.get('COMPLEMENTO_AM_PM_PREPARADO', 0) or 0,
                    'complemento_pm': reg.get('COMPLEMENTO_PM_PREPARADO', 0) or 0,
                    'almuerzo_ju': reg.get('ALMUERZO_JORNADA_UNICA', 0) or 0,
                    'industrializado': reg.get('COMPLEMENTO_AM_PM_INDUSTRIALIZADO', 0) or 0,
                    'novedad_fact': reg.get('NOVEDAD', '')
                }

        return facturacion_por_sede

    def calcular_horas_en_minutos(self, hora_inicial, hora_final):
        """Calcula el total de minutos entre dos horarios"""
        try:
            if not hora_inicial or not hora_final:
                return 0

            def parse_hora(h):
                h = str(h).strip()
                if not h:
                    return None
                partes = h.split(':')
                horas = int(partes[0])
                minutos = int(partes[1]) if len(partes) > 1 else 0
                return horas * 60 + minutos

            inicio_min = parse_hora(hora_inicial)
            fin_min = parse_hora(hora_final)

            if inicio_min is None or fin_min is None:
                return 0

            diff_min = fin_min - inicio_min
            if diff_min < 0:
                diff_min += 24 * 60

            return diff_min

        except Exception:
            return 0

    def minutos_a_horas(self, minutos):
        """Convierte minutos a formato HH:MM"""
        if minutos == 0:
            return ''
        horas = minutos // 60
        mins = minutos % 60
        return f"{horas}:{mins:02d}"

    def crear_hoja_si_no_existe(self):
        """Crea la hoja liquidacion_nomina si no existe y agrega los encabezados"""
        try:
            hoja = self.sheets_service.obtener_hoja(self.libro, self.NOMBRE_HOJA)
            return hoja
        except Exception:
            # La hoja no existe, crearla
            hoja = self.libro.add_worksheet(
                title=self.NOMBRE_HOJA,
                rows=1000,
                cols=len(self.HEADERS)
            )
            # Agregar encabezados
            hoja.update(values=[self.HEADERS], range_name='A1:O1')
            print(f"Hoja '{self.NOMBRE_HOJA}' creada con encabezados")
            return hoja

    def generar_liquidacion_dia(self, fecha=None):
        """
        Genera la liquidación agrupada por sede

        Args:
            fecha: date object, si es None usa fecha actual

        Returns:
            tuple: (registros_generados, mensaje)
        """
        if fecha is None:
            fecha = date.today()

        # Verificar si es domingo (no hay registros)
        dia_semana_num = fecha.weekday()
        if dia_semana_num == 6:  # Domingo
            return [], f"No hay registros para domingos ({fecha})"

        fecha_str = fecha.strftime('%Y-%m-%d')
        dia_semana = self.DIAS_SEMANA[dia_semana_num]

        # Obtener datos
        nomina = self.obtener_nomina_cali(fecha)
        facturacion = self.obtener_facturacion(fecha)

        if not nomina:
            return [], f"No hay registros en nomina_cali para {fecha_str}"

        # Agrupar por sede
        sedes_agrupadas = defaultdict(lambda: {
            'supervisor': '',
            'cantidad_manipuladoras': 0,
            'total_minutos': 0,
            'tiene_novedad': False
        })

        for emp in nomina:
            sede = emp.get('DESCRIPCION PROYECTO', '').strip()
            sede_key = sede.upper()

            # Acumular datos
            sedes_agrupadas[sede_key]['sede_original'] = sede
            sedes_agrupadas[sede_key]['supervisor'] = emp.get('SUPERVISOR', '')
            sedes_agrupadas[sede_key]['cantidad_manipuladoras'] += 1

            # Sumar horas
            hora_inicial = emp.get('HORA INICIAL', '')
            hora_final = emp.get('HORA FINAL', '')
            minutos = self.calcular_horas_en_minutos(hora_inicial, hora_final)
            sedes_agrupadas[sede_key]['total_minutos'] += minutos

            # Verificar si hay novedad
            if emp.get('NOVEDAD', '').strip().upper() == 'SI':
                sedes_agrupadas[sede_key]['tiene_novedad'] = True

        # Generar registros agrupados
        registros = []
        consecutivo = 1
        for sede_key, datos_sede in sedes_agrupadas.items():
            sede = datos_sede.get('sede_original', sede_key)

            # Buscar facturación de esta sede
            fact = facturacion.get(sede_key, {})

            comp_ampm = fact.get('complemento_ampm', 0)
            comp_pm = fact.get('complemento_pm', 0)
            almuerzo = fact.get('almuerzo_ju', 0)
            industrializado = fact.get('industrializado', 0)

            total_raciones = comp_ampm + comp_pm + almuerzo + industrializado
            hubo_raciones = 'SI' if total_raciones > 0 else 'NO'
            observacion = '' if total_raciones > 0 else 'ASEO/LIMPIEZA'

            # Verificar novedad (de nomina o facturacion)
            novedad_nomina = datos_sede['tiene_novedad']
            novedad_fact = fact.get('novedad_fact', '').strip().upper() == 'SI'
            novedad = 'SI' if (novedad_nomina or novedad_fact) else ''

            total_horas = self.minutos_a_horas(datos_sede['total_minutos'])
            
            # Generar ID
            id_registro = f"LIQ-{fecha.strftime('%Y%m%d')}-{consecutivo:04d}"
            consecutivo += 1

            registro = [
                id_registro,                        # ID
                datos_sede['supervisor'],           # SUPERVISOR
                sede,                               # SEDE
                fecha_str,                          # FECHA
                dia_semana,                         # DIA
                datos_sede['cantidad_manipuladoras'],  # CANT. MANIPULADORAS
                total_horas,                        # TOTAL HORAS
                hubo_raciones,                      # HUBO_RACIONES
                comp_ampm,                          # COMPLEMENTO AM/PM
                comp_pm,                            # COMPLEMENTO PM
                almuerzo,                           # ALMUERZO JU
                industrializado,                    # INDUSTRIALIZADO
                total_raciones,                     # TOTAL RACIONES
                observacion,                        # OBSERVACION
                novedad                             # NOVEDAD
            ]
            registros.append(registro)

        # Ordenar por supervisor y sede
        registros.sort(key=lambda x: (x[1], x[2]))

        return registros, f"Generados {len(registros)} registros de liquidación (por sede) para {fecha_str}"

    def verificar_registros_existentes(self, fecha):
        """Verifica si ya existen registros para una fecha"""
        hoja = self.crear_hoja_si_no_existe()
        datos = hoja.get_all_values()

        fecha_str = fecha.strftime('%Y-%m-%d')

        # Buscar si hay registros con esta fecha (columna 4 = FECHA, índice 3)
        for fila in datos[1:]:  # Skip header
            if len(fila) > 3 and fila[3] == fecha_str:
                return True
        return False

    def insertar_registros(self, registros):
        """Inserta los registros en la hoja de liquidación"""
        if not registros:
            return 0

        hoja = self.crear_hoja_si_no_existe()

        # Obtener última fila con datos
        datos_actuales = hoja.get_all_values()
        ultima_fila = len(datos_actuales) + 1

        # Insertar registros
        rango = f"A{ultima_fila}:O{ultima_fila + len(registros) - 1}"
        hoja.update(values=registros, range_name=rango)

        return len(registros)

    def ejecutar_liquidacion_diaria(self, fecha=None, forzar=False):
        """
        Ejecuta el proceso completo de liquidación diaria

        Args:
            fecha: date object, si es None usa fecha actual
            forzar: si es True, crea registros aunque ya existan

        Returns:
            dict con resultado de la operación
        """
        if fecha is None:
            fecha = date.today()

        resultado = {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'dia': self.DIAS_SEMANA.get(fecha.weekday(), ''),
            'exito': False,
            'mensaje': '',
            'registros_creados': 0
        }

        # Verificar domingo
        if fecha.weekday() == 6:
            resultado['mensaje'] = 'No hay registros para domingos'
            resultado['exito'] = True
            return resultado

        # Verificar si ya existen registros
        if not forzar and self.verificar_registros_existentes(fecha):
            resultado['mensaje'] = f'Ya existen registros de liquidación para {fecha}'
            return resultado

        # Generar registros
        registros, mensaje = self.generar_liquidacion_dia(fecha)

        if not registros:
            resultado['mensaje'] = mensaje
            return resultado

        # Insertar registros
        cantidad = self.insertar_registros(registros)

        resultado['exito'] = True
        resultado['mensaje'] = mensaje
        resultado['registros_creados'] = cantidad

        return resultado


def ejecutar_liquidacion_hoy(sede='CALI'):
    """Función helper para ejecutar liquidación del día actual"""
    service = LiquidacionNominaService(sede=sede)
    resultado = service.ejecutar_liquidacion_diaria()
    return resultado


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    resultado = ejecutar_liquidacion_hoy()
    print(f"Resultado: {resultado}")
