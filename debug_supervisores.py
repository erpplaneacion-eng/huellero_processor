
import os
import sys
from dotenv import load_dotenv
import django
from django.conf import settings

# Agregar root al path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web'))

# Configurar Django mínimamente
if not settings.configured:
    load_dotenv('web/.env')
    settings.configure(
        BASE_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web'),
        INSTALLED_APPS=[],
    )
    django.setup()

from apps.tecnicos.google_sheets import GoogleSheetsService
from apps.tecnicos.constantes import obtener_id_hoja

def diagnosticar_supervisores():
    sede = 'YUMBO'
    print(f"--- Diagnóstico Supervisores {sede} ---")
    
    try:
        service = GoogleSheetsService()
        sheet_id = obtener_id_hoja(sede)
        libro = service.abrir_libro(sheet_id)
        print(f"Libro abierto: {libro.title}")
        
        # 1. Revisar hoja sedes_supevisor
        try:
            hoja_sup = service.obtener_hoja(libro, 'sedes_supevisor')
            datos_sup = hoja_sup.get_all_records()
            print(f"\n[sedes_supevisor] Registros encontrados: {len(datos_sup)}")
            if datos_sup:
                print(f"Columnas detectadas: {list(datos_sup[0].keys())}")
                # print("Ejemplo de primer registro:")
                # print(datos_sup[0])
            else:
                print("⚠️ La hoja sedes_supevisor está vacía.")
                
        except Exception as e:
            print(f"❌ Error leyendo sedes_supevisor: {e}")
            return

        # 2. Revisar hoja Manipuladoras para ver qué supervisores se usan
        try:
            hoja_manip = service.obtener_hoja(libro, 'Manipuladoras')
            datos_manip = hoja_manip.get_all_records()
            
            supervisores_en_manip = set()
            for m in datos_manip:
                if m.get('Estado', '').lower() == 'activo':
                    sup = m.get('SUPERVISOR', '').strip()
                    if sup:
                        supervisores_en_manip.add(sup)
            
            print(f"\n[Manipuladoras] Supervisores únicos encontrados en personal activo: {len(supervisores_en_manip)}")
            for s in supervisores_en_manip:
                print(f" - '{s}'")
                
            # 3. Cruzar información
            print("\n--- Cruce de Información ---")
            # Normalizar claves del dict de configuración
            supervisores_configurados = {}
            for d in datos_sup:
                nombre = str(d.get('nombre', '')).strip().upper()
                # Intentar obtener 'user' o 'correo' o 'email'
                user = str(d.get('user', '')).strip()
                if not user:
                     user = str(d.get('correo', '')).strip()
                
                if nombre:
                    supervisores_configurados[nombre] = user

            for s_manip in supervisores_en_manip:
                s_upper = s_manip.upper()
                if s_upper in supervisores_configurados:
                    user = supervisores_configurados[s_upper]
                    if user:
                        print(f"✅ '{s_manip}': Configurado con user '{user}'")
                    else:
                        print(f"⚠️ '{s_manip}': Encontrado pero columna 'user' VACÍA")
                else:
                    print(f"❌ '{s_manip}': NO encontrado en hoja sedes_supevisor")

        except Exception as e:
            print(f"❌ Error leyendo Manipuladoras: {e}")

    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    diagnosticar_supervisores()

