"""
Management command: cargar_maestro

Lee todas las hojas del archivo Excel maestro (data/maestro/empleados.xlsx)
y carga los registros en la base de datos PostgreSQL.

Orden de carga:
  1. horas_cargos  → Cargo
  2. horarios      → Horario
  3. cargos_horarios → CargoHorario
  4. empleados_ejemplo → Empleado
  5. conceptos     → Concepto

Uso:
  python manage.py cargar_maestro
  python manage.py cargar_maestro --ruta /ruta/personalizada/empleados.xlsx
  python manage.py cargar_maestro --limpiar   # borra registros previos antes de cargar
"""

import os
import math
from datetime import time

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from apps.logistica.models import Cargo, CargoHorario, Concepto, Empleado, Horario


RUTA_DEFAULT = os.path.join(
    os.path.dirname(__file__),
    '..', '..', '..', '..', '..', '..', 'data', 'maestro', 'empleados.xlsx'
)


def _parse_time(valor) -> time | None:
    """Convierte un string 'HH:MM:SS' o 'HH:MM' a un objeto time."""
    if not valor or (isinstance(valor, float) and math.isnan(valor)):
        return None
    s = str(valor).strip()
    partes = s.split(':')
    try:
        if len(partes) >= 2:
            hora = int(partes[0])
            minuto = int(partes[1])
            segundo = int(partes[2]) if len(partes) > 2 else 0
            return time(hora, minuto, segundo)
    except (ValueError, TypeError):
        pass
    return None


def _safe_int(valor, default=0) -> int:
    try:
        if isinstance(valor, float) and math.isnan(valor):
            return default
        return int(valor)
    except (ValueError, TypeError):
        return default


def _safe_float(valor, default=0.0) -> float:
    try:
        if isinstance(valor, float) and math.isnan(valor):
            return default
        return float(valor)
    except (ValueError, TypeError):
        return default


def _safe_str(valor, default='') -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return default
    return str(valor).strip()


class Command(BaseCommand):
    help = 'Carga los datos del Excel maestro (empleados.xlsx) en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ruta',
            type=str,
            default=None,
            help='Ruta al archivo Excel maestro. Por defecto: data/maestro/empleados.xlsx',
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            default=False,
            help='Elimina todos los registros existentes antes de cargar.',
        )

    def handle(self, *args, **options):
        ruta = options['ruta'] or os.path.normpath(RUTA_DEFAULT)

        if not os.path.exists(ruta):
            raise CommandError(f"No se encontró el archivo: {ruta}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n📂 Leyendo archivo: {ruta}"))

        try:
            xl = pd.ExcelFile(ruta)
        except Exception as e:
            raise CommandError(f"Error al abrir el Excel: {e}")

        hojas_disponibles = xl.sheet_names
        self.stdout.write(f"   Hojas encontradas: {hojas_disponibles}\n")

        if options['limpiar']:
            self.stdout.write(self.style.WARNING("⚠️  Limpiando registros existentes..."))
            CargoHorario.objects.all().delete()
            Empleado.objects.all().delete()
            Cargo.objects.all().delete()
            Horario.objects.all().delete()
            Concepto.objects.all().delete()
            self.stdout.write("   Hecho.\n")

        # ── 1. Cargos ────────────────────────────────────────────────────────
        self._cargar_cargos(xl)

        # ── 2. Horarios ──────────────────────────────────────────────────────
        self._cargar_horarios(xl)

        # ── 3. Cargos-Horarios ───────────────────────────────────────────────
        self._cargar_cargos_horarios(xl)

        # ── 4. Empleados ─────────────────────────────────────────────────────
        self._cargar_empleados(xl)

        # ── 5. Conceptos ─────────────────────────────────────────────────────
        self._cargar_conceptos(xl)

        self.stdout.write(self.style.SUCCESS("\n✅ Carga completada exitosamente.\n"))

    # ── Métodos privados de carga ─────────────────────────────────────────────

    def _cargar_cargos(self, xl: pd.ExcelFile):
        self.stdout.write(self.style.MIGRATE_HEADING("📋 [1/5] Cargando hoja: horas_cargos → Cargo"))
        df = pd.read_excel(xl, sheet_name='horas_cargos')
        creados = actualizados = errores = 0

        for _, fila in df.iterrows():
            id_cargo = _safe_str(fila.get('id_cargo'))
            if not id_cargo:
                errores += 1
                continue
            _, creado = Cargo.objects.update_or_create(
                id_cargo=id_cargo,
                defaults={
                    'cargo': _safe_str(fila.get('cargo')),
                    'numero_colaboradores': _safe_int(fila.get('numero_colaboradores')),
                    'horas_semana': _safe_int(fila.get('horas_semana')),
                    'horas_dia': _safe_float(fila.get('horas_dia')),
                },
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self._resumen(creados, actualizados, errores)

    def _cargar_horarios(self, xl: pd.ExcelFile):
        self.stdout.write(self.style.MIGRATE_HEADING("🕐 [2/5] Cargando hoja: horarios → Horario"))
        df = pd.read_excel(xl, sheet_name='horarios')
        creados = actualizados = errores = 0

        for _, fila in df.iterrows():
            id_horario = _safe_int(fila.get('id_horario'), default=None)
            if id_horario is None:
                errores += 1
                continue
            hora_inicio = _parse_time(fila.get('hora_inicio'))
            hora_fin = _parse_time(fila.get('hora_fin'))
            if hora_inicio is None or hora_fin is None:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠ Horario {id_horario}: horas inválidas, se omite.")
                )
                errores += 1
                continue

            _, creado = Horario.objects.update_or_create(
                id_horario=id_horario,
                defaults={'hora_inicio': hora_inicio, 'hora_fin': hora_fin},
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self._resumen(creados, actualizados, errores)

    def _cargar_cargos_horarios(self, xl: pd.ExcelFile):
        self.stdout.write(self.style.MIGRATE_HEADING("🔗 [3/5] Cargando hoja: cargos_horarios → CargoHorario"))
        df = pd.read_excel(xl, sheet_name='cargos_horarios')
        creados = omitidos = errores = 0

        for _, fila in df.iterrows():
            id_cargo = _safe_str(fila.get('id_cargo'))
            id_horario = _safe_int(fila.get('id_horario'), default=None)
            if not id_cargo or id_horario is None:
                errores += 1
                continue
            try:
                cargo = Cargo.objects.get(id_cargo=id_cargo)
                horario = Horario.objects.get(id_horario=id_horario)
            except (Cargo.DoesNotExist, Horario.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f"   ⚠ {e}, se omite fila."))
                errores += 1
                continue

            _, creado = CargoHorario.objects.get_or_create(cargo=cargo, horario=horario)
            if creado:
                creados += 1
            else:
                omitidos += 1

        self._resumen(creados, omitidos, errores, label_existentes='ya existían')

    def _cargar_empleados(self, xl: pd.ExcelFile):
        self.stdout.write(self.style.MIGRATE_HEADING("👤 [4/5] Cargando hoja: empleados_ejemplo → Empleado"))
        df = pd.read_excel(xl, sheet_name='empleados_ejemplo')
        creados = actualizados = errores = 0

        for _, fila in df.iterrows():
            nombre = _safe_str(fila.get('NOMBRE'))
            if not nombre:
                errores += 1
                continue

            codigo = _safe_int(fila.get('CODIGO'))

            doc_raw = fila.get('DOCUMENTO')
            if doc_raw is None or (isinstance(doc_raw, float) and math.isnan(doc_raw)):
                documento = None
            else:
                try:
                    documento = int(float(doc_raw))
                except (ValueError, TypeError):
                    documento = None

            id_cargo = _safe_str(fila.get('CARGO')) or None
            cargo_obj = None
            if id_cargo:
                try:
                    cargo_obj = Cargo.objects.get(id_cargo=id_cargo)
                except Cargo.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠ Cargo '{id_cargo}' no existe para '{nombre}', se asigna NULL.")
                    )

            # update_or_create por (codigo, nombre)
            _, creado = Empleado.objects.update_or_create(
                codigo=codigo,
                nombre=nombre,
                defaults={'documento': documento, 'cargo': cargo_obj},
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self._resumen(creados, actualizados, errores)

    def _cargar_conceptos(self, xl: pd.ExcelFile):
        self.stdout.write(self.style.MIGRATE_HEADING("📝 [5/5] Cargando hoja: conceptos → Concepto"))
        df = pd.read_excel(xl, sheet_name='conceptos')
        creados = omitidos = errores = 0

        for _, fila in df.iterrows():
            obs = _safe_str(fila.get('observaciones'))
            if not obs:
                errores += 1
                continue
            procesos = _safe_str(fila.get('procesos'))
            _, creado = Concepto.objects.get_or_create(
                observaciones=obs,
                defaults={'procesos': procesos},
            )
            if creado:
                creados += 1
            else:
                omitidos += 1

        self._resumen(creados, omitidos, errores, label_existentes='ya existían')

    def _resumen(self, creados, secundarios, errores, label_existentes='actualizados'):
        self.stdout.write(
            f"   ✔ Creados: {creados} | {label_existentes}: {secundarios} | Errores/omitidos: {errores}"
        )
