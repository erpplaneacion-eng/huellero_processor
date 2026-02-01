"""
Comando de Django para ejecutar la liquidación de nómina diaria
Cruza nomina_cali con facturacion y envía reporte por email
Uso: python manage.py liquidacion_nomina_diaria [--fecha YYYY-MM-DD] [--forzar] [--sin-email]
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from apps.tecnicos.liquidacion_nomina_service import LiquidacionNominaService
from apps.tecnicos.email_service import EmailService


class Command(BaseCommand):
    help = 'Genera la liquidación de nómina cruzando nomina_cali con facturacion'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha para generar liquidación (YYYY-MM-DD). Default: hoy'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar creación aunque ya existan registros para la fecha'
        )
        parser.add_argument(
            '--sin-email',
            action='store_true',
            help='No enviar correo de notificación'
        )
        parser.add_argument(
            '--sede',
            type=str,
            help='Sede específica (CALI o YUMBO). Si se omite, ejecuta todas.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.NOTICE('LIQUIDACIÓN DE NÓMINA - Generación Diaria'))
        self.stdout.write(self.style.NOTICE('Cruce: nomina_cali + facturacion'))
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
        sin_email = options['sin_email']

        if forzar:
            self.stdout.write(self.style.WARNING('Modo forzado activado'))

        if sin_email:
            self.stdout.write(self.style.WARNING('Notificación por email desactivada'))
            
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
            registros_generados = []

            try:
                # Ejecutar servicio de liquidación
                service = LiquidacionNominaService(sede=sede_key)

                # Primero generar registros para tenerlos disponibles para el email
                if fecha is None:
                    from datetime import date
                    fecha = date.today()

                registros_generados, msg = service.generar_liquidacion_dia(fecha)

                # Ejecutar liquidación completa
                resultado = service.ejecutar_liquidacion_diaria(fecha=fecha, forzar=forzar)

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

                # Enviar correo si hay registros y no se desactivó
                if not sin_email and registros_generados:
                    self.stdout.write(self.style.NOTICE('Enviando notificación por email...'))

                    try:
                        email_service = EmailService()
                        resultado_email = email_service.enviar_reporte_liquidacion(
                            fecha=fecha,
                            registros=registros_generados,
                            resultado=resultado
                        )

                        if resultado_email['exito']:
                            self.stdout.write(
                                self.style.SUCCESS(f"✓ {resultado_email['mensaje']}")
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(f"✗ {resultado_email['mensaje']}")
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"✗ Error al enviar email: {str(e)}")
                        )

                elif not sin_email and not registros_generados:
                    self.stdout.write(
                        self.style.WARNING('⚠ No se envió email (sin registros para reportar)')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error: {str(e)}")
                )

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('='*60))
