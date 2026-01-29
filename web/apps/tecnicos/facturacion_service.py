"""
Servicio de Facturación Diaria
Genera registros diarios de raciones por sede educativa
Corporación Hacia un Valle Solidario
"""

import os
from datetime import datetime, date
from apps.tecnicos.google_sheets import GoogleSheetsService


class FacturacionService:
    """Servicio para generar registros de facturación diaria"""

    DIAS_SEMANA = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        self.libro = self.sheets_service.abrir_libro(self.sheet_id)

    def obtener_sedes(self):
        """Obtiene las sedes activas de la hoja Sedes"""
        hoja_sedes = self.sheets_service.obtener_hoja(self.libro, 'Sedes')
        datos = hoja_sedes.get_all_records()

        # Filtrar sedes válidas (excluir BODEGA y vacías)
        sedes_validas = [
            s for s in datos
            if s.get('NOMBRE_SEDE_EDUCATIVA')
            and s.get('NOMBRE_SEDE_EDUCATIVA') != 'BODEGA'
        ]
        return sedes_validas

    def obtener_supervisores(self):
        """Obtiene los supervisores por sede"""
        hoja_sup = self.sheets_service.obtener_hoja(self.libro, 'sedes_supevisor')
        datos = hoja_sup.get_all_records()

        # Crear diccionario por nombre de sede
        supervisores = {}
        for sup in datos:
            sede = sup.get('sedes educativas', '')
            if sede:
                supervisores[sede] = {
                    'nombre': sup.get('nombre', ''),
                    'correo': sup.get('user', '')
                }
        return supervisores

    def generar_registros_dia(self, fecha=None):
        """
        Genera los registros de facturación para un día específico

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
        sedes = self.obtener_sedes()
        supervisores = self.obtener_supervisores()

        # Generar registros
        registros = []
        for i, sede in enumerate(sedes, 1):
            # Generar ID único
            id_registro = f"FAC-{fecha.strftime('%Y%m%d')}-{i:04d}"

            # Datos de la sede
            centro = sede.get('NOMBRE_DEL_ESTABLECIMIENTO_EDUCATIVO', '')
            sede_nombre = sede.get('NOMBRE_SEDE_EDUCATIVA', '')

            # Buscar supervisor
            sup_info = supervisores.get(sede_nombre, {'nombre': '', 'correo': ''})

            # Raciones (0 si es sábado, normales si no)
            if es_sabado:
                comp_ampm = 0
                comp_pm = 0
                almuerzo = 0
                comp_ind = 0
            else:
                comp_ampm = sede.get('COMPLEMENTO AM/PM PREPARADO', 0) or 0
                comp_pm = sede.get('COMPLEMENTO PM PREPARADO', 0) or 0
                almuerzo = sede.get('ALMUERZO JORNADA UNICA', 0) or 0
                comp_ind = sede.get('COMPLEMENTO AM/PM INDUSTRIALIZADO', 0) or 0

            registro = [
                id_registro,
                centro,
                sede_nombre,
                fecha_str,
                dia_semana,
                sup_info['nombre'],
                sup_info['correo'],
                comp_ampm,
                comp_pm,
                almuerzo,
                comp_ind
            ]
            registros.append(registro)

        return registros, f"Generados {len(registros)} registros para {dia_semana} {fecha_str}"

    def verificar_registros_existentes(self, fecha):
        """Verifica si ya existen registros para una fecha"""
        hoja_fact = self.sheets_service.obtener_hoja(self.libro, 'facturacion')
        datos = hoja_fact.get_all_values()

        fecha_str = fecha.strftime('%Y-%m-%d')

        # Buscar si hay registros con esta fecha (columna 4 = FECHA)
        for fila in datos[1:]:  # Skip header
            if len(fila) > 3 and fila[3] == fecha_str:
                return True
        return False

    def insertar_registros(self, registros):
        """Inserta los registros en la hoja de facturación"""
        if not registros:
            return 0

        hoja_fact = self.sheets_service.obtener_hoja(self.libro, 'facturacion')

        # Obtener última fila con datos
        datos_actuales = hoja_fact.get_all_values()
        ultima_fila = len(datos_actuales) + 1

        # Insertar registros
        rango = f"A{ultima_fila}:K{ultima_fila + len(registros) - 1}"
        hoja_fact.update(values=registros, range_name=rango)

        return len(registros)

    def ejecutar_facturacion_diaria(self, fecha=None, forzar=False):
        """
        Ejecuta el proceso completo de facturación diaria

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


def ejecutar_facturacion_hoy():
    """Función helper para ejecutar facturación del día actual"""
    service = FacturacionService()
    resultado = service.ejecutar_facturacion_diaria()
    return resultado


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    resultado = ejecutar_facturacion_hoy()
    print(f"Resultado: {resultado}")
