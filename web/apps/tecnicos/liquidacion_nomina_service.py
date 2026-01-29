"""
Servicio de Liquidación de Nómina
Cruza nomina_cali con facturacion para generar liquidación de pagos
Corporación Hacia un Valle Solidario
"""

import os
from datetime import datetime, date, timedelta
from apps.tecnicos.google_sheets import GoogleSheetsService


class LiquidacionNominaService:
    """Servicio para generar liquidación de nómina cruzando nomina_cali con facturacion"""

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

    # Encabezados de la hoja
    HEADERS = [
        'SUPERVISOR',
        'CEDULA',
        'NOMBRE COLABORADOR',
        'SEDE',
        'FECHA',
        'DIA',
        'HORA INICIAL',
        'HORA FINAL',
        'TOTAL HORAS',
        'HUBO_RACIONES',
        'COMPLEMENTO AM/PM',
        'COMPLEMENTO PM',
        'ALMUERZO JU',
        'INDUSTRIALIZADO',
        'TOTAL RACIONES',
        'OBSERVACION'
    ]

    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.sheet_id = os.environ.get('GOOGLE_SHEET_ID')
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
                    'industrializado': reg.get('COMPLEMENTO_AM_PM_INDUSTRIALIZADO', 0) or 0
                }

        return facturacion_por_sede

    def calcular_horas(self, hora_inicial, hora_final):
        """Calcula el total de horas entre dos horarios"""
        try:
            if not hora_inicial or not hora_final:
                return ''

            # Parsear horas (pueden venir como "5:30:00" o "05:30:00")
            def parse_hora(h):
                h = str(h).strip()
                if not h:
                    return None
                partes = h.split(':')
                horas = int(partes[0])
                minutos = int(partes[1]) if len(partes) > 1 else 0
                return horas * 60 + minutos  # Retornar en minutos

            inicio_min = parse_hora(hora_inicial)
            fin_min = parse_hora(hora_final)

            if inicio_min is None or fin_min is None:
                return ''

            # Calcular diferencia
            diff_min = fin_min - inicio_min
            if diff_min < 0:
                diff_min += 24 * 60  # Ajustar si cruza medianoche

            horas = diff_min // 60
            minutos = diff_min % 60

            return f"{horas}:{minutos:02d}"

        except Exception:
            return ''

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
            hoja.update('A1:P1', [self.HEADERS])
            print(f"Hoja '{self.NOMBRE_HOJA}' creada con encabezados")
            return hoja

    def generar_liquidacion_dia(self, fecha=None):
        """
        Genera la liquidación cruzando nomina_cali con facturacion para un día

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

        # Obtener datos
        nomina = self.obtener_nomina_cali(fecha)
        facturacion = self.obtener_facturacion(fecha)

        if not nomina:
            return [], f"No hay registros en nomina_cali para {fecha_str}"

        # Generar registros cruzados
        registros = []
        for emp in nomina:
            sede = emp.get('DESCRIPCION PROYECTO', '').strip()
            sede_upper = sede.upper()

            # Buscar facturación de esta sede
            fact = facturacion.get(sede_upper, {})

            comp_ampm = fact.get('complemento_ampm', 0)
            comp_pm = fact.get('complemento_pm', 0)
            almuerzo = fact.get('almuerzo_ju', 0)
            industrializado = fact.get('industrializado', 0)

            total_raciones = comp_ampm + comp_pm + almuerzo + industrializado
            hubo_raciones = 'SI' if total_raciones > 0 else 'NO'
            observacion = '' if total_raciones > 0 else 'ASEO/LIMPIEZA'

            hora_inicial = emp.get('HORA INICIAL', '')
            hora_final = emp.get('HORA FINAL', '')
            total_horas = self.calcular_horas(hora_inicial, hora_final)

            registro = [
                emp.get('SUPERVISOR', ''),      # SUPERVISOR
                emp.get('CEDULA', ''),          # CEDULA
                emp.get('NOMBRE COLABORADOR', ''),  # NOMBRE COLABORADOR
                sede,                            # SEDE
                emp.get('FECHA', ''),           # FECHA
                emp.get('DIA', ''),             # DIA
                hora_inicial,                    # HORA INICIAL
                hora_final,                      # HORA FINAL
                total_horas,                     # TOTAL HORAS
                hubo_raciones,                   # HUBO_RACIONES
                comp_ampm,                       # COMPLEMENTO AM/PM
                comp_pm,                         # COMPLEMENTO PM
                almuerzo,                        # ALMUERZO JU
                industrializado,                 # INDUSTRIALIZADO
                total_raciones,                  # TOTAL RACIONES
                observacion                      # OBSERVACION
            ]
            registros.append(registro)

        return registros, f"Generados {len(registros)} registros de liquidación para {fecha_str}"

    def verificar_registros_existentes(self, fecha):
        """Verifica si ya existen registros para una fecha"""
        hoja = self.crear_hoja_si_no_existe()
        datos = hoja.get_all_values()

        fecha_str = fecha.strftime('%Y-%m-%d')

        # Buscar si hay registros con esta fecha (columna 5 = FECHA, índice 4)
        for fila in datos[1:]:  # Skip header
            if len(fila) > 4 and fila[4] == fecha_str:
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
        rango = f"A{ultima_fila}:P{ultima_fila + len(registros) - 1}"
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


def ejecutar_liquidacion_hoy():
    """Función helper para ejecutar liquidación del día actual"""
    service = LiquidacionNominaService()
    resultado = service.ejecutar_liquidacion_diaria()
    return resultado


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    resultado = ejecutar_liquidacion_hoy()
    print(f"Resultado: {resultado}")
