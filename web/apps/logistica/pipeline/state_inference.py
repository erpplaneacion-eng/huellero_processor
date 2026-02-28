"""
Módulo de Inferencia de Estados
Deduce si una marcación sin estado es Entrada o Salida
"""

import pandas as pd
from . import config
from .logger import logger


class StateInference:
    """Infiere estados faltantes (NaN) basándose en contexto"""

    def __init__(self):
        """Inicializa el inferidor de estados"""
        self.inferencias_realizadas = []

    def inferir_por_hora(self, hora):
        """
        Infiere estado basándose en la hora del día

        Args:
            hora: Hora (0-23)

        Returns:
            'Entrada', 'Salida', o None si no se puede inferir
        """
        # Verificar rangos de entrada
        for rango_inicio, rango_fin in config.RANGO_INFERENCIA_ENTRADA:
            if rango_inicio <= hora < rango_fin:
                return 'Entrada'

        # Verificar rangos de salida
        for rango_inicio, rango_fin in config.RANGO_INFERENCIA_SALIDA:
            if rango_inicio <= hora < rango_fin:
                return 'Salida'

        return None

    def inferir_por_contexto(self, df_empleado, idx_actual):
        """
        Infiere estado basándose en marcaciones anteriores/posteriores

        Args:
            df_empleado: DataFrame del empleado
            idx_actual: Índice de la marcación actual

        Returns:
            'Entrada', 'Salida', o None
        """
        # Obtener marcación actual
        registro_actual = df_empleado.iloc[idx_actual]

        # Buscar marcación anterior válida
        estado_anterior = None
        for i in range(idx_actual - 1, -1, -1):
            if pd.notna(df_empleado.iloc[i]['ESTADO']):
                estado_anterior = df_empleado.iloc[i]['ESTADO']
                break

        # Buscar marcación posterior válida
        estado_posterior = None
        for i in range(idx_actual + 1, len(df_empleado)):
            if pd.notna(df_empleado.iloc[i]['ESTADO']):
                estado_posterior = df_empleado.iloc[i]['ESTADO']
                break

        # Lógica de inferencia
        if estado_anterior == 'Entrada' and (estado_posterior is None or estado_posterior == 'Entrada'):
            # Después de entrada sin salida registrada -> probablemente Salida
            return 'Salida'

        if estado_anterior == 'Salida' and (estado_posterior is None or estado_posterior == 'Salida'):
            # Después de salida -> probablemente Entrada
            return 'Entrada'

        if estado_anterior is None and estado_posterior == 'Salida':
            # Antes de salida -> probablemente Entrada
            return 'Entrada'

        if estado_anterior is None and estado_posterior == 'Entrada':
            # Antes de entrada -> podría ser Salida del turno anterior
            # Verificar hora
            hora = registro_actual['FECHA_HORA'].hour
            if hora < 10:  # Madrugada
                return 'Salida'

        return None

    def inferir_por_horario_cargo(self, timestamps_dia, horarios):
        """
        Encuentra el turno de mejor ajuste para los registros de un empleado
        en un día y etiqueta cada timestamp como 'Entrada' o 'Salida'.

        Para cargos con múltiples turnos (hasta 6), evalúa todos y elige el que
        minimiza la desviación total entre el primer/último registro del día y
        las horas de entrada/salida esperadas del turno.

        Args:
            timestamps_dia: lista de datetime con TODOS los registros del día
                            (incluyendo los que ya tienen estado conocido)
            horarios: list of (entrada_min, salida_min) en minutos desde medianoche.
                      Para turnos nocturnos salida_min puede ser < entrada_min.

        Returns:
            dict {timestamp: 'Entrada'|'Salida'} con la etiqueta inferida,
            o {} si ningún turno encaja dentro de la tolerancia configurada.
        """
        if not horarios or not timestamps_dia:
            return {}

        def to_min(dt):
            return dt.hour * 60 + dt.minute

        def normalizar(h_ini, h_fin):
            # Turno nocturno: salida del día siguiente → sumar 1440 min (24h)
            return (h_ini, h_fin + 1440 if h_fin < h_ini else h_fin)

        ts_sorted = sorted(timestamps_dia, key=to_min)
        ts_primero = to_min(ts_sorted[0])
        ts_ultimo  = to_min(ts_sorted[-1])

        mejor_horario = None
        mejor_dev     = float('inf')

        for h_ini, h_fin in horarios:
            h_ini_n, h_fin_n = normalizar(h_ini, h_fin)

            # Para turnos nocturnos, la salida cruza medianoche.
            # Si el último ts es de madrugada (< 8h), interpretarlo como día siguiente.
            ts_ult_adj = ts_ultimo
            if h_fin_n > 1440 and ts_ultimo < 480:
                ts_ult_adj = ts_ultimo + 1440

            if len(ts_sorted) >= 2:
                dev = abs(ts_primero - h_ini_n) + abs(ts_ult_adj - h_fin_n)
            else:
                # Un solo registro: tomar la distancia mínima a entrada o salida
                dev = min(abs(ts_primero - h_ini_n), abs(ts_ult_adj - h_fin_n))

            if dev < mejor_dev:
                mejor_dev     = dev
                mejor_horario = (h_ini_n, h_fin_n)

        # Si la desviación supera la tolerancia por extremo → no inferir
        n_extremos = 1 if len(ts_sorted) == 1 else 2
        if mejor_dev > config.TOLERANCIA_HORARIO_MIN * n_extremos:
            return {}

        # Etiquetar cada timestamp según proximidad al mejor horario
        resultado = {}
        h_ini_n, h_fin_n = mejor_horario

        for ts in timestamps_dia:
            ts_min = to_min(ts)
            if h_fin_n > 1440 and ts_min < 480:
                ts_min += 1440
            dist_ent = abs(ts_min - h_ini_n)
            dist_sal = abs(ts_min - h_fin_n)
            resultado[ts] = 'Entrada' if dist_ent <= dist_sal else 'Salida'

        return resultado

    def _tiene_entrada_nocturna_dia_anterior(self, df_empleado, fecha, horarios):
        """
        Determina si el empleado tuvo una entrada de turno nocturno el día anterior,
        lo que implica que los registros de madrugada del día actual son la SALIDA
        de ese turno y no una nueva ENTRADA.

        Condiciones para retornar True:
          1. El cargo tiene al menos un turno nocturno (hora_fin < hora_entrada).
          2. El día anterior existe al menos un registro cuya hora esté dentro de
             la ventana de entrada del turno nocturno (±TOLERANCIA_HORARIO_MIN).

        Args:
            df_empleado: DataFrame con todos los registros del empleado.
            fecha: date del día que se está evaluando (el "día siguiente").
            horarios: list of (entrada_min, salida_min) del cargo.

        Returns:
            True si se confirma contexto nocturno del día anterior, False si no.
        """
        from datetime import timedelta

        # Identificar turnos nocturnos del cargo (salida cruda < entrada)
        turnos_nocturnos = [
            (h_ini, h_fin) for h_ini, h_fin in horarios if h_fin < h_ini
        ]
        if not turnos_nocturnos:
            return False

        # Buscar registros del día anterior
        dia_anterior = fecha - timedelta(days=1)
        mask = df_empleado['FECHA_HORA'].dt.date == dia_anterior
        registros_ant = df_empleado[mask]

        if registros_ant.empty:
            return False

        # Verificar si algún registro del día anterior está cerca de
        # la hora de entrada del turno nocturno
        for h_ini, _ in turnos_nocturnos:
            for _, reg in registros_ant.iterrows():
                reg_min = reg['FECHA_HORA'].hour * 60 + reg['FECHA_HORA'].minute
                if abs(reg_min - h_ini) <= config.TOLERANCIA_HORARIO_MIN:
                    return True

        return False

    def inferir_por_patron_empleado(self, df_empleado):
        """
        Analiza el patrón histórico del empleado

        Args:
            df_empleado: DataFrame del empleado

        Returns:
            Dict con información del patrón
        """
        # Analizar marcaciones válidas
        marcaciones_validas = df_empleado[df_empleado['ESTADO'].notna()]

        if len(marcaciones_validas) == 0:
            return {'tipo_turno': 'desconocido'}

        # Analizar horas de entrada
        entradas = marcaciones_validas[marcaciones_validas['ESTADO'] == 'Entrada']

        if len(entradas) > 0:
            horas_entrada = entradas['FECHA_HORA'].dt.hour
            hora_promedio_entrada = horas_entrada.mean()

            if hora_promedio_entrada >= config.HORA_INICIO_TURNO_NOCTURNO:
                return {'tipo_turno': 'nocturno', 'hora_entrada_tipica': hora_promedio_entrada}
            else:
                return {'tipo_turno': 'diurno', 'hora_entrada_tipica': hora_promedio_entrada}

        return {'tipo_turno': 'desconocido'}

    def inferir_estados(self, df, horarios_por_codigo=None):
        """
        Infiere todos los estados faltantes en el DataFrame.

        Aplica los métodos en orden de precisión:
          0. Por horario de cargo (si se provee horarios_por_codigo) — más preciso
          1. Por hora del día (rangos globales en config)
          2. Por contexto (registros adyacentes del mismo empleado)
          3. Por patrón histórico del empleado (nocturno/diurno)

        Args:
            df: DataFrame con los datos
            horarios_por_codigo: dict {codigo: [(entrada_min, salida_min), ...]}
                                 Obtenido desde DB o Excel. Opcional.

        Returns:
            DataFrame con estados inferidos
        """
        logger.log_fase("INFERENCIA DE ESTADOS")

        if not config.PERMITIR_INFERENCIA:
            logger.info("Inferencia de estados desactivada")
            return df

        df_procesado = df.copy()

        estados_nan = df_procesado['ESTADO'].isna().sum()
        logger.info(f"Estados faltantes detectados: {estados_nan}")

        if estados_nan == 0:
            logger.info("No hay estados para inferir")
            return df_procesado

        if horarios_por_codigo:
            logger.info("Método 0 activo: inferencia por horario de cargo")

        # Procesar por empleado
        for codigo in df_procesado['CODIGO'].unique():
            df_empleado = df_procesado[df_procesado['CODIGO'] == codigo].copy()

            # ── Método 0: Por horario de cargo ───────────────────────────────
            if horarios_por_codigo and codigo in horarios_por_codigo:
                horarios = horarios_por_codigo[codigo]

                for fecha in df_empleado['FECHA_HORA'].dt.date.unique():
                    mask_dia = df_empleado['FECHA_HORA'].dt.date == fecha
                    idx_dia  = df_empleado.index[mask_dia].tolist()

                    # Solo actuar si el día tiene al menos un NaN
                    if not any(pd.isna(df_empleado.loc[i, 'ESTADO']) for i in idx_dia):
                        continue

                    # ── Contexto nocturno del día anterior ───────────────────
                    # Si el empleado tuvo una entrada nocturna ayer, los registros
                    # de madrugada de hoy son la SALIDA de ese turno.
                    # Se corrigen tanto los NaN como los que el dispositivo marcó
                    # incorrectamente como "Entrada" (error común del huellero).
                    if self._tiene_entrada_nocturna_dia_anterior(df_empleado, fecha, horarios):
                        for idx in idx_dia:
                            ts = df_empleado.loc[idx, 'FECHA_HORA']
                            estado_actual = df_empleado.loc[idx, 'ESTADO']
                            es_madrugada = ts.hour < 8

                            # Aplica si: es madrugada Y (sin estado O device marcó "Entrada")
                            if es_madrugada and (pd.isna(estado_actual) or estado_actual == 'Entrada'):
                                metodo = (
                                    'nocturno_dia_anterior'
                                    if pd.isna(estado_actual)
                                    else 'nocturno_dia_anterior_correccion'
                                )
                                df_procesado.loc[idx, 'ESTADO'] = 'Salida'
                                df_procesado.loc[idx, 'ESTADO_INFERIDO'] = True
                                df_empleado.loc[idx, 'ESTADO'] = 'Salida'
                                registro = df_empleado.loc[idx]
                                logger.log_inferencia(
                                    empleado=f"{registro['CODIGO']} - {registro['NOMBRE']}",
                                    fecha_hora=ts,
                                    estado_inferido='Salida',
                                    metodo=metodo,
                                )
                                self.inferencias_realizadas.append({
                                    'codigo': registro['CODIGO'],
                                    'nombre': registro['NOMBRE'],
                                    'fecha_hora': ts,
                                    'estado': 'Salida',
                                    'metodo': metodo,
                                })
                        # Recargar para que el best-fit vea los estados ya asignados
                        df_empleado = df_procesado[df_procesado['CODIGO'] == codigo].copy()

                    # ── Best-fit de turno para los NaN restantes del día ─────
                    # Si se aplicó corrección nocturna, excluir los registros de
                    # madrugada (hora < 8) del cálculo: son salidas del turno
                    # anterior y contaminarían el best-fit del turno actual.
                    if self._tiene_entrada_nocturna_dia_anterior(df_empleado, fecha, horarios):
                        timestamps_dia = [
                            df_empleado.loc[i, 'FECHA_HORA']
                            for i in idx_dia
                            if df_empleado.loc[i, 'FECHA_HORA'].hour >= 8
                        ]
                    else:
                        timestamps_dia = df_empleado.loc[idx_dia, 'FECHA_HORA'].tolist()
                    resultado = self.inferir_por_horario_cargo(timestamps_dia, horarios)

                    for idx in idx_dia:
                        if pd.isna(df_empleado.loc[idx, 'ESTADO']):
                            ts = df_empleado.loc[idx, 'FECHA_HORA']
                            estado_inferido = resultado.get(ts)
                            if estado_inferido:
                                df_procesado.loc[idx, 'ESTADO'] = estado_inferido
                                df_procesado.loc[idx, 'ESTADO_INFERIDO'] = True
                                df_empleado.loc[idx, 'ESTADO'] = estado_inferido
                                registro = df_empleado.loc[idx]
                                logger.log_inferencia(
                                    empleado=f"{registro['CODIGO']} - {registro['NOMBRE']}",
                                    fecha_hora=ts,
                                    estado_inferido=estado_inferido,
                                    metodo='horario_cargo',
                                )
                                self.inferencias_realizadas.append({
                                    'codigo': registro['CODIGO'],
                                    'nombre': registro['NOMBRE'],
                                    'fecha_hora': ts,
                                    'estado': estado_inferido,
                                    'metodo': 'horario_cargo',
                                })

                # Recargar df_empleado para que los métodos de fallback
                # vean los estados ya inferidos por el método 0
                df_empleado = df_procesado[df_procesado['CODIGO'] == codigo].copy()

            # ── Métodos 1-3: Fallback para NaN restantes ─────────────────────
            patron = self.inferir_por_patron_empleado(df_empleado)

            for idx in df_empleado.index:
                if pd.isna(df_empleado.loc[idx, 'ESTADO']):
                    registro = df_empleado.loc[idx]
                    hora = registro['FECHA_HORA'].hour

                    # Método 1: Por hora
                    estado_inferido = self.inferir_por_hora(hora)
                    metodo = 'hora'

                    # Método 2: Por contexto
                    if estado_inferido is None:
                        idx_local = df_empleado.index.get_loc(idx)
                        estado_inferido = self.inferir_por_contexto(df_empleado, idx_local)
                        metodo = 'contexto'

                    # Método 3: Por patrón nocturno
                    if estado_inferido is None and patron['tipo_turno'] == 'nocturno':
                        if 16 <= hora <= 23:
                            estado_inferido = 'Entrada'
                            metodo = 'patron_nocturno'
                        elif 0 <= hora <= 6:
                            estado_inferido = 'Salida'
                            metodo = 'patron_nocturno'

                    # Aplicar inferencia
                    if estado_inferido:
                        df_procesado.loc[idx, 'ESTADO'] = estado_inferido
                        df_procesado.loc[idx, 'ESTADO_INFERIDO'] = True
                        logger.log_inferencia(
                            empleado=f"{registro['CODIGO']} - {registro['NOMBRE']}",
                            fecha_hora=registro['FECHA_HORA'],
                            estado_inferido=estado_inferido,
                            metodo=metodo,
                        )
                        self.inferencias_realizadas.append({
                            'codigo': registro['CODIGO'],
                            'nombre': registro['NOMBRE'],
                            'fecha_hora': registro['FECHA_HORA'],
                            'estado': estado_inferido,
                            'metodo': metodo,
                        })

        # Marcar estados no inferidos como indefinidos
        mask_nan = df_procesado['ESTADO'].isna()
        if mask_nan.any():
            df_procesado.loc[mask_nan, 'ESTADO'] = 'INDEFINIDO'
            df_procesado.loc[mask_nan, 'ESTADO_INFERIDO'] = False

        # Llenar columna ESTADO_INFERIDO con False para registros originales
        df_procesado['ESTADO_INFERIDO'] = df_procesado['ESTADO_INFERIDO'].fillna(False)

        logger.info(config.MENSAJES['inferencia_completa'])
        logger.info(f"Estados inferidos: {len(self.inferencias_realizadas)}")

        return df_procesado

    def obtener_resumen(self):
        """
        Obtiene resumen de las inferencias

        Returns:
            Dict con estadísticas
        """
        return {
            'total_inferencias': len(self.inferencias_realizadas),
            'inferencias': self.inferencias_realizadas
        }
