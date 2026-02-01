"""
Comando de Django para ejecutar la generación de nómina diaria de Cali
Uso: python manage.py nomina_cali_diaria [--fecha YYYY-MM-DD] [--forzar]
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from apps.tecnicos.nomina_cali_service import NominaCaliService


class Command(BaseCommand):
    help = 'Genera los registros de nómina diaria para manipuladoras (Cali/Yumbo)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha para generar registros (YYYY-MM-DD). Default: hoy'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar creación aunque ya existan registros para la fecha'
        )
        parser.add_argument(
            '--sede',
            type=str,
            help='Sede específica (CALI o YUMBO). Si se omite, ejecuta todas.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.NOTICE('NÓMINA - Generación Diaria'))
        self.stdout.write(self.style.NOTICE('Corporación Hacia un Valle Solidario'))
        self.stdout.write(self.style.NOTICE('='*60))

        # Parsear fecha si se proporcionó
        fecha = None
        if options['fecha']:
            try:
                fecha = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
                self.stdout.write(f"Fecha especificada: {fecha}")
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Formato de fecha inválido. Use YYYY-MM-DD')
                )
                return

        forzar = options['forzar']
        if forzar:
            self.stdout.write(self.style.WARNING('Modo forzado activado'))
            
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
                # Ejecutar servicio
                service = NominaCaliService(sede=sede_key)
                resultado = service.ejecutar_nomina_diaria(fecha=fecha, forzar=forzar)

                # Mostrar resultado
                self.stdout.write(f"Fecha: {resultado['fecha']} ({resultado['dia']})")

                if resultado['exito']:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {resultado['mensaje']}")
                    )
                    if resultado['registros_creados'] > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Registros insertados: {resultado['registros_creados']}"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"⚠ {resultado['mensaje']}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error: {str(e)}")
                )

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('='*60))
