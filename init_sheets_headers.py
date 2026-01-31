import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def init_headers():
    # Cargar variables de entorno
    env_path = os.path.join(BASE_DIR, 'web', '.env')
    load_dotenv(env_path)
    
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    credentials_file = os.environ.get('GOOGLE_CREDENTIALS_FILE', 'web/credentials/nomina.json')
    credentials_path = os.path.join(BASE_DIR, 'web', credentials_file)
    
    if not os.path.exists(credentials_path):
        print(f"❌ Error: No se encontró el archivo de credenciales en {credentials_path}")
        return

    # Autenticación
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)
    
    try:
        libro = client.open_by_key(sheet_id)
        print(f"✅ Libro abierto: {libro.title}")
    except Exception as e:
        print(f"❌ Error al abrir el libro: {e}")
        return

    # 1. Nomina Cali
    print("\n--- Procesando nomina_cali ---")
    nomina_headers = [
        'ID', 'SUPERVISOR', 'user', 'MODALIDAD', 'DESCRIPCION PROYECTO',
        'TIPO TIEMPO LABORADO', 'CEDULA', 'NOMBRE COLABORADOR', 'FECHA',
        'DIA', 'HORA INICIAL', 'HORA FINAL', 'TOTAL_HORAS', 'NOVEDAD',
        'FECHA FINAL', 'DIA FINAL', 'OBSERVACIONES'
    ]
    try:
        hoja_nomina = libro.worksheet('nomina_cali')
        hoja_nomina.update(values=[nomina_headers], range_name='A1:Q1')
        print("✅ Headers de nomina_cali actualizados (17 columnas)")
    except gspread.WorksheetNotFound:
        print("Creando hoja nomina_cali...")
        hoja_nomina = libro.add_worksheet(title='nomina_cali', rows=1000, cols=20)
        hoja_nomina.update(values=[nomina_headers], range_name='A1:Q1')
        print("✅ Hoja nomina_cali creada con headers")
    except Exception as e:
        print(f"⚠️ Error en nomina_cali: {e}")

    # 2. Facturacion
    print("\n--- Procesando facturacion ---")
    fact_headers = [
        'ID', 'CENTRO EDUCATIVO', 'SEDE', 'FECHA', 'DIA', 
        'SUPERVISOR', 'CORREO', 'COMP_AM_PM', 'COMP_PM', 
        'ALMUERZO', 'COMP_IND', 'NOVEDAD'
    ]
    try:
        hoja_fact = libro.worksheet('facturacion')
        hoja_fact.update(values=[fact_headers], range_name='A1:L1')
        print("✅ Headers de facturacion actualizados (12 columnas)")
    except gspread.WorksheetNotFound:
        print("Creando hoja facturacion...")
        hoja_fact = libro.add_worksheet(title='facturacion', rows=1000, cols=15)
        hoja_fact.update(values=[fact_headers], range_name='A1:L1')
        print("✅ Hoja facturacion creada con headers")
    except Exception as e:
        print(f"⚠️ Error en facturacion: {e}")

    # 3. Liquidacion Nomina (Asegurar que existan headers)
    print("\n--- Procesando liquidacion_nomina ---")
    liq_headers = [
        'ID', 'SUPERVISOR', 'SEDE', 'FECHA', 'DIA', 'CANT. MANIPULADORAS',
        'TOTAL HORAS', 'HUBO_RACIONES', 'COMPLEMENTO AM/PM',
        'COMPLEMENTO PM', 'ALMUERZO JU', 'INDUSTRIALIZADO',
        'TOTAL RACIONES', 'OBSERVACION', 'NOVEDAD'
    ]
    try:
        hoja_liq = libro.worksheet('liquidacion_nomina')
        hoja_liq.update(values=[liq_headers], range_name='A1:O1')
        print("✅ Headers de liquidacion_nomina actualizados (15 columnas)")
    except gspread.WorksheetNotFound:
        print("Creando hoja liquidacion_nomina...")
        hoja_liq = libro.add_worksheet(title='liquidacion_nomina', rows=1000, cols=15)
        hoja_liq.update(values=[liq_headers], range_name='A1:O1')
        print("✅ Hoja liquidacion_nomina creada con headers")
    except Exception as e:
        print(f"⚠️ Error en liquidacion_nomina: {e}")

    # 4. Novedades Cali
    print("\n--- Procesando novedades_cali ---")
    novedades_headers = [
        'ID', 'FECHA_REGISTRO', 'SUPERVISOR', 'SEDE', 'TIPO TIEMPO LABORADO',
        'CEDULA', 'NOMBRE_COLABORADOR', 'FECHA', 'DIA', 'HORA_INICIAL',
        'HORA_FINAL', 'TOTAL_HORAS', 'FECHA FINAL', 'DIA FINAL',
        'OBSERVACIONES', 'OBSERVACION', 'ESTADO', 'PROCESADO_POR'
    ]
    try:
        hoja_novedades = libro.worksheet('novedades_cali')
        hoja_novedades.update(values=[novedades_headers], range_name='A1:R1')
        print("✅ Headers de novedades_cali actualizados (18 columnas)")
    except gspread.WorksheetNotFound:
        print("Creando hoja novedades_cali...")
        hoja_novedades = libro.add_worksheet(title='novedades_cali', rows=1000, cols=20)
        hoja_novedades.update(values=[novedades_headers], range_name='A1:R1')
        print("✅ Hoja novedades_cali creada con headers")
    except Exception as e:
        print(f"⚠️ Error en novedades_cali: {e}")

    print("\n🚀 Proceso completado exitosamente.")

if __name__ == '__main__':
    init_headers()
