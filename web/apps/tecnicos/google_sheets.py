"""
Servicio de conexión a Google Sheets
Corporación Hacia un Valle Solidario
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from django.conf import settings


class GoogleSheetsService:
    """Servicio para conectar y operar con Google Sheets"""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.client = None
        self.credentials = None
        self._conectar()

    def _conectar(self):
        """Establece conexión con Google Sheets API"""
        try:
            # Ruta al archivo de credenciales
            credentials_file = os.environ.get(
                'GOOGLE_CREDENTIALS_FILE',
                'credentials/nomina.json'
            )

            # Construir ruta absoluta desde BASE_DIR
            credentials_path = Path(settings.BASE_DIR) / credentials_file

            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Archivo de credenciales no encontrado: {credentials_path}"
                )

            # Cargar credenciales
            self.credentials = Credentials.from_service_account_file(
                str(credentials_path),
                scopes=self.SCOPES
            )

            # Crear cliente de gspread
            self.client = gspread.authorize(self.credentials)

            print(f"Conexion a Google Sheets exitosa")

        except Exception as e:
            print(f"Error al conectar con Google Sheets: {e}")
            raise

    def abrir_libro(self, spreadsheet_id=None, nombre=None):
        """
        Abre un libro de Google Sheets

        Args:
            spreadsheet_id: ID del libro (de la URL)
            nombre: Nombre del libro (alternativo)

        Returns:
            Objeto Spreadsheet de gspread
        """
        try:
            if spreadsheet_id:
                return self.client.open_by_key(spreadsheet_id)
            elif nombre:
                return self.client.open(nombre)
            else:
                # Usar ID del .env
                sheet_id = os.environ.get('GOOGLE_SHEET_ID')
                if sheet_id:
                    return self.client.open_by_key(sheet_id)
                raise ValueError("Debe proporcionar spreadsheet_id o nombre")
        except gspread.SpreadsheetNotFound:
            raise Exception(
                "Libro no encontrado. Verifica que el Service Account "
                "tenga acceso al documento."
            )

    def obtener_hoja(self, libro, nombre_hoja=None, indice=0):
        """
        Obtiene una hoja específica del libro

        Args:
            libro: Objeto Spreadsheet
            nombre_hoja: Nombre de la hoja
            indice: Índice de la hoja (default: 0)

        Returns:
            Objeto Worksheet
        """
        if nombre_hoja:
            return libro.worksheet(nombre_hoja)
        return libro.get_worksheet(indice)

    def leer_datos(self, hoja, rango=None):
        """
        Lee datos de una hoja

        Args:
            hoja: Objeto Worksheet
            rango: Rango a leer (ej: 'A1:D10'), None para todos

        Returns:
            Lista de listas con los datos
        """
        if rango:
            return hoja.get(rango)
        return hoja.get_all_values()

    def leer_como_dict(self, hoja):
        """
        Lee datos como lista de diccionarios (primera fila como headers)

        Args:
            hoja: Objeto Worksheet

        Returns:
            Lista de diccionarios
        """
        return hoja.get_all_records()

    def escribir_celda(self, hoja, celda, valor):
        """
        Escribe un valor en una celda

        Args:
            hoja: Objeto Worksheet
            celda: Referencia de celda (ej: 'A1')
            valor: Valor a escribir
        """
        hoja.update_acell(celda, valor)

    def escribir_rango(self, hoja, rango, valores):
        """
        Escribe valores en un rango

        Args:
            hoja: Objeto Worksheet
            rango: Rango (ej: 'A1:C3')
            valores: Lista de listas con valores
        """
        hoja.update(rango, valores)

    def agregar_fila(self, hoja, valores):
        """
        Agrega una fila al final de la hoja

        Args:
            hoja: Objeto Worksheet
            valores: Lista con valores de la fila
        """
        hoja.append_row(valores)

    def buscar_celda(self, hoja, valor):
        """
        Busca una celda con un valor específico

        Args:
            hoja: Objeto Worksheet
            valor: Valor a buscar

        Returns:
            Objeto Cell o None
        """
        try:
            return hoja.find(valor)
        except gspread.CellNotFound:
            return None


def test_conexion():
    """Función para probar la conexión"""
    try:
        service = GoogleSheetsService()
        print("Conexion exitosa!")

        # Si hay GOOGLE_SHEET_ID configurado, intentar abrir el libro
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if sheet_id:
            libro = service.abrir_libro(sheet_id)
            print(f"Libro abierto: {libro.title}")

            # Listar hojas disponibles
            hojas = libro.worksheets()
            print(f"Hojas disponibles: {[h.title for h in hojas]}")
        else:
            print("GOOGLE_SHEET_ID no configurado en .env")
            print("Configura el ID del libro para probar la lectura")

        return True

    except Exception as e:
        print(f"Error en la conexion: {e}")
        return False


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()
    test_conexion()
