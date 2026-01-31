
import os
import django

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'huellero_web.settings')
django.setup()

from apps.tecnicos.nomina_cali_service import NominaCaliService

def revisar_columnas_manipuladoras():
    service = NominaCaliService()
    try:
        hoja = service.sheets_service.obtener_hoja(service.libro, 'Manipuladoras')
        # Leer solo la primera fila (headers)
        headers = hoja.row_values(1)
        print("--- COLUMNAS ENCONTRADAS EN 'Manipuladoras' ---")
        for i, header in enumerate(headers):
            print(f"{i+1}. {header}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    revisar_columnas_manipuladoras()
