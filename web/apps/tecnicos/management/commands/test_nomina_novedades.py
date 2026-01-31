
from django.test import TestCase
from unittest.mock import MagicMock, patch
from datetime import date, datetime
from apps.tecnicos.nomina_cali_service import NominaCaliService

class NominaNovedadesTest(TestCase):

    def setUp(self):
        # Mock de dependencias externas
        self.patcher_sheets = patch('apps.tecnicos.nomina_cali_service.GoogleSheetsService')
        self.MockSheetsService = self.patcher_sheets.start()
        
        # Instancia del servicio con mock
        self.service = NominaCaliService()
        
        # Datos base de prueba
        self.manipuladora = {
            'Nombre': 'Juan Perez',
            'No. Documento': '123',
            'sede educativa': 'SEDE PRUEBA',
            'SUPERVISOR': 'SUPERVISOR 1',
            'Estado': 'Activo'
        }
        
        self.supervisor = {
            'nombre': 'SUPERVISOR 1',
            'user': 'sup@test.com'
        }
        
        self.horario = {
            'SEDE PRUEBA': [{
                'turno': 'A',
                'hora_entrada': '07:00',
                'hora_salida': '15:00'
            }]
        }

        # Mockear métodos internos de obtención de datos base
        self.service.obtener_manipuladoras_activas = MagicMock(return_value=[self.manipuladora])
        self.service.obtener_supervisores = MagicMock(return_value={'SUPERVISOR 1': self.supervisor})
        self.service.obtener_horarios = MagicMock(return_value=self.horario)

    def tearDown(self):
        self.patcher_sheets.stop()

    def test_dia_normal_sin_novedad(self):
        """
        Caso: Día normal fuera de cualquier rango de novedad.
        Debe generar horas calculadas y P. ALIMENTOS.
        """
        # Mockear que NO hay novedades en la hoja
        hoja_novedades_mock = MagicMock()
        hoja_novedades_mock.get_all_records.return_value = []
        
        self.service.sheets_service.obtener_hoja.return_value = hoja_novedades_mock
        self.service.libro = MagicMock() # Mock del libro

        fecha_prueba = date(2026, 1, 28) # Antes de la incapacidad
        
        registros, msg = self.service.generar_registros_dia(fecha=fecha_prueba)
        
        self.assertEqual(len(registros), 1)
        reg = registros[0]
        
        # Verificar columnas clave
        # Index 5: TIPO TIEMPO LABORADO
        self.assertEqual(reg[5], 'P. ALIMENTOS') 
        # Index 12: TOTAL_HORAS (7am a 3pm = 8 horas)
        self.assertEqual(reg[12], '8.00')
        # Index 13: NOVEDAD (vacío)
        self.assertEqual(reg[13], '')

    def test_dia_con_novedad_activa_iso_date(self):
        """
        Caso: Día DENTRO del rango de novedad.
        Novedad guardada con formato YYYY-MM-DD.
        Debe generar 0 horas, Tipo de Novedad y Novedad=SI.
        """
        # Datos de la hoja novedades_cali
        novedades_data = [{
            'CEDULA': '123',
            'FECHA': '2026-01-29',
            'FECHA FINAL': '2026-02-02',
            'TIPO TIEMPO LABORADO': 'INCAPACIDAD',
            'DIA FINAL': 'Lunes',
            'OBSERVACIONES': 'Reposo medico'
        }]

        # Mockear la hoja de novedades
        hoja_novedades_mock = MagicMock()
        hoja_novedades_mock.get_all_records.return_value = novedades_data
        self.service.sheets_service.obtener_hoja.return_value = hoja_novedades_mock

        # Fecha de prueba: 30 de Enero (Dentro del rango 29 Ene - 02 Feb)
        fecha_prueba = date(2026, 1, 30)
        
        registros, msg = self.service.generar_registros_dia(fecha=fecha_prueba)
        
        self.assertEqual(len(registros), 1)
        reg = registros[0]
        
        # Verificar lógica de negocio aplicada
        # Index 5: TIPO TIEMPO LABORADO debe ser el de la novedad
        self.assertEqual(reg[5], 'INCAPACIDAD')
        # Index 12: TOTAL_HORAS debe ser 0
        self.assertEqual(reg[12], '0')
        # Index 13: NOVEDAD debe ser SI
        self.assertEqual(reg[13], 'SI')
        # Index 14: FECHA FINAL debe ser la de la novedad
        self.assertEqual(reg[14], '2026-02-02')

    def test_dia_con_novedad_activa_latam_date(self):
        """
        Caso: Día DENTRO del rango de novedad.
        Novedad guardada con formato DD/MM/YYYY.
        Debe parsear correctamente y aplicar la lógica.
        """
        # Datos con formato de fecha DD/MM/YYYY
        novedades_data = [{
            'CEDULA': '123',
            'FECHA': '29/01/2026',
            'FECHA FINAL': '02/02/2026',
            'TIPO TIEMPO LABORADO': 'PERMISO NO REMUNERADO',
            'DIA FINAL': 'Lunes',
            'OBSERVACIONES': 'Personal'
        }]

        hoja_novedades_mock = MagicMock()
        hoja_novedades_mock.get_all_records.return_value = novedades_data
        self.service.sheets_service.obtener_hoja.return_value = hoja_novedades_mock

        # Fecha de prueba: 30 de Enero
        fecha_prueba = date(2026, 1, 30)
        
        registros, msg = self.service.generar_registros_dia(fecha=fecha_prueba)
        
        reg = registros[0]
        self.assertEqual(reg[5], 'PERMISO NO REMUNERADO')
        self.assertEqual(reg[12], '0')
        self.assertEqual(reg[14], '02/02/2026')

    def test_dia_despues_de_novedad(self):
        """
        Caso: Día POSTERIOR al rango de la novedad.
        Debe volver a la normalidad (P. ALIMENTOS y cálculo de horas).
        """
        novedades_data = [{
            'CEDULA': '123',
            'FECHA': '2026-01-29',
            'FECHA FINAL': '2026-02-02', # Termina el 2 de Feb
            'TIPO TIEMPO LABORADO': 'INCAPACIDAD'
        }]

        hoja_novedades_mock = MagicMock()
        hoja_novedades_mock.get_all_records.return_value = novedades_data
        self.service.sheets_service.obtener_hoja.return_value = hoja_novedades_mock

        # Fecha de prueba: 3 de Febrero (Ya venció la incapacidad)
        fecha_prueba = date(2026, 2, 3)
        
        registros, msg = self.service.generar_registros_dia(fecha=fecha_prueba)
        
        reg = registros[0]
        # Debe haber vuelto a P. ALIMENTOS
        self.assertEqual(reg[5], 'P. ALIMENTOS')
        # Debe tener horas calculadas
        self.assertEqual(reg[12], '8.00')
        # NOVEDAD vacía
        self.assertEqual(reg[13], '')
