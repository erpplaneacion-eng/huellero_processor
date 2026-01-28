"""
Comando para probar la conexión a Google Sheets
Uso: python manage.py test_sheets [--sheet-id ID]
"""

from django.core.management.base import BaseCommand
from apps.tecnicos.google_sheets import GoogleSheetsService
import os


class Command(BaseCommand):
    help = 'Prueba la conexión a Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sheet-id',
            type=str,
            help='ID del libro de Google Sheets (opcional si está en .env)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Probando conexión a Google Sheets...'))

        try:
            # Crear servicio
            service = GoogleSheetsService()
            self.stdout.write(self.style.SUCCESS('Conexión establecida correctamente'))

            # Obtener ID del libro
            sheet_id = options.get('sheet_id') or os.environ.get('GOOGLE_SHEET_ID')

            if not sheet_id:
                self.stdout.write(self.style.WARNING(
                    '\nNo se especificó GOOGLE_SHEET_ID.'
                    '\nConfigúralo en .env o usa: python manage.py test_sheets --sheet-id TU_ID'
                ))
                self.stdout.write(self.style.NOTICE(
                    '\nEl ID está en la URL del libro:'
                    '\nhttps://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit'
                ))
                return

            # Intentar abrir el libro
            self.stdout.write(f'\nAbriendo libro con ID: {sheet_id}')
            libro = service.abrir_libro(sheet_id)
            self.stdout.write(self.style.SUCCESS(f'Libro abierto: {libro.title}'))

            # Listar hojas
            hojas = libro.worksheets()
            self.stdout.write(f'\nHojas disponibles ({len(hojas)}):')
            for hoja in hojas:
                self.stdout.write(f'  - {hoja.title} ({hoja.row_count} filas x {hoja.col_count} columnas)')

            # Leer primeras filas de la primera hoja
            primera_hoja = hojas[0]
            self.stdout.write(f'\nPrimeras 3 filas de "{primera_hoja.title}":')
            datos = service.leer_datos(primera_hoja, 'A1:E3')
            for i, fila in enumerate(datos):
                self.stdout.write(f'  Fila {i+1}: {fila}')

            self.stdout.write(self.style.SUCCESS('\nConexión verificada exitosamente'))

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f'\nError: {e}'))
            self.stdout.write(self.style.NOTICE(
                'Asegúrate de que el archivo credentials/nomina.json existe'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError: {e}'))
            self.stdout.write(self.style.NOTICE(
                '\nPosibles causas:'
                '\n1. El Service Account no tiene acceso al libro'
                '\n2. El ID del libro es incorrecto'
                '\n3. Las credenciales son inválidas'
                '\n\nPara dar acceso, comparte el libro con el email del Service Account'
            ))
