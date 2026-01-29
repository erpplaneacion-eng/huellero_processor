"""
Módulo de Cálculos
Calcula horas, conteos y genera observaciones
"""

import pandas as pd
from datetime import datetime, timedelta, time
import config
from src.logger import logger


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
            observaciones.append(config.OBSERVACIONES['TURNO_NOCTURNO'])
        
        # Estados inferidos
        if turno.get('entrada_inferida', False):
            observaciones.append(config.OBSERVACIONES['ESTADO_INFERIDO'] + " (Entrada)")
        if turno.get('salida_inferida', False):
            observaciones.append(config.OBSERVACIONES['ESTADO_INFERIDO'] + " (Salida)")
        
        # Salida corregida (segunda Entrada tratada como Salida)
        if turno.get('salida_corregida', False):
            observaciones.append(config.OBSERVACIONES['SALIDA_CORREGIDA'])

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
            
            # Verificar si cruza medianoche (turno nocturno que termina al día siguiente)
            cruza_medianoche = False
            if turno['es_nocturno'] and turno['completo'] and pd.notna(turno['salida']) and pd.notna(turno['entrada']):
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
                    'FECHA': fecha_str,
                    'DIA': dia_semana,
                    '# MARCACIONES AM': marc_am,
                    '# MARCACIONES PM': marc_pm,
                    'HORA DE INGRESO': entrada_str,
                    'HORA DE SALIDA': '00:00',
                    'TOTAL HORAS LABORADAS': round(horas_p1, 2),
                    'OBSERVACION': observaciones
                }
                resultados.append(res_p1)
                
                # --- PARTE 2: 00:00 -> Salida ---
                # Usar fecha del día siguiente
                fecha_p2 = turno['salida'].date()
                fecha_str_p2 = fecha_p2.strftime(config.FORMATO_FECHA_OUTPUT)
                dia_semana_p2 = config.DIAS_SEMANA[fecha_p2.weekday()]
                
                horas_p2 = (turno['salida'] - fin_dia_p1).total_seconds() / 3600
                
                res_p2 = {
                    'CODIGO COLABORADOR': int(turno['codigo']),
                    'NOMBRE COMPLETO DEL COLABORADOR': turno['nombre'],
                    'DOCUMENTO DEL COLABORADOR': '',
                    'FECHA': fecha_str_p2,
                    'DIA': dia_semana_p2,
                    '# MARCACIONES AM': 0,  # No duplicar conteos
                    '# MARCACIONES PM': 0,
                    'HORA DE INGRESO': '00:00',
                    'HORA DE SALIDA': salida_str.replace('*', ''),
                    'TOTAL HORAS LABORADAS': round(horas_p2, 2),
                    'OBSERVACION': observaciones
                }
                resultados.append(res_p2)
                
            else:
                # ===== REGISTRO ÚNICO (ESTÁNDAR) =====
                resultado = {
                    'CODIGO COLABORADOR': int(turno['codigo']),
                    'NOMBRE COMPLETO DEL COLABORADOR': turno['nombre'],
                    'DOCUMENTO DEL COLABORADOR': '',  # Se llenará con maestro si existe
                    'FECHA': fecha_str,
                    'DIA': dia_semana,
                    '# MARCACIONES AM': marc_am,
                    '# MARCACIONES PM': marc_pm,
                    'HORA DE INGRESO': entrada_str,
                    'HORA DE SALIDA': salida_str,
                    'TOTAL HORAS LABORADAS': turno['horas'] if turno['horas'] else '',
                    'OBSERVACION': observaciones
                }
                
                resultados.append(resultado)
        
        df_resultado = pd.DataFrame(resultados)
        
        # Ordenar por código y fecha
        df_resultado = df_resultado.sort_values(
            ['CODIGO COLABORADOR', 'FECHA']
        ).reset_index(drop=True)
        
        logger.info(config.MENSAJES['calculo_completo'])
        logger.info(f"Total registros calculados: {len(df_resultado)}")
        
        return df_resultado
    
    def agregar_datos_maestro(self, df_resultado, ruta_maestro):
        """
        Agrega datos del archivo maestro de empleados
        
        Args:
            df_resultado: DataFrame con resultados
            ruta_maestro: Ruta al archivo maestro
            
        Returns:
            DataFrame con datos de maestro
        """
        try:
            logger.info(f"Cargando archivo maestro: {ruta_maestro}")
            
            # Leer maestro
            df_maestro = pd.read_excel(ruta_maestro)
            
            # Renombrar columnas si es necesario
            columnas_map = {}
            for col in df_maestro.columns:
                col_upper = col.upper()
                if 'CODIGO' in col_upper or 'ID' in col_upper:
                    columnas_map[col] = 'CODIGO'
                elif 'DOCUMENTO' in col_upper or 'CEDULA' in col_upper:
                    columnas_map[col] = 'DOCUMENTO'
                elif 'NOMBRE' in col_upper:
                    columnas_map[col] = 'NOMBRE_MAESTRO'
            
            df_maestro = df_maestro.rename(columns=columnas_map)
            
            # Asegurar que CODIGO sea numérico
            df_maestro['CODIGO'] = pd.to_numeric(df_maestro['CODIGO'], errors='coerce')
            
            # Seleccionar columnas relevantes
            columnas_maestro = ['CODIGO']
            if 'DOCUMENTO' in df_maestro.columns:
                columnas_maestro.append('DOCUMENTO')
            
            df_maestro = df_maestro[columnas_maestro].drop_duplicates('CODIGO')
            
            # Hacer merge
            df_resultado = df_resultado.merge(
                df_maestro,
                left_on='CODIGO COLABORADOR',
                right_on='CODIGO',
                how='left'
            )
            
            # Actualizar columna de documento (convertir a entero para evitar notación científica)
            if 'DOCUMENTO' in df_resultado.columns:
                df_resultado['DOCUMENTO DEL COLABORADOR'] = df_resultado['DOCUMENTO'].apply(
                    lambda x: str(int(x)) if pd.notna(x) and x != '' else ''
                )
                df_resultado = df_resultado.drop('DOCUMENTO', axis=1)
            
            # Eliminar columna CODIGO duplicada
            if 'CODIGO' in df_resultado.columns:
                df_resultado = df_resultado.drop('CODIGO', axis=1)
            
            logger.info(f"✅ Datos de maestro agregados")
            
        except FileNotFoundError:
            logger.warning(f"Archivo maestro no encontrado: {ruta_maestro}")
        except Exception as e:
            logger.warning(f"Error al cargar maestro: {str(e)}")
        
        return df_resultado
