"""
Comando para ejecutar la facturación diaria
Uso: python manage.py facturacion_diaria [--fecha YYYY-MM-DD] [--forzar]

Programar con cron para las 8am:
0 8 * * * cd /path/to/web && python manage.py facturacion_diaria
"""

from django.core.management.base import BaseCommand
from apps.tecnicos.facturacion_service import FacturacionService
from datetime import datetime


class Command(BaseCommand):
    help = 'Genera los registros de facturación diaria para las sedes educativas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica (YYYY-MM-DD). Por defecto usa la fecha actual.',
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar creación aunque ya existan registros para esa fecha',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.NOTICE('FACTURACIÓN DIARIA - CHVS'))
        self.stdout.write(self.style.NOTICE('='*60))

        # Parsear fecha si se proporcionó
        fecha = None
        if options.get('fecha'):
            try:
                fecha = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(
                    f"Formato de fecha inválido: {options['fecha']}. Use YYYY-MM-DD"
                ))
                return

        forzar = options.get('forzar', False)

        try:
            # Ejecutar facturación
            service = FacturacionService()
            resultado = service.ejecutar_facturacion_diaria(fecha=fecha, forzar=forzar)

            # Mostrar resultado
            self.stdout.write(f"Fecha: {resultado['fecha']}")
            self.stdout.write(f"Día: {resultado['dia']}")

            if resultado['exito']:
                self.stdout.write(self.style.SUCCESS(f"✓ {resultado['mensaje']}"))
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Registros creados: {resultado['registros_creados']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ {resultado['mensaje']}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))

        self.stdout.write(self.style.NOTICE('='*60))
