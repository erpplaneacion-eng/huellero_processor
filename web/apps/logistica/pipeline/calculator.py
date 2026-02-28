"""
Módulo de Cálculos
Calcula horas, conteos y genera observaciones
"""

import pandas as pd
from datetime import datetime, timedelta, time
from . import config
from .logger import logger


class Calculator:
    """Calcula métricas y genera observaciones"""

    def __init__(self):
        """Inicializa el calculador"""
        pass

    def contar_marcaciones_am_pm(self, df_empleado_dia):
        """
        Cuenta marcaciones AM y PM para un empleado en un día

        Args:
            df_empleado_dia: DataFrame con marcaciones del empleado en el día

        Returns:
            Tupla (marcaciones_am, marcaciones_pm)
        """
        marcaciones_am = 0
        marcaciones_pm = 0

        for _, row in df_empleado_dia.iterrows():
            hora = row['FECHA_HORA'].hour

            if config.HORA_INICIO_AM <= hora < config.HORA_FIN_AM:
                marcaciones_am += 1
            elif config.HORA_INICIO_PM <= hora < config.HORA_FIN_PM:
                marcaciones_pm += 1

        return marcaciones_am, marcaciones_pm

    def generar_observaciones(self, turno, df_empleado_dia=None):
        """
        Genera observaciones para un turno

        Args:
            turno: Dict con información del turno
            df_empleado_dia: DataFrame con marcaciones del día (opcional)

        Returns:
            String con observaciones
        """
        observaciones = []

        # Turno incompleto
        if not turno['completo']:
            if pd.isna(turno['entrada']):
                observaciones.append(config.OBSERVACIONES['ENTRADA_NR'])
            elif pd.isna(turno['salida']):
                observaciones.append(config.OBSERVACIONES['SALIDA_NR'])

        # Turno nocturno
        if turno['es_nocturno'] and turno['completo']:
            # Priorizar observación de salida estándar si aplica
            if turno.get('salida_estandar_nocturna', False):
                observaciones.append(config.OBSERVACIONES['SALIDA_ESTANDAR_NOCTURNA'])
            else:
                observaciones.append(config.OBSERVACIONES['TURNO_NOCTURNO'])

        # Estados inferidos
        if turno.get('entrada_inferida', False):
            observaciones.append(config.OBSERVACIONES['ESTADO_INFERIDO'] + " (Entrada)")
        if turno.get('salida_inferida', False):
            observaciones.append(config.OBSERVACIONES['ESTADO_INFERIDO'] + " (Salida)")

        # Salida corregida (segunda Entrada tratada como Salida)
        if turno.get('salida_corregida', False):
            observaciones.append(config.OBSERVACIONES['SALIDA_CORREGIDA'])

        # Regla especial vigilantes: castigo por marcación AM+PM mismo día
        if turno.get('castigo_marcacion_diurna', False):
            observaciones.append(config.OBSERVACIONES['CASTIGO_MARCACION_INCORRECTA_DIURNO'])

        # Turno nocturno prospectivo (entrada PM + salida AM día siguiente)
        if turno.get('nocturno_prospectivo', False):
            observaciones.append(config.OBSERVACIONES['NOCTURNO_PROSPECTIVO'])

        # Validación de horas
        if turno['horas'] is not None:
            if turno['horas'] > config.HORAS_MAXIMAS_TURNO:
                observaciones.append(config.OBSERVACIONES['TURNO_LARGO'])
            elif turno['horas'] > config.HORAS_LIMITE_JORNADA:
                observaciones.append(config.OBSERVACIONES['EXCEDE_JORNADA'])
            elif turno['horas'] < config.HORAS_MINIMAS_TURNO:
                observaciones.append(config.OBSERVACIONES['TURNO_CORTO'])

        # Duplicados (si hay información del día)
        if df_empleado_dia is not None and len(df_empleado_dia) > 2:
            # Buscar duplicados
            df_dia = df_empleado_dia.copy()
            df_dia['diff_seconds'] = df_dia['FECHA_HORA'].diff().dt.total_seconds()
            duplicados = df_dia[df_dia['diff_seconds'] <= config.UMBRAL_DUPLICADOS]

            if len(duplicados) > 0:
                observaciones.append(f"{config.OBSERVACIONES['DUPLICADOS_ELIM']} ({len(duplicados)})")

        # Datos del empleado
        if str(turno['codigo']) in str(turno['nombre']):
            observaciones.append(config.OBSERVACIONES['DATOS_CORRUPTOS'])

        # Día de la semana
        if turno['fecha']:
            dia_semana = turno['fecha'].weekday()
            if dia_semana == 6:  # Domingo
                observaciones.append(config.OBSERVACIONES['TRABAJO_DOMINICAL'])

        # Si no hay observaciones
        if not observaciones:
            return config.OBSERVACIONES['OK']

        return ' | '.join(observaciones)

    def calcular_metricas(self, df_turnos, df_marcaciones):
        """
        Calcula métricas finales para todos los turnos

        Args:
            df_turnos: DataFrame con turnos
            df_marcaciones: DataFrame con marcaciones originales

        Returns:
            DataFrame con métricas calculadas
        """
        logger.log_fase("CÁLCULO DE MÉTRICAS")

        resultados = []

        for idx, turno in df_turnos.iterrows():
            # Obtener marcaciones del empleado en la fecha
            df_emp_dia = df_marcaciones[
                (df_marcaciones['CODIGO'] == turno['codigo']) &
                (df_marcaciones['FECHA_HORA'].dt.date == turno['fecha'])
            ].copy()

            # Contar marcaciones AM/PM
            marc_am, marc_pm = self.contar_marcaciones_am_pm(df_emp_dia)

            # Generar observaciones
            observaciones = self.generar_observaciones(turno, df_emp_dia)

            # Formatear horas
            entrada_str = turno['entrada'].strftime(config.FORMATO_HORA_OUTPUT) if pd.notna(turno['entrada']) else ''
            salida_str = turno['salida'].strftime(config.FORMATO_HORA_OUTPUT) if pd.notna(turno['salida']) else ''

            # Si es turno nocturno, indicar que la salida es del día siguiente
            if turno['es_nocturno'] and pd.notna(turno['salida']) and pd.notna(turno['entrada']):
                if turno['salida'].date() > turno['entrada'].date():
                    salida_str += '*'

            # Formatear fecha
            fecha_str = turno['fecha'].strftime(config.FORMATO_FECHA_OUTPUT)
            dia_semana = config.DIAS_SEMANA[turno['fecha'].weekday()]

            # Verificar si cruza medianoche (cualquier turno que termina al día siguiente).
            # Esto permite partir correctamente casos como 16:31 -> 04:31 en dos filas.
            cruza_medianoche = False
            if turno['completo'] and pd.notna(turno['salida']) and pd.notna(turno['entrada']):
                if turno['salida'].date() > turno['entrada'].date():
                    cruza_medianoche = True

            if cruza_medianoche:
                # ===== DIVIDIR EN DOS REGISTROS =====

                # --- PARTE 1: Entrada -> 00:00 ---
                fin_dia_p1 = datetime.combine(turno['entrada'].date() + timedelta(days=1), time.min)
                horas_p1 = (fin_dia_p1 - turno['entrada']).total_seconds() / 3600

                res_p1 = {
                    'CODIGO COLABORADOR': int(turno['codigo']),
                    'NOMBRE COMPLETO DEL COLABORADOR': turno['nombre'],
                    'DOCUMENTO DEL COLABORADOR': '',
                    'CARGO': '',
                    'FECHA': fecha_str,
                    'DIA': dia_semana,
                    '# MARCACIONES AM': marc_am,
                    '# MARCACIONES PM': marc_pm,
                    'HORA DE INGRESO': entrada_str,
                    'HORA DE SALIDA': '00:00',
                    'TOTAL HORAS LABORADAS': round(horas_p1, 2),
                    'LÍMITE HORAS DÍA': '',
                    'OBSERVACION': observaciones,
                    'OBSERVACIONES_1': ''
                }
                resultados.append(res_p1)

                # --- PARTE 2: 00:00 -> Salida ---
                # Usar fecha del día siguiente
                fecha_p2 = turno['entrada'].date() + timedelta(days=1)
                fecha_str_p2 = fecha_p2.strftime(config.FORMATO_FECHA_OUTPUT)
                dia_semana_p2 = config.DIAS_SEMANA[fecha_p2.weekday()]

                horas_p2 = (turno['salida'] - fin_dia_p1).total_seconds() / 3600

                res_p2 = {
                    'CODIGO COLABORADOR': int(turno['codigo']),
                    'NOMBRE COMPLETO DEL COLABORADOR': turno['nombre'],
                    'DOCUMENTO DEL COLABORADOR': '',
                    'CARGO': '',
                    'FECHA': fecha_str_p2,
                    'DIA': dia_semana_p2,
                    '# MARCACIONES AM': 0,  # No duplicar conteos
                    '# MARCACIONES PM': 0,
                    'HORA DE INGRESO': '00:00',
                    'HORA DE SALIDA': salida_str.replace('*', ''),
                    'TOTAL HORAS LABORADAS': round(horas_p2, 2),
                    'LÍMITE HORAS DÍA': '',
                    'OBSERVACION': observaciones,
                    'OBSERVACIONES_1': ''
                }
                resultados.append(res_p2)

            else:
                # ===== REGISTRO ÚNICO (ESTÁNDAR) =====
                resultado = {
                    'CODIGO COLABORADOR': int(turno['codigo']),
                    'NOMBRE COMPLETO DEL COLABORADOR': turno['nombre'],
                    'DOCUMENTO DEL COLABORADOR': '',  # Se llenará con maestro si existe
                    'CARGO': '',
                    'FECHA': fecha_str,
                    'DIA': dia_semana,
                    '# MARCACIONES AM': marc_am,
                    '# MARCACIONES PM': marc_pm,
                    'HORA DE INGRESO': entrada_str,
                    'HORA DE SALIDA': salida_str,
                    'TOTAL HORAS LABORADAS': turno['horas'] if turno['horas'] else '',
                    'LÍMITE HORAS DÍA': '',
                    'OBSERVACION': observaciones,
                    'OBSERVACIONES_1': ''
                }

                resultados.append(resultado)

        df_resultado = pd.DataFrame(resultados)

        # Rellenar días faltantes
        df_resultado = self.rellenar_dias_faltantes(df_resultado)

        # Ordenar por código y fecha
        df_resultado = df_resultado.sort_values(
            ['CODIGO COLABORADOR', 'FECHA']
        ).reset_index(drop=True)

        logger.info(config.MENSAJES['calculo_completo'])
        logger.info(f"Total registros calculados: {len(df_resultado)}")

        return df_resultado

    def rellenar_dias_faltantes(self, df_resultado):
        """
        Rellena los días faltantes entre registros de un mismo empleado

        Args:
            df_resultado: DataFrame con resultados actuales

        Returns:
            DataFrame con días rellenados
        """
        if df_resultado.empty:
            return df_resultado

        logger.info("Rellenando días faltantes...")
        nuevos_registros = []

        # Convertir columna FECHA a datetime para cálculos
        df_calc = df_resultado.copy()
        df_calc['FECHA_DT'] = pd.to_datetime(df_calc['FECHA'], format=config.FORMATO_FECHA_OUTPUT)

        # Iterar por empleado
        for codigo in df_calc['CODIGO COLABORADOR'].unique():
            df_emp = df_calc[df_calc['CODIGO COLABORADOR'] == codigo].sort_values('FECHA_DT')

            if len(df_emp) < 2:
                continue

            # Iterar pares de filas consecutivas
            for i in range(len(df_emp) - 1):
                fecha_actual = df_emp.iloc[i]['FECHA_DT']
                fecha_siguiente = df_emp.iloc[i+1]['FECHA_DT']

                # Calcular diferencia en días
                dias_diferencia = (fecha_siguiente - fecha_actual).days

                # Si hay hueco (diferencia > 1 día)
                if dias_diferencia > 1:
                    nombre_colaborador = df_emp.iloc[i]['NOMBRE COMPLETO DEL COLABORADOR']
                    doc_colaborador = df_emp.iloc[i]['DOCUMENTO DEL COLABORADOR']

                    # Generar registros intermedios
                    for d in range(1, dias_diferencia):
                        fecha_relleno = fecha_actual + timedelta(days=d)
                        fecha_relleno_str = fecha_relleno.strftime(config.FORMATO_FECHA_OUTPUT)
                        dia_semana_relleno = config.DIAS_SEMANA[fecha_relleno.weekday()]

                        nuevo_reg = {
                            'CODIGO COLABORADOR': int(codigo),
                            'NOMBRE COMPLETO DEL COLABORADOR': nombre_colaborador,
                            'DOCUMENTO DEL COLABORADOR': doc_colaborador,
                            'CARGO': '',
                            'FECHA': fecha_relleno_str,
                            'DIA': dia_semana_relleno,
                            '# MARCACIONES AM': '',
                            '# MARCACIONES PM': '',
                            'HORA DE INGRESO': '',
                            'HORA DE SALIDA': '',
                            'TOTAL HORAS LABORADAS': '',
                            'LÍMITE HORAS DÍA': '',
                            'OBSERVACION': config.OBSERVACIONES['SIN_REGISTROS'],
                            'OBSERVACIONES_1': ''
                        }
                        nuevos_registros.append(nuevo_reg)

        if nuevos_registros:
            df_nuevos = pd.DataFrame(nuevos_registros)
            df_final = pd.concat([df_resultado, df_nuevos], ignore_index=True)
            logger.info(f"✅ Se generaron {len(nuevos_registros)} registros de relleno")
            return df_final

        return df_resultado

    def agregar_datos_maestro(self, df_resultado, df_maestro, df_cargos=None):
        """
        Agrega datos del maestro de empleados al resultado, incluyendo cargo
        y límite de horas por día.

        Args:
            df_resultado: DataFrame con resultados
            df_maestro: DataFrame con empleados (columnas: CODIGO, NOMBRE, DOCUMENTO, CARGO)
            df_cargos: DataFrame con cargos (columnas: id_cargo, cargo, horas_dia,
                       horas_semana, numero_colaboradores). Opcional.

        Returns:
            DataFrame con datos de maestro y validación de horas
        """
        try:
            logger.info("Cargando datos de maestro desde base de datos")

            if df_cargos is None:
                df_cargos = pd.DataFrame(columns=['id_cargo', 'cargo', 'horas_dia', 'horas_semana', 'numero_colaboradores'])

            # Renombrar columnas si es necesario para df_maestro
            columnas_map = {}
            for col in df_maestro.columns:
                col_upper = col.upper()
                if 'CODIGO' in col_upper or 'ID' in col_upper:
                    columnas_map[col] = 'CODIGO'
                elif 'DOCUMENTO' in col_upper or 'CEDULA' in col_upper:
                    columnas_map[col] = 'DOCUMENTO'
                elif 'NOMBRE' in col_upper:
                    columnas_map[col] = 'NOMBRE_MAESTRO'
                elif 'CARGO' in col_upper:
                    columnas_map[col] = 'CARGO_ID'

            df_maestro = df_maestro.rename(columns=columnas_map)

            # Asegurar que CODIGO sea numérico
            df_maestro['CODIGO'] = pd.to_numeric(df_maestro['CODIGO'], errors='coerce')

            # Preparar cruce con cargos
            if not df_cargos.empty and 'CARGO_ID' in df_maestro.columns:
                # Renombrar para que coincida para el merge
                df_cargos = df_cargos.rename(columns={'id_cargo': 'CARGO_ID'})

                # Hacer merge de maestro con cargos para obtener el nombre del cargo y horas límite
                df_maestro = df_maestro.merge(
                    df_cargos[['CARGO_ID', 'cargo', 'horas_dia', 'horas_semana', 'numero_colaboradores']],
                    on='CARGO_ID',
                    how='left'
                )
                # Renombrar a columnas finales deseadas
                df_maestro = df_maestro.rename(columns={
                    'cargo': 'NOMBRE_CARGO',
                    'horas_dia': 'LIMITE_HORAS_DIA',
                    'horas_semana': 'LIMITE_HORAS_SEMANA',
                    'numero_colaboradores': 'COLABORADORES_ESPERADOS'
                })
            else:
                df_maestro['NOMBRE_CARGO'] = ''
                df_maestro['LIMITE_HORAS_DIA'] = config.HORAS_LIMITE_JORNADA  # Usar configuración global por defecto
                df_maestro['LIMITE_HORAS_SEMANA'] = config.HORAS_LIMITE_JORNADA * 5  # Valor por defecto seguro
                df_maestro['COLABORADORES_ESPERADOS'] = 1  # Valor por defecto

            # Seleccionar columnas relevantes
            columnas_maestro = ['CODIGO', 'NOMBRE_CARGO', 'LIMITE_HORAS_DIA', 'LIMITE_HORAS_SEMANA', 'COLABORADORES_ESPERADOS']
            if 'DOCUMENTO' in df_maestro.columns:
                columnas_maestro.append('DOCUMENTO')

            df_maestro = df_maestro[columnas_maestro].drop_duplicates('CODIGO')

            # Hacer merge con df_resultado
            df_resultado = df_resultado.merge(
                df_maestro,
                left_on='CODIGO COLABORADOR',
                right_on='CODIGO',
                how='left'
            )

            # Actualizar columnas en el resultado

            # Actualizar columna de documento (convertir a entero para evitar notación científica)
            if 'DOCUMENTO' in df_resultado.columns:
                df_resultado['DOCUMENTO DEL COLABORADOR'] = df_resultado['DOCUMENTO'].apply(
                    lambda x: str(int(x)) if pd.notna(x) and x != '' else ''
                )
                df_resultado = df_resultado.drop('DOCUMENTO', axis=1)

            # Actualizar Cargo
            if 'NOMBRE_CARGO' in df_resultado.columns:
                df_resultado['CARGO'] = df_resultado['NOMBRE_CARGO'].fillna('')
                df_resultado = df_resultado.drop('NOMBRE_CARGO', axis=1)

            # Actualizar Límite Horas
            if 'LIMITE_HORAS_DIA' in df_resultado.columns:
                df_resultado['LÍMITE HORAS DÍA'] = df_resultado['LIMITE_HORAS_DIA'].fillna('')

                # Validación de horas excedidas por cargo
                def validar_exceso(row):
                    observacion = str(row['OBSERVACION']) if pd.notna(row['OBSERVACION']) else ''

                    # Evitar duplicar la alerta
                    if 'EXCEDE LÍMITE DE HORAS DEL CARGO' in observacion:
                        return observacion

                    # Verificar que haya valores numéricos válidos
                    if pd.notna(row['TOTAL HORAS LABORADAS']) and row['TOTAL HORAS LABORADAS'] != '' and pd.notna(row['LIMITE_HORAS_DIA']) and row['LIMITE_HORAS_DIA'] != '':
                        try:
                            horas_laboradas = float(row['TOTAL HORAS LABORADAS'])
                            limite_cargo = float(row['LIMITE_HORAS_DIA'])

                            if horas_laboradas > limite_cargo:
                                alerta = f"ALERTA: EXCEDE LÍMITE DE HORAS DEL CARGO ({limite_cargo} horas)"
                                if observacion and observacion != config.OBSERVACIONES['OK'] and observacion != config.OBSERVACIONES['SIN_REGISTROS']:
                                    return f"{observacion} | {alerta}"
                                else:
                                    return alerta
                        except ValueError:
                            pass

                    return observacion

                df_resultado['OBSERVACION'] = df_resultado.apply(validar_exceso, axis=1)

                # Remover la alerta genérica de config si la tenemos para este cargo
                df_resultado['OBSERVACION'] = df_resultado['OBSERVACION'].str.replace(f" | {config.OBSERVACIONES['EXCEDE_JORNADA']}", "", regex=False)
                df_resultado['OBSERVACION'] = df_resultado['OBSERVACION'].str.replace(config.OBSERVACIONES['EXCEDE_JORNADA'], "", regex=False)

                # Limpiar "|" sueltos y espacios que puedan quedar
                df_resultado['OBSERVACION'] = df_resultado['OBSERVACION'].str.strip(' |')

                # Si quedó vacío por borrar la alerta genérica, poner OK
                df_resultado['OBSERVACION'] = df_resultado['OBSERVACION'].replace('', config.OBSERVACIONES['OK'])

                df_resultado = df_resultado.drop('LIMITE_HORAS_DIA', axis=1)

            # Eliminar columna CODIGO duplicada
            if 'CODIGO' in df_resultado.columns:
                df_resultado = df_resultado.drop('CODIGO', axis=1)

            logger.info(f"✅ Datos de maestro agregados (incluyendo cargos y límites de horas)")

        except Exception as e:
            logger.warning(f"Error al cargar maestro: {str(e)}")

        return df_resultado
