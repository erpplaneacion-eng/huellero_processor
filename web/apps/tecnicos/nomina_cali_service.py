"""
Servicio de Nómina Cali
Genera registros diarios de nómina para manipuladoras de Cali
Corporación Hacia un Valle Solidario
"""

import os
from datetime import datetime, date
from apps.tecnicos.google_sheets import GoogleSheetsService


class NominaCaliService:
    """Servicio para generar registros de nómina diaria de Cali"""

    DIAS_SEMANA = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    # Constantes
    MODALIDAD = 'COMPLEMENTO AM/PM PREPARADO'
    TIPO_TIEMPO_LABORADO = 'P. ALIMENTOS'
    NOMBRE_HOJA = 'nomina_cali'

    # Encabezados de la hoja
    HEADERS = [
        'ID',
        'SUPERVISOR',
        'user',
        'MODALIDAD',
        'DESCRIPCION PROYECTO',
        'TIPO TIEMPO LABORADO',
        'CEDULA',
        'NOMBRE COLABORADOR',
        'FECHA',
        'DIA',
        'HORA INICIAL',
        'HORA FINAL',
        'NOVEDAD',
        'FECHA FINAL',
        'DIA FINAL',
        'OBSERVACIONES'
    ]

    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        self.libro = self.sheets_service.abrir_libro(self.sheet_id)

    def obtener_manipuladoras_activas(self):
        """Obtiene las manipuladoras activas de la hoja Manipuladoras"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'Manipuladoras')
        datos = hoja.get_all_records()

        # Filtrar solo activas
        manipuladoras_activas = [
            m for m in datos
            if m.get('Estado', '').strip().lower() == 'activo'
            and m.get('Nombre')
            and m.get('No. Documento')
        ]
        return manipuladoras_activas

    def obtener_supervisores(self):
        """Obtiene los supervisores con su user (correo)"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'sedes_supevisor')
        datos = hoja.get_all_records()

        # Crear diccionario por nombre de supervisor
        supervisores = {}
        for sup in datos:
            nombre = sup.get('nombre', '').strip()
            if nombre:
                supervisores[nombre.upper()] = {
                    'nombre': nombre,
                    'user': sup.get('user', '')
                }
        return supervisores

    def obtener_horarios(self):
        """Obtiene los horarios por sede"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'HORARIOS')
        datos = hoja.get_all_records()

        # Crear diccionario por nombre de sede
        horarios = {}
        for h in datos:
            sede = h.get('SEDE', '').strip()
            if sede:
                horarios[sede.upper()] = {
                    'hora_entrada': h.get('HORA ENTRADA', ''),
                    'hora_salida': h.get('HORA SALIDA', '')
                }
        return horarios

    def crear_hoja_si_no_existe(self):
        """Crea la hoja nomina_cali si no existe y agrega los encabezados"""
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
            hoja.update(values=[self.HEADERS], range_name='A1:P1')
            print(f"Hoja '{self.NOMBRE_HOJA}' creada con encabezados")
            return hoja

    def generar_registros_dia(self, fecha=None):
        """
        Genera los registros de nómina para un día específico

        Args:
            fecha: date object, si es None usa fecha actual

        Returns:
            tuple: (registros_generados, mensaje)
        """
        if fecha is None:
            fecha = date.today()

        # Verificar si es domingo (no se crean registros)
        dia_semana_num = fecha.weekday()
        if dia_semana_num == 6:  # Domingo
            return [], f"No se crean registros los domingos ({fecha})"

        dia_semana = self.DIAS_SEMANA[dia_semana_num]
        es_sabado = dia_semana_num == 5
        fecha_str = fecha.strftime('%Y-%m-%d')

        # Obtener datos
        manipuladoras = self.obtener_manipuladoras_activas()
        supervisores = self.obtener_supervisores()
        horarios = self.obtener_horarios()

        # Generar registros
        registros = []
        consecutivo = 1
        for manip in manipuladoras:
            # Generar ID único
            id_registro = f"NOM-{fecha.strftime('%Y%m%d')}-{consecutivo:04d}"
            consecutivo += 1

            # Datos de la manipuladora
            nombre = manip.get('Nombre', '')
            cedula = manip.get('No. Documento', '')
            sede = manip.get('sede educativa', '')
            supervisor_nombre = manip.get('SUPERVISOR', '')

            # Buscar user del supervisor
            sup_info = supervisores.get(supervisor_nombre.upper(), {})
            user = sup_info.get('user', '')

            # Buscar horarios de la sede
            horario_sede = horarios.get(sede.upper(), {})

            # Sábados: horas vacías
            if es_sabado:
                hora_entrada = ''
                hora_salida = ''
            else:
                hora_entrada = horario_sede.get('hora_entrada', '')
                hora_salida = horario_sede.get('hora_salida', '')

            registro = [
                id_registro,                # ID
                supervisor_nombre,          # SUPERVISOR
                user,                       # user
                self.MODALIDAD,             # MODALIDAD (constante)
                sede,                       # DESCRIPCION PROYECTO
                self.TIPO_TIEMPO_LABORADO,  # TIPO TIEMPO LABORADO (constante)
                cedula,                     # CEDULA
                nombre,                     # NOMBRE COLABORADOR
                fecha_str,                  # FECHA
                dia_semana,                 # DIA
                hora_entrada,               # HORA INICIAL
                hora_salida,                # HORA FINAL
                '',                         # NOVEDAD (vacío por defecto)
                '',                         # FECHA FINAL (vacío por defecto)
                '',                         # DIA FINAL (vacío por defecto)
                ''                          # OBSERVACIONES (vacío por defecto)
            ]
            registros.append(registro)

        return registros, f"Generados {len(registros)} registros para {dia_semana} {fecha_str}"

    def verificar_registros_existentes(self, fecha):
        """Verifica si ya existen registros para una fecha"""
        hoja = self.crear_hoja_si_no_existe()
        datos = hoja.get_all_values()

        fecha_str = fecha.strftime('%Y-%m-%d')

        # Buscar si hay registros con esta fecha (columna 8 = FECHA, índice 7)
        for fila in datos[1:]:  # Skip header
            if len(fila) > 7 and fila[7] == fecha_str:
                return True
        return False

    def insertar_registros(self, registros):
        """Inserta los registros en la hoja de nómina"""
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

    def ejecutar_nomina_diaria(self, fecha=None, forzar=False):
        """
        Ejecuta el proceso completo de nómina diaria

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
            resultado['mensaje'] = 'No se crean registros los domingos'
            resultado['exito'] = True
            return resultado

        # Verificar si ya existen registros
        if not forzar and self.verificar_registros_existentes(fecha):
            resultado['mensaje'] = f'Ya existen registros para {fecha}'
            return resultado

        # Generar registros
        registros, mensaje = self.generar_registros_dia(fecha)

        if not registros:
            resultado['mensaje'] = mensaje
            return resultado

        # Insertar registros
        cantidad = self.insertar_registros(registros)

        resultado['exito'] = True
        resultado['mensaje'] = mensaje
        resultado['registros_creados'] = cantidad

        return resultado


def ejecutar_nomina_cali_hoy():
    """Función helper para ejecutar nómina del día actual"""
    service = NominaCaliService()
    resultado = service.ejecutar_nomina_diaria()
    return resultado


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    resultado = ejecutar_nomina_cali_hoy()
    print(f"Resultado: {resultado}")
