"""
Management command: sincronizar_planta

Lee tabla_planta de la BD externa (TABLA_PLANTA_DB_URL) y sincroniza
nombre_completo y cargo hacia maestro_empleado, cruzando por cédula/documento.
- Empleados nuevos: se crean.
- Empleados existentes: se actualiza nombre y cargo si vienen de la BD externa.
Se omiten filas sin cédula o con cédula vacía.

Uso:
  python manage.py sincronizar_planta
"""

import os
import psycopg2
from django.core.management.base import BaseCommand, CommandError

from apps.logistica.models import Empleado


class Command(BaseCommand):
    help = 'Sincroniza tabla_planta (BD externa) → maestro_empleado (upsert por cédula).'

    def handle(self, *args, **options):
        url_externa = os.environ.get('TABLA_PLANTA_DB_URL') or os.environ.get('RAILWAY_EXTERNAL_DB_URL')
        if not url_externa:
            raise CommandError('Falta la variable de entorno TABLA_PLANTA_DB_URL.')

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

        # ── 2. Cargar mapa documento → Empleado desde la BD local ─────────────
        empleados_por_doc = {
            str(emp.documento): emp
            for emp in Empleado.objects.exclude(documento__isnull=True)
        }

        # ── 3. Upsert ─────────────────────────────────────────────────────────
        creados = 0
        actualizados = 0
        omitidos = 0
        errores = 0

        for cedula, nombre_completo, cargo_externo in filas:
            cedula_str = str(cedula).strip()
            nombre = str(nombre_completo or '').strip()

            if not nombre:
                errores += 1
                continue

            try:
                documento = int(float(cedula_str))
            except (ValueError, TypeError):
                self.stdout.write(
                    self.style.WARNING(f'   ⚠ Cédula inválida "{cedula_str}" para "{nombre}", se omite.')
                )
                errores += 1
                continue

            if cedula_str in empleados_por_doc:
                # Actualizar nombre si cambió
                emp = empleados_por_doc[cedula_str]
                cambios = []
                if emp.nombre != nombre:
                    cambios.append(f'nombre: "{emp.nombre}" → "{nombre}"')
                    emp.nombre = nombre

                if cambios:
                    emp.save(update_fields=['nombre'])
                    actualizados += 1
                    self.stdout.write(f'   ✎ {documento} | {", ".join(cambios)}')
                else:
                    omitidos += 1
            else:
                # Crear nuevo empleado
                emp = Empleado.objects.create(
                    codigo=0,
                    nombre=nombre,
                    documento=documento,
                    cargo=None,
                    excluido=False,
                )
                empleados_por_doc[cedula_str] = emp
                creados += 1
                self.stdout.write(f'   + {documento} | {nombre}')

        self.stdout.write(self.style.SUCCESS(
            f'\nSincronización completada — '
            f'Creados: {creados} | Actualizados: {actualizados} | Sin cambios: {omitidos} | Errores: {errores}'
        ))
