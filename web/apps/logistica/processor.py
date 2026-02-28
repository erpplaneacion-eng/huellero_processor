"""
Procesador de Huellero para el área de Logística
Corporación Hacia un Valle Solidario
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

import config
from src.logger import logger
from src.data_cleaner import DataCleaner
from src.state_inference import StateInference
from src.shift_builder import ShiftBuilder
from src.calculator import Calculator
from src.excel_generator import ExcelGenerator


class HuelleroProcessor:
    """Procesador de archivos de huellero"""

    def __init__(self, area='logistica'):
        """
        Inicializa el procesador

        Args:
            area: Nombre del área (logistica, supervision, etc.)
        """
        self.area = area
        self.maestro_dir = PROJECT_ROOT / 'data' / 'maestro'
        self.output_dir = PROJECT_ROOT / 'data' / 'output'

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
            df_limpio = cleaner.procesar(ruta_archivo)

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

            # ===== FIN DEL PROCESO =====
            logger.log_fin_proceso(exito=True)

            # Preparar respuesta
            nombre_archivo = os.path.basename(ruta_salida)
            nombre_casos = os.path.basename(ruta_casos) if ruta_casos else None

            # Serializar datos para el dashboard frontend
            datos = self._serializar_datos(df_resultado)

            return {
                'success': True,
                'archivo': nombre_archivo,
                'archivo_casos': nombre_casos,
                'stats': stats,
                'area': self.area,
                'datos': datos
            }

        except Exception as e:
            logger.error(f"Error durante el procesamiento: {str(e)}")
            logger.log_fin_proceso(exito=False)
            raise

    def _serializar_datos(self, df):
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

            if codigo not in empleados:
                empleados[codigo] = {
                    'codigo': codigo,
                    'nombre': _str_nonempty(row['NOMBRE COMPLETO DEL COLABORADOR']),
                    'documento': _str_nonempty(row['DOCUMENTO DEL COLABORADOR']),
                    'cargo': _str_nonempty(row['CARGO']),
                    'registros': []
                }
            empleados[codigo]['registros'].append({
                'fecha': _str_nonempty(row['FECHA']),
                'dia': _str_nonempty(row['DIA']),
                'am': _int_safe(row['# MARCACIONES AM']),
                'pm': _int_safe(row['# MARCACIONES PM']),
                'ingreso': _str_nonempty(row['HORA DE INGRESO']),
                'salida': _str_nonempty(row['HORA DE SALIDA']),
                'horas': _float_safe(row['TOTAL HORAS LABORADAS']),
                'limite': _str_nonempty(row['LÍMITE HORAS DÍA']),
                'observacion': _str_nonempty(row['OBSERVACION']),
            })
        return list(empleados.values())
