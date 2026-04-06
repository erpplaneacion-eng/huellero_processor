"""
Management command: sincronizar_planta

Lee tabla_planta de la BD externa (RAILWAY_EXTERNAL_DB_URL) y sincroniza
los registros faltantes hacia maestro_empleado, cruzando por cédula/documento.
Se omiten filas sin cédula o con cédula vacía.

Uso:
  python manage.py sincronizar_planta
"""

import os
import psycopg2
from django.core.management.base import BaseCommand, CommandError

from apps.logistica.models import Empleado


class Command(BaseCommand):
    help = 'Sincroniza tabla_planta (BD externa) → maestro_empleado.'

    def handle(self, *args, **options):
        url_externa = os.environ.get('RAILWAY_EXTERNAL_DB_URL')
        if not url_externa:
            raise CommandError('Falta la variable de entorno RAILWAY_EXTERNAL_DB_URL.')

        # ── 1. Leer tabla_planta ──────────────────────────────────────────────
        try:
            conn = psycopg2.connect(url_externa)
            cur = conn.cursor()
            cur.execute("""
                SELECT cedula, nombre_completo, cargo
                FROM tabla_planta
                WHERE cedula IS NOT NULL AND cedula <> ''
            """)
            filas = cur.fetchall()
            conn.close()
        except Exception as e:
            raise CommandError(f'Error al conectar con BD externa: {e}')

        self.stdout.write(f'Registros en tabla_planta con cédula: {len(filas)}')

        # ── 2. Documentos ya existentes en maestro_empleado ──────────────────
        documentos_existentes = set(
            str(d) for d in Empleado.objects.exclude(documento__isnull=True)
                                            .values_list('documento', flat=True)
        )

        # ── 3. Insertar faltantes ─────────────────────────────────────────────
        creados = 0
        omitidos = 0
        errores = 0

        for cedula, nombre_completo, cargo in filas:
            cedula_str = str(cedula).strip()

            if cedula_str in documentos_existentes:
                omitidos += 1
                continue

            try:
                documento = int(float(cedula_str))
            except (ValueError, TypeError):
                self.stdout.write(
                    self.style.WARNING(f'   ⚠ Cédula inválida "{cedula_str}" para "{nombre_completo}", se omite.')
                )
                errores += 1
                continue

            nombre = str(nombre_completo or '').strip()
            if not nombre:
                errores += 1
                continue

            Empleado.objects.create(
                codigo=0,
                nombre=nombre,
                documento=documento,
                cargo=None,
                excluido=False,
            )
            documentos_existentes.add(cedula_str)
            creados += 1
            self.stdout.write(f'   + {documento} | {nombre}')

        self.stdout.write(self.style.SUCCESS(
            f'\nSincronización completada — Creados: {creados} | Ya existían: {omitidos} | Errores: {errores}'
        ))
