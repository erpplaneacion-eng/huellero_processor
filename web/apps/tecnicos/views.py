from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .google_sheets import GoogleSheetsService
import logging

logger = logging.getLogger(__name__)


@login_required
def index(request):
    """
    Vista principal del área de supervisión/técnicos.
    Muestra el dashboard con accesos a las diferentes funcionalidades.
    """
    context = {
        'titulo': 'Panel de Supervisión',
        'usuario': request.user,
    }
    return render(request, 'tecnicos/index.html', context)

@login_required
def liquidacion_nomina(request):
    """
    Vista para visualizar la hoja de 'Liquidacion Nomina' desde Google Sheets.
    """
    data = []
    headers = []
    error_message = None

    try:
        # Instanciar servicio
        service = GoogleSheetsService()
        
        # Abrir libro (usa ID del .env por defecto)
        libro = service.abrir_libro()
        
        # Intentar obtener la hoja.
        # Se busca estrictamente con el nombre "liquidacion_nomina" como solicitado.
        nombre_hoja = "liquidacion_nomina"
        hoja = service.obtener_hoja(libro, nombre_hoja=nombre_hoja)
                
        if not hoja:
            # Si no encuentra por nombre, intenta la primera hoja como fallback
            hoja = service.obtener_hoja(libro, indice=0)
            error_message = f"No se encontró la hoja exacta '{nombre_hoja}'. Mostrando la primera hoja disponible: '{hoja.title}'"

        if hoja:
            # Obtener todos los valores
            raw_data = service.leer_datos(hoja)
            
            if raw_data:
                headers = raw_data[0]  # La primera fila son los encabezados
                data = raw_data[1:]    # El resto son los datos
            else:
                error_message = "La hoja está vacía."

    except Exception as e:
        logger.error(f"Error accediendo a Google Sheets: {e}")
        error_message = f"Error al cargar los datos: {str(e)}"

    context = {
        'headers': headers,
        'rows': data,
        'error_message': error_message,
        'titulo': 'Liquidación Nómina'
    }

    return render(request, 'tecnicos/liquidacion_nomina.html', context)