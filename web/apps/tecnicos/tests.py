"""
Tests para el módulo de tecnicos/supervisión
Valida el cálculo de métricas de liquidación de nómina
"""

from django.test import TestCase
from apps.tecnicos.views import _safe_float, _parsear_horas_formato, _parsear_hora


class ParsearHorasFormatoTest(TestCase):
    """Tests para la función _parsear_horas_formato"""

    def test_formato_hhmm_simple(self):
        """5:30 debe convertir a 5.5 horas"""
        self.assertEqual(_parsear_horas_formato("5:30"), 5.5)

    def test_formato_hhmm_hora_completa(self):
        """10:00 debe convertir a 10.0 horas"""
        self.assertEqual(_parsear_horas_formato("10:00"), 10.0)

    def test_formato_hhmm_quince_minutos(self):
        """8:15 debe convertir a 8.25 horas"""
        self.assertEqual(_parsear_horas_formato("8:15"), 8.25)

    def test_formato_hhmm_cuarenta_cinco_minutos(self):
        """6:45 debe convertir a 6.75 horas"""
        self.assertEqual(_parsear_horas_formato("6:45"), 6.75)

    def test_formato_vacio(self):
        """String vacío debe retornar 0.0"""
        self.assertEqual(_parsear_horas_formato(""), 0.0)

    def test_formato_none(self):
        """None debe retornar 0.0"""
        self.assertEqual(_parsear_horas_formato(None), 0.0)

    def test_formato_numero_directo(self):
        """Número directo '5' debe retornar 5.0"""
        self.assertEqual(_parsear_horas_formato("5"), 5.0)

    def test_formato_numero_decimal(self):
        """Número decimal '5.5' debe retornar 5.5"""
        self.assertEqual(_parsear_horas_formato("5.5"), 5.5)

    def test_formato_numero_coma(self):
        """Número con coma '5,5' debe retornar 5.5"""
        self.assertEqual(_parsear_horas_formato("5,5"), 5.5)

    def test_formato_con_espacios(self):
        """Debe manejar espacios: ' 5:30 ' -> 5.5"""
        self.assertEqual(_parsear_horas_formato(" 5:30 "), 5.5)

    def test_formato_cero(self):
        """'0:00' debe retornar 0.0"""
        self.assertEqual(_parsear_horas_formato("0:00"), 0.0)


class SafeFloatTest(TestCase):
    """Tests para la función _safe_float"""

    def test_numero_entero(self):
        """'100' debe retornar 100.0"""
        self.assertEqual(_safe_float("100"), 100.0)

    def test_numero_decimal_punto(self):
        """'100.5' debe retornar 100.5"""
        self.assertEqual(_safe_float("100.5"), 100.5)

    def test_numero_decimal_coma(self):
        """'100,5' debe retornar 100.5"""
        self.assertEqual(_safe_float("100,5"), 100.5)

    def test_string_vacio(self):
        """String vacío debe retornar 0.0"""
        self.assertEqual(_safe_float(""), 0.0)

    def test_none(self):
        """None debe retornar 0.0"""
        self.assertEqual(_safe_float(None), 0.0)

    def test_texto_invalido(self):
        """Texto no numérico debe retornar 0.0"""
        self.assertEqual(_safe_float("abc"), 0.0)

    def test_con_espacios(self):
        """' 100 ' debe retornar 100.0"""
        self.assertEqual(_safe_float(" 100 "), 100.0)


class CalculoMetricasLiquidacionTest(TestCase):
    """Tests para validar el cálculo de métricas de liquidación"""

    def calcular_metricas(self, rows):
        """
        Simula el cálculo de métricas como lo hace la vista liquidacion_nomina.
        rows: lista de filas con formato:
        [SUPERVISOR, SEDE, FECHA, DIA, CANT_MAN, TOTAL_HORAS, HUBO_RAC, TOTAL_RAC, OBS, NOV]
        """
        stats = {
            'dias_nomina': 0,
            'dias_raciones': 0,
            'inconsistencias': 0
        }
        rows_processed = []

        idx_tot_horas = 5
        idx_tot_rac = 7

        for r in rows:
            horas = _parsear_horas_formato(r[idx_tot_horas]) if len(r) > idx_tot_horas else 0.0
            raciones = _safe_float(r[idx_tot_rac]) if len(r) > idx_tot_rac else 0.0

            if horas > 0:
                stats['dias_nomina'] += 1

            if raciones > 0:
                stats['dias_raciones'] += 1

            tiene_alerta = False
            tipo_alerta = ""

            if raciones > 0 and horas == 0:
                tiene_alerta = True
                stats['inconsistencias'] += 1
                tipo_alerta = "Producción sin horas registradas"
            elif horas > 0 and raciones == 0:
                tiene_alerta = True
                stats['inconsistencias'] += 1
                tipo_alerta = "Horas registradas sin producción"

            rows_processed.append({
                'cells': r,
                'alert': tiene_alerta,
                'alert_msg': tipo_alerta
            })

        return stats, rows_processed

    def test_registro_completo_sin_inconsistencia(self):
        """Registro con horas Y raciones no debe ser inconsistencia"""
        rows = [
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 3, '5:30', 'SI', 150, '', '']
        ]
        stats, processed = self.calcular_metricas(rows)

        self.assertEqual(stats['dias_nomina'], 1)
        self.assertEqual(stats['dias_raciones'], 1)
        self.assertEqual(stats['inconsistencias'], 0)
        self.assertFalse(processed[0]['alert'])

    def test_registro_solo_horas_sin_raciones(self):
        """Registro con horas pero sin raciones = inconsistencia"""
        rows = [
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 3, '5:30', 'NO', 0, 'ASEO', '']
        ]
        stats, processed = self.calcular_metricas(rows)

        self.assertEqual(stats['dias_nomina'], 1)
        self.assertEqual(stats['dias_raciones'], 0)
        self.assertEqual(stats['inconsistencias'], 1)
        self.assertTrue(processed[0]['alert'])
        self.assertEqual(processed[0]['alert_msg'], "Horas registradas sin producción")

    def test_registro_solo_raciones_sin_horas(self):
        """Registro con raciones pero sin horas = inconsistencia"""
        rows = [
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 3, '', 'SI', 150, '', '']
        ]
        stats, processed = self.calcular_metricas(rows)

        self.assertEqual(stats['dias_nomina'], 0)
        self.assertEqual(stats['dias_raciones'], 1)
        self.assertEqual(stats['inconsistencias'], 1)
        self.assertTrue(processed[0]['alert'])
        self.assertEqual(processed[0]['alert_msg'], "Producción sin horas registradas")

    def test_registro_sin_horas_ni_raciones(self):
        """Registro sin horas ni raciones no es inconsistencia (ambos 0)"""
        rows = [
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 0, '', 'NO', 0, '', '']
        ]
        stats, processed = self.calcular_metricas(rows)

        self.assertEqual(stats['dias_nomina'], 0)
        self.assertEqual(stats['dias_raciones'], 0)
        self.assertEqual(stats['inconsistencias'], 0)
        self.assertFalse(processed[0]['alert'])

    def test_multiples_registros_mixtos(self):
        """Test con múltiples registros de diferentes tipos"""
        rows = [
            # Completo (horas + raciones)
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 3, '5:30', 'SI', 150, '', ''],
            # Solo horas (inconsistencia)
            ['SUP1', 'SEDE2', '2025-01-27', 'Lunes', 2, '4:00', 'NO', 0, 'ASEO', ''],
            # Solo raciones (inconsistencia)
            ['SUP2', 'SEDE3', '2025-01-27', 'Lunes', 1, '0:00', 'SI', 80, '', ''],
            # Completo
            ['SUP2', 'SEDE4', '2025-01-27', 'Lunes', 4, '8:15', 'SI', 200, '', ''],
            # Sin nada
            ['SUP3', 'SEDE5', '2025-01-27', 'Lunes', 0, '', 'NO', 0, '', ''],
        ]
        stats, processed = self.calcular_metricas(rows)

        # Días nómina: registros 0, 1, 3 tienen horas > 0
        self.assertEqual(stats['dias_nomina'], 3)
        # Días raciones: registros 0, 2, 3 tienen raciones > 0
        self.assertEqual(stats['dias_raciones'], 3)
        # Inconsistencias: registros 1 y 2
        self.assertEqual(stats['inconsistencias'], 2)

    def test_horas_formato_variados(self):
        """Test con diferentes formatos de horas"""
        rows = [
            ['SUP1', 'SEDE1', '2025-01-27', 'Lunes', 1, '10:30', 'SI', 100, '', ''],  # 10.5h
            ['SUP1', 'SEDE2', '2025-01-27', 'Lunes', 1, '5:00', 'SI', 50, '', ''],    # 5h
            ['SUP1', 'SEDE3', '2025-01-27', 'Lunes', 1, '0:45', 'SI', 10, '', ''],    # 0.75h
        ]
        stats, _ = self.calcular_metricas(rows)

        self.assertEqual(stats['dias_nomina'], 3)
        self.assertEqual(stats['dias_raciones'], 3)
        self.assertEqual(stats['inconsistencias'], 0)


class ParsearHoraTest(TestCase):
    """Tests para la función _parsear_hora (usada en nomina_cali)"""

    def test_formato_24h(self):
        """Formato HH:MM debe parsearse correctamente"""
        result = _parsear_hora("14:30")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_formato_24h_con_segundos(self):
        """Formato HH:MM:SS debe parsearse correctamente"""
        result = _parsear_hora("14:30:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_vacio(self):
        """String vacío debe retornar None"""
        self.assertIsNone(_parsear_hora(""))

    def test_con_espacios(self):
        """Debe manejar espacios"""
        result = _parsear_hora(" 09:15 ")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
