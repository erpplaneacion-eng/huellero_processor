
import os
import django
from datetime import date

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'huellero_web.settings')
django.setup()

from apps.tecnicos.nomina_cali_service import NominaCaliService

def diagnosticar_novedades():
    service = NominaCaliService()
    print("--- DIAGNÓSTICO DE NOVEDADES ---")
    
    try:
        hoja = service.sheets_service.obtener_hoja(service.libro, 'novedades_cali')
        registros = hoja.get_all_records()
        print(f"Total registros encontrados en 'novedades_cali': {len(registros)}")
        
        if not registros:
            print("La hoja está vacía o no se pudieron leer registros.")
            return

        print("\n--- MUESTRA DE DATOS CRUDOS (Primeros 3) ---")
        for i, reg in enumerate(registros[:3]):
            print(f"Registro {i+1}:")
            print(f"  CEDULA: '{reg.get('CEDULA')}' (Tipo: {type(reg.get('CEDULA'))})")
            print(f"  FECHA: '{reg.get('FECHA')}' (Tipo: {type(reg.get('FECHA'))})")
            print(f"  FECHA FINAL: '{reg.get('FECHA FINAL')}' (Tipo: {type(reg.get('FECHA FINAL'))})")
            print("-" * 20)

        print("\n--- PRUEBA DE PARSING PARA FECHA OBJETIVO: 2026-01-28 ---")
        fecha_objetivo = date(2026, 1, 28)
        novedades_activas = service.obtener_novedades_activas(fecha_objetivo)
        
        print(f"\nNovedades detectadas para {fecha_objetivo}: {len(novedades_activas)}")
        for cedula, datos in novedades_activas.items():
            print(f"  -> Cédula {cedula}: {datos}")
            
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n--- DIAGNÓSTICO DE CÉDULAS EN 'Manipuladoras' ---")
    try:
        # Obtener manipuladoras para comparar formato de cédula
        manipuladoras = service.obtener_manipuladoras_activas()
        print(f"Total manipuladoras activas leídas: {len(manipuladoras)}")
        
        # Buscar la cédula problemática (38.640.942 o similar)
        ejemplo_cedula = '38640942' # Sin puntos para búsqueda laxa
        
        encontrado = False
        for m in manipuladoras:
            ced_origen = str(m.get('No. Documento', ''))
            nombre = m.get('Nombre', '')
            
            # Limpiar puntos para comparar
            ced_limpia = ced_origen.replace('.', '').strip()
            
            if ced_limpia == ejemplo_cedula:
                print(f"¡ENCONTRADA! -> Nombre: {nombre}")
                print(f"  Cédula en 'Manipuladoras' (RAW): '{ced_origen}'")
                print(f"  Cédula limpia: '{ced_limpia}'")
                encontrado = True
                break
        
        if not encontrado:
            print(f"No se encontró ninguna manipuladora con cédula similar a {ejemplo_cedula}")
            # Mostrar las primeras 3 para ver formato general
            print("Muestra de 3 manipuladoras:")
            for m in manipuladoras[:3]:
                 print(f"  - {m.get('Nombre')}: '{m.get('No. Documento')}'")

    except Exception as e:
        print(f"ERROR leyendo manipuladoras: {e}")

if __name__ == '__main__':
    diagnosticar_novedades()
