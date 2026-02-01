"""
Constantes y configuraciones compartidas para la app tecnicos
"""
import os

SEDES = {
    'CALI': {
        'nombre': 'Cali',
        'env_var': 'GOOGLE_SHEET_ID',
        'default': True
    },
    'YUMBO': {
        'nombre': 'Yumbo',
        'env_var': 'GOOGLE_SHEET_ID_YUMBO',
        'default': False
    }
}

def obtener_id_hoja(sede_key=None):
    """
    Obtiene el ID de la hoja según la sede.
    Si sede_key es None, retorna el de Cali (default).
    """
    if not sede_key:
        sede_key = 'CALI'
    
    sede_key = sede_key.upper()
    config = SEDES.get(sede_key)
    
    # Si no existe la sede, fallback a Cali
    if not config:
        config = SEDES['CALI']
        
    return os.environ.get(config['env_var'])

def obtener_nombre_sede(sede_key=None):
    """Retorna el nombre legible de la sede"""
    if not sede_key:
        return SEDES['CALI']['nombre']
    
    sede_key = sede_key.upper()
    config = SEDES.get(sede_key, SEDES['CALI'])
    return config['nombre']
