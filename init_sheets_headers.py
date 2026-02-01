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
    
    # Definir libros a procesar
    LIBROS_CONFIG = {
        'CALI': os.environ.get('GOOGLE_SHEET_ID'),
        'YUMBO': os.environ.get('GOOGLE_SHEET_ID_YUMBO')
    }
    
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
    
    # Headers Definitions
    HEADERS_DEF = {
        'nomina_cali': {
            'cols': [
                'ID', 'SUPERVISOR', 'user', 'MODALIDAD', 'DESCRIPCION PROYECTO',
                'TIPO TIEMPO LABORADO', 'CEDULA', 'NOMBRE COLABORADOR', 'FECHA',
                'DIA', 'HORA INICIAL', 'HORA FINAL', 'TOTAL_HORAS', 'NOVEDAD',
                'FECHA FINAL', 'DIA FINAL', 'OBSERVACIONES'
            ],
            'range': 'A1:Q1',
            'create_cols': 20
        },
        'facturacion': {
            'cols': [
                'ID', 'CENTRO EDUCATIVO', 'SEDE_EDUCATIVA', 'FECHA', 'DIA', 
                'SUPERVISOR', 'CORREO', 'COMPLEMENTO_AM_PM_PREPARADO', 'COMPLEMENTO_PM_PREPARADO', 
                'ALMUERZO_JORNADA_UNICA', 'COMPLEMENTO_AM_PM_INDUSTRIALIZADO', 'NOVEDAD'
            ],
            'range': 'A1:L1',
            'create_cols': 15
        },
        'liquidacion_nomina': {
            'cols': [
                'ID', 'SUPERVISOR', 'SEDE', 'FECHA', 'DIA', 'CANT. MANIPULADORAS',
                'TOTAL HORAS', 'HUBO_RACIONES', 'COMPLEMENTO AM/PM',
                'COMPLEMENTO PM', 'ALMUERZO JU', 'INDUSTRIALIZADO',
                'TOTAL RACIONES', 'OBSERVACION', 'NOVEDAD'
            ],
            'range': 'A1:O1',
            'create_cols': 15
        },
        'novedades_cali': {
            'cols': [
                'ID', 'FECHA_REGISTRO', 'SUPERVISOR', 'SEDE', 'TIPO TIEMPO LABORADO',
                'CEDULA', 'NOMBRE_COLABORADOR', 'FECHA', 'DIA', 'HORA_INICIAL',
                'HORA_FINAL', 'TOTAL_HORAS', 'FECHA FINAL', 'DIA FINAL',
                'OBSERVACIONES', 'OBSERVACION', 'ESTADO', 'PROCESADO_POR'
            ],
            'range': 'A1:R1',
            'create_cols': 20
        }
    }

    # Iterar sobre cada libro configurado
    for nombre_sede, sheet_id in LIBROS_CONFIG.items():
        if not sheet_id:
            print(f"\n⚠️ Saltando {nombre_sede}: ID no configurado en .env")
            continue
            
        print(f"\n{'='*40}")
        print(f"PROCESANDO SEDE: {nombre_sede}")
        print(f"ID: {sheet_id}")
        print(f"{'='*40}")
        
        try:
            libro = client.open_by_key(sheet_id)
            print(f"✅ Libro abierto: {libro.title}")
            
            for nombre_hoja, config in HEADERS_DEF.items():
                print(f"   --- Verificando {nombre_hoja} ---")
                try:
                    hoja = libro.worksheet(nombre_hoja)
                    hoja.update(values=[config['cols']], range_name=config['range'])
                    print(f"   ✅ Headers actualizados")
                except gspread.WorksheetNotFound:
                    print(f"   🔨 Creando hoja {nombre_hoja}...")
                    hoja = libro.add_worksheet(title=nombre_hoja, rows=1000, cols=config['create_cols'])
                    hoja.update(values=[config['cols']], range_name=config['range'])
                    print(f"   ✅ Hoja creada con headers")
                except Exception as e:
                    print(f"   ❌ Error en hoja {nombre_hoja}: {e}")
                    
        except Exception as e:
            print(f"❌ Error crítico al procesar {nombre_sede}: {e}")

    print("\n🚀 Proceso completado exitosamente.")

if __name__ == '__main__':
    init_headers()
