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
        parser.add_argument(
            '--sede',
            type=str,
            help='Sede específica (CALI o YUMBO). Si se omite, ejecuta todas.',
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
        sede_arg = options.get('sede')
        
        from apps.tecnicos.constantes import SEDES
        
        sedes_a_procesar = []
        if sede_arg:
            if sede_arg.upper() in SEDES:
                sedes_a_procesar.append(sede_arg.upper())
            else:
                 self.stdout.write(self.style.ERROR(f"Sede no válida: {sede_arg}. Opciones: {list(SEDES.keys())}"))
                 return
        else:
            sedes_a_procesar = list(SEDES.keys())

        for sede_key in sedes_a_procesar:
            self.stdout.write(f"\n--- Procesando {sede_key} ---")
            try:
                # Ejecutar facturación
                service = FacturacionService(sede=sede_key)
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
