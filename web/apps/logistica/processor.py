"""
Procesador de Huellero para el área de Logística
Corporación Hacia un Valle Solidario
"""

import os

import pandas as pd

from apps.logistica.pipeline import config
from apps.logistica.pipeline.logger import logger
from apps.logistica.pipeline.data_cleaner import DataCleaner
from apps.logistica.pipeline.state_inference import StateInference
from apps.logistica.pipeline.shift_builder import ShiftBuilder
from apps.logistica.pipeline.calculator import Calculator
from apps.logistica.pipeline.excel_generator import ExcelGenerator


class HuelleroProcessor:
    """Procesador de archivos de huellero"""

    def __init__(self, area='logistica'):
        """
        Inicializa el procesador

        Args:
            area: Nombre del área (logistica, supervision, etc.)
        """
        self.area = area
        self.maestro_dir = config.DIR_MAESTRO
        self.output_dir = config.DIR_OUTPUT

    def _guardar_registros_en_db(self, df_resultado):
        """
        Guarda df_resultado en la tabla RegistroAsistencia usando operaciones bulk.
        1 SELECT para encontrar existentes + 1 INSERT para los nuevos → evita N round-trips.
        Si ya existe un registro (codigo, fecha, hora_ingreso) no lo duplica.

        Returns:
            (
                dict {(codigo, fecha_str, hora_ingreso): {'id', 'obs1'}},
                {'creados': int, 'existentes': int, 'errores': int}
            )
        """
        import math
        from datetime import datetime
        from django.db import transaction
        from apps.logistica.models import RegistroAsistencia

        def _sfloat(v):
            try:
                f = float(v)
                return None if (math.isnan(f) or math.isinf(f)) else f
            except (TypeError, ValueError):
                return None

        # Preparar lista de dicts antes de tocar la DB
        filas = []
        for _, row in df_resultado.iterrows():
            try:
                fecha_str = str(row.get('FECHA', ''))
                fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
                codigo = int(float(row.get('CODIGO COLABORADOR', 0)))
                hora_ingreso = str(row.get('HORA DE INGRESO', '') or '')
                filas.append({
                    'codigo':         codigo,
                    'fecha':          fecha,
                    'fecha_str':      fecha_str,
                    'hora_ingreso':   hora_ingreso,
                    'nombre':         str(row.get('NOMBRE COMPLETO DEL COLABORADOR', '') or ''),
                    'documento':      str(row.get('DOCUMENTO DEL COLABORADOR', '') or ''),
                    'cargo':          str(row.get('CARGO', '') or ''),
                    'dia':            str(row.get('DIA', '') or ''),
                    'marcaciones_am': int(row.get('# MARCACIONES AM', 0) or 0),
                    'marcaciones_pm': int(row.get('# MARCACIONES PM', 0) or 0),
                    'hora_salida':    str(row.get('HORA DE SALIDA', '') or ''),
                    'total_horas':    _sfloat(row.get('TOTAL HORAS LABORADAS')),
                    'limite_horas_dia': str(row.get('LÍMITE HORAS DÍA', '') or ''),
                    'observacion':    str(row.get('OBSERVACION', '') or ''),
                    'observaciones_1': str(row.get('OBSERVACIONES_1', '') or ''),
                })
            except Exception as e:
                logger.warning(f"Error preparando fila para BD: {e}")

        if not filas:
            return {}, {'creados': 0, 'existentes': 0, 'errores': 0}

        codigos = {f['codigo'] for f in filas}
        fechas  = {f['fecha']  for f in filas}

        # ── 1 SELECT: todos los registros existentes para estos empleados y fechas ──
        existentes_db = {
            (r.codigo, r.fecha.strftime('%d/%m/%Y'), r.hora_ingreso): {
                'id': r.id, 'obs1': r.observaciones_1,
            }
            for r in RegistroAsistencia.objects.filter(
                codigo__in=codigos, fecha__in=fechas
            ).only('id', 'codigo', 'fecha', 'hora_ingreso', 'observaciones_1')
        }

        # Determinar qué filas son nuevas
        nuevos_filas = [
            f for f in filas
            if (f['codigo'], f['fecha_str'], f['hora_ingreso']) not in existentes_db
        ]

        creados = errores = 0

        if nuevos_filas:
            objs = []
            for f in nuevos_filas:
                try:
                    objs.append(RegistroAsistencia(
                        codigo=f['codigo'],
                        fecha=f['fecha'],
                        hora_ingreso=f['hora_ingreso'],
                        nombre=f['nombre'],
                        documento=f['documento'],
                        cargo=f['cargo'],
                        dia=f['dia'],
                        marcaciones_am=f['marcaciones_am'],
                        marcaciones_pm=f['marcaciones_pm'],
                        hora_salida=f['hora_salida'],
                        total_horas=f['total_horas'],
                        limite_horas_dia=f['limite_horas_dia'],
                        observacion=f['observacion'],
                        observaciones_1=f['observaciones_1'],
                    ))
                except Exception as e:
                    errores += 1
                    logger.warning(f"Error preparando objeto BD: {e}")

            if objs:
                try:
                    # ── 1 INSERT bulk para todos los nuevos ──
                    with transaction.atomic():
                        RegistroAsistencia.objects.bulk_create(objs, ignore_conflicts=True)
                    creados = len(objs)

                    # Re-fetch para obtener IDs de los recién creados
                    nuevos_codigos = {f['codigo'] for f in nuevos_filas}
                    nuevos_fechas  = {f['fecha']  for f in nuevos_filas}
                    nuevos_db = {
                        (r.codigo, r.fecha.strftime('%d/%m/%Y'), r.hora_ingreso): {
                            'id': r.id, 'obs1': r.observaciones_1,
                        }
                        for r in RegistroAsistencia.objects.filter(
                            codigo__in=nuevos_codigos, fecha__in=nuevos_fechas
                        ).only('id', 'codigo', 'fecha', 'hora_ingreso', 'observaciones_1')
                    }
                    existentes_db.update(nuevos_db)
                except Exception as e:
                    errores += len(objs)
                    logger.warning(f"Error en bulk_create: {e}")

        existentes_count = len(filas) - len(nuevos_filas)

        # Construir lookup final
        lookup = {
            (f['codigo'], f['fecha_str'], f['hora_ingreso']): existentes_db.get(
                (f['codigo'], f['fecha_str'], f['hora_ingreso']), {}
            )
            for f in filas
        }

        logger.info(f"Registros BD — nuevos: {creados} | ya existían: {existentes_count} | errores: {errores}")
        return lookup, {
            'creados': int(creados),
            'existentes': int(existentes_count),
            'errores': int(errores),
        }

    def _cargar_codigos_excluidos(self):
        """Retorna un set con los códigos de empleados marcados como excluidos en la DB."""
        try:
            from apps.logistica.models import Empleado
            codigos = set(
                Empleado.objects.filter(excluido=True).values_list('codigo', flat=True)
            )
            if codigos:
                logger.info(f"Empleados excluidos del análisis: {len(codigos)} códigos")
            return codigos
        except Exception as e:
            logger.warning(f"No se pudo cargar lista de excluidos: {e}")
            return set()

    def _cargar_horarios_por_codigo(self):
        """
        Consulta la DB y retorna un dict {codigo_empleado: [(entrada_min, salida_min), ...]}
        con todos los turnos posibles para el cargo de cada empleado.
        """
        try:
            from apps.logistica.models import Empleado

            horarios_por_codigo = {}
            empleados = (
                Empleado.objects
                .select_related('cargo')
                .prefetch_related('cargo__horarios__horario')
                .exclude(cargo=None)
            )
            for emp in empleados:
                turnos = []
                for ch in emp.cargo.horarios.select_related('horario').all():
                    h = ch.horario
                    entrada_min = h.hora_inicio.hour * 60 + h.hora_inicio.minute
                    salida_min  = h.hora_fin.hour  * 60 + h.hora_fin.minute
                    turnos.append((entrada_min, salida_min))
                if turnos:
                    horarios_por_codigo[emp.codigo] = turnos

            logger.info(f"Horarios cargados desde DB para {len(horarios_por_codigo)} empleados")
            return horarios_por_codigo

        except Exception as e:
            logger.warning(f"No se pudo cargar horarios desde DB: {e}")
            return {}

    def _cargar_maestro_desde_db(self):
        """
        Consulta los modelos Empleado, Cargo y Concepto desde PostgreSQL
        y retorna DataFrames con la misma estructura que el Excel maestro.

        Returns:
            (df_empleados, df_cargos, df_conceptos) — cualquiera puede ser None
            si la tabla está vacía o hay un error.
        """
        try:
            from apps.logistica.models import Cargo, Concepto, Empleado

            # ── Empleados ────────────────────────────────────────────────────
            empleados_qs = Empleado.objects.select_related('cargo').values(
                'codigo', 'nombre', 'documento', 'cargo__id_cargo'
            )
            if empleados_qs.exists():
                df_empleados = pd.DataFrame(list(empleados_qs))
                df_empleados = df_empleados.rename(columns={'cargo__id_cargo': 'CARGO'})
                df_empleados.columns = [c.upper() if c != 'CARGO' else 'CARGO' for c in df_empleados.columns]
            else:
                df_empleados = None

            # ── Cargos ───────────────────────────────────────────────────────
            cargos_qs = Cargo.objects.values(
                'id_cargo', 'cargo', 'horas_dia', 'horas_semana', 'numero_colaboradores'
            )
            if cargos_qs.exists():
                df_cargos = pd.DataFrame(list(cargos_qs))
            else:
                df_cargos = None

            # ── Conceptos ────────────────────────────────────────────────────
            conceptos_qs = Concepto.objects.values('observaciones')
            if conceptos_qs.exists():
                df_conceptos = pd.DataFrame(list(conceptos_qs))
            else:
                df_conceptos = None

            return df_empleados, df_cargos, df_conceptos

        except Exception as e:
            logger.warning(f"No se pudo cargar maestro desde DB: {e}")
            return None, None, None

    def procesar(self, ruta_archivo, usar_maestro=True):
        """
        Procesa el archivo de huellero

        Args:
            ruta_archivo: Ruta al archivo de entrada
            usar_maestro: Si debe usar archivo maestro

        Returns:
            Dict con resultado del procesamiento
        """
        logger.log_inicio_proceso(ruta_archivo)

        try:
            # ===== FASE 1: LIMPIEZA DE DATOS =====
            cleaner = DataCleaner()
            codigos_excluidos = self._cargar_codigos_excluidos()
            df_limpio = cleaner.procesar(ruta_archivo, codigos_excluidos)

            # ===== FASE 2: INFERENCIA DE ESTADOS =====
            inference = StateInference()
            horarios_por_codigo = self._cargar_horarios_por_codigo()
            df_con_estados = inference.inferir_estados(df_limpio, horarios_por_codigo)

            # ===== FASE 3: CONSTRUCCIÓN DE TURNOS =====
            builder = ShiftBuilder()
            df_turnos = builder.construir_turnos(df_con_estados)

            # ===== FASE 4: CÁLCULO DE MÉTRICAS =====
            calculator = Calculator()
            df_resultado = calculator.calcular_metricas(df_turnos, df_con_estados)

            # Agregar datos de maestro desde PostgreSQL
            df_conceptos = None
            if usar_maestro:
                df_empleados, df_cargos, df_conceptos = self._cargar_maestro_desde_db()
                if df_empleados is not None:
                    df_resultado = calculator.agregar_datos_maestro(df_resultado, df_empleados, df_cargos)
                else:
                    logger.warning("Maestro no disponible en DB — documentos quedarán vacíos")

            # ===== FASE 5: GENERACIÓN DE EXCEL =====
            generator = ExcelGenerator()

            # Preparar estadísticas
            stats_cleaner = cleaner.obtener_resumen()
            stats_inference = inference.obtener_resumen()
            stats_builder = builder.obtener_resumen()

            # Convertir a int nativo de Python para evitar errores de serialización JSON
            stats = {
                'empleados_unicos': int(df_resultado['CODIGO COLABORADOR'].nunique()),
                'total_registros': int(len(df_resultado)),
                'turnos_completos': int(stats_builder.get('turnos_completos', 0)),
                'turnos_incompletos': int(stats_builder.get('turnos_incompletos', 0)),
                'duplicados_eliminados': int(stats_cleaner.get('duplicados_eliminados', 0)),
                'estados_inferidos': int(stats_inference.get('total_inferencias', 0)),
            }

            # Generar Excel
            ruta_salida = generator.generar_excel(df_resultado, stats, df_conceptos=df_conceptos)

            # Generar casos especiales
            ruta_casos = generator.generar_casos_especiales(df_resultado)

            # ===== GUARDAR EN BASE DE DATOS =====
            db_lookup, db_stats = self._guardar_registros_en_db(df_resultado)

            # ===== FIN DEL PROCESO =====
            logger.log_fin_proceso(exito=True)

            # Preparar respuesta
            nombre_archivo = os.path.basename(ruta_salida)
            nombre_casos = os.path.basename(ruta_casos) if ruta_casos else None

            # Serializar datos para el dashboard frontend (con IDs de BD)
            datos = self._serializar_datos(df_resultado, db_lookup, horarios_por_codigo)

            # Opciones de conceptos para el dropdown en el dashboard
            from apps.logistica.models import Concepto
            conceptos = list(Concepto.objects.values_list('observaciones', flat=True).order_by('observaciones'))

            return {
                'success': True,
                'archivo': nombre_archivo,
                'archivo_casos': nombre_casos,
                'stats': stats,
                'db_stats': db_stats,
                'area': self.area,
                'datos': datos,
                'conceptos': conceptos,
            }

        except Exception as e:
            logger.error(f"Error durante el procesamiento: {str(e)}")
            logger.log_fin_proceso(exito=False)
            raise

    def _serializar_datos(self, df, db_lookup=None, horarios_por_codigo=None):
        """Agrupa el DataFrame por empleado para el dashboard frontend."""
        import pandas as pd

        def _int_safe(val):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0

        def _float_safe(val):
            try:
                import math
                f = float(val)
                return round(f, 2) if not math.isnan(f) else None
            except (ValueError, TypeError):
                return None

        def _str_nonempty(val):
            """Devuelve str si el valor no es NaN ni cadena vacía, si no ''."""
            if pd.isna(val):
                return ''
            s = str(val).strip()
            return s if s not in ('', 'nan', 'None') else ''

        empleados = {}
        for _, row in df.iterrows():
            raw_codigo = row['CODIGO COLABORADOR']
            if pd.isna(raw_codigo) or str(raw_codigo).strip() == '':
                continue
            codigo = str(_int_safe(raw_codigo))
            codigo_int = int(float(raw_codigo))

            if codigo not in empleados:
                empleados[codigo] = {
                    'codigo': codigo,
                    'nombre': _str_nonempty(row['NOMBRE COMPLETO DEL COLABORADOR']),
                    'documento': _str_nonempty(row['DOCUMENTO DEL COLABORADOR']),
                    'cargo': _str_nonempty(row['CARGO']),
                    'registros': []
                }
            fecha_str    = _str_nonempty(row['FECHA'])
            hora_ingreso = _str_nonempty(row['HORA DE INGRESO'])
            db_key = (codigo_int, fecha_str, hora_ingreso)
            db_info = (db_lookup or {}).get(db_key, {})

            # Best-fit: turno del cargo más cercano a la hora de ingreso real
            turno_str = ''
            if horarios_por_codigo and hora_ingreso and ':' in hora_ingreso:
                turnos_raw = horarios_por_codigo.get(codigo_int, [])
                if turnos_raw:
                    try:
                        parts = hora_ingreso.split(':')
                        ingreso_min = int(parts[0]) * 60 + int(parts[1])
                        e, s = min(turnos_raw, key=lambda t: abs(t[0] - ingreso_min))
                        turno_str = f"{e//60:02d}:{e%60:02d}-{s//60:02d}:{s%60:02d}"
                    except Exception:
                        pass

            empleados[codigo]['registros'].append({
                'id':          db_info.get('id'),
                'fecha':       fecha_str,
                'dia':         _str_nonempty(row['DIA']),
                'am':          _int_safe(row['# MARCACIONES AM']),
                'pm':          _int_safe(row['# MARCACIONES PM']),
                'ingreso':     hora_ingreso,
                'salida':      _str_nonempty(row['HORA DE SALIDA']),
                'horas':       _float_safe(row['TOTAL HORAS LABORADAS']),
                'limite':      _str_nonempty(row['LÍMITE HORAS DÍA']),
                'observacion': _str_nonempty(row['OBSERVACION']),
                'obs1':        db_info.get('obs1', ''),
                'turno':       turno_str,
            })
        return list(empleados.values())
