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
        self.area = area
        self.maestro_dir = config.DIR_MAESTRO
        self.output_dir = config.DIR_OUTPUT

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

            empleados_qs = Empleado.objects.select_related('cargo').values(
                'codigo', 'nombre', 'documento', 'cargo__id_cargo'
            )
            if empleados_qs.exists():
                df_empleados = pd.DataFrame(list(empleados_qs))
                df_empleados = df_empleados.rename(columns={'cargo__id_cargo': 'CARGO'})
                df_empleados.columns = [c.upper() if c != 'CARGO' else 'CARGO' for c in df_empleados.columns]
            else:
                df_empleados = None

            cargos_qs = Cargo.objects.values(
                'id_cargo', 'cargo', 'horas_dia', 'horas_semana', 'numero_colaboradores'
            )
            df_cargos = pd.DataFrame(list(cargos_qs)) if cargos_qs.exists() else None

            conceptos_qs = Concepto.objects.values('observaciones')
            df_conceptos = pd.DataFrame(list(conceptos_qs)) if conceptos_qs.exists() else None

            return df_empleados, df_cargos, df_conceptos

        except Exception as e:
            logger.warning(f"No se pudo cargar maestro desde DB: {e}")
            return None, None, None

    def procesar(self, ruta_archivo, usar_maestro=True):
        """
        Procesa el archivo de huellero y genera los Excel de salida.

        Returns:
            Dict con: success, archivo, archivo_casos, stats
        """
        logger.log_inicio_proceso(ruta_archivo)

        try:
            # FASE 1: Limpieza
            cleaner = DataCleaner()
            codigos_excluidos = self._cargar_codigos_excluidos()
            df_limpio = cleaner.procesar(ruta_archivo, codigos_excluidos)

            # FASE 2: Inferencia de estados
            inference = StateInference()
            horarios_por_codigo = self._cargar_horarios_por_codigo()
            df_con_estados = inference.inferir_estados(df_limpio, horarios_por_codigo)

            # FASE 3: Construcción de turnos
            builder = ShiftBuilder()
            df_turnos = builder.construir_turnos(df_con_estados)

            # FASE 4: Cálculo de métricas
            calculator = Calculator()
            df_resultado = calculator.calcular_metricas(df_turnos, df_con_estados)

            # Agregar datos de maestro (nombres, cédulas, cargos) desde DB
            # y cargar conceptos para el dropdown de OBSERVACIONES_1 en el Excel
            df_empleados, df_cargos, df_conceptos = self._cargar_maestro_desde_db()

            if usar_maestro:
                if df_empleados is not None:
                    df_resultado = calculator.agregar_datos_maestro(df_resultado, df_empleados, df_cargos)
                else:
                    logger.warning("Maestro no disponible en DB — nombres y documentos vendrán del huellero")

            # FASE 5: Generación de Excel
            generator = ExcelGenerator()

            stats_cleaner = cleaner.obtener_resumen()
            stats_inference = inference.obtener_resumen()
            stats_builder = builder.obtener_resumen()

            stats = {
                'empleados_unicos':      int(df_resultado['CODIGO COLABORADOR'].nunique()),
                'total_registros':       int(len(df_resultado)),
                'turnos_completos':      int(stats_builder.get('turnos_completos', 0)),
                'turnos_incompletos':    int(stats_builder.get('turnos_incompletos', 0)),
                'duplicados_eliminados': int(stats_cleaner.get('duplicados_eliminados', 0)),
                'estados_inferidos':     int(stats_inference.get('total_inferencias', 0)),
            }

            ruta_salida = generator.generar_excel(df_resultado, stats, df_conceptos=df_conceptos)
            ruta_casos  = generator.generar_casos_especiales(df_resultado)

            logger.log_fin_proceso(exito=True)

            return {
                'success':       True,
                'archivo':       os.path.basename(ruta_salida),
                'archivo_casos': os.path.basename(ruta_casos) if ruta_casos else None,
                'stats':         stats,
            }

        except Exception as e:
            logger.error(f"Error durante el procesamiento: {str(e)}")
            logger.log_fin_proceso(exito=False)
            raise
