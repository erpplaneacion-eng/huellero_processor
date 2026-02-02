
import pandas as pd
from datetime import datetime
import config
from src.calculator import Calculator

# Mock data
turno_mock = {
    'codigo': 123,
    'nombre': 'TEST USER',
    'fecha': datetime(2026, 1, 13).date(),
    'entrada': datetime(2026, 1, 13, 16, 39),
    'salida': datetime(2026, 1, 14, 4, 44),
    'horas': 12.08,
    'es_nocturno': True,
    'completo': True,
    'entrada_inferida': False,
    'salida_inferida': False,
    'salida_corregida': False,
    'nocturno_prospectivo': False
}

df_turnos = pd.DataFrame([turno_mock])

# Mock marcaciones (needed for Calculator)
df_marcaciones = pd.DataFrame([
    {'CODIGO': 123, 'FECHA_HORA': datetime(2026, 1, 13, 16, 39), 'ESTADO': 'Entrada'},
    {'CODIGO': 123, 'FECHA_HORA': datetime(2026, 1, 14, 4, 44), 'ESTADO': 'Salida'}
])

calc = Calculator()
resultado = calc.calcular_metricas(df_turnos, df_marcaciones)

print("RESULTADO:")
print(resultado[['FECHA', 'HORA DE INGRESO', 'HORA DE SALIDA', 'TOTAL HORAS LABORADAS']])
