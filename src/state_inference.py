"""
Módulo de Inferencia de Estados
Deduce si una marcación sin estado es Entrada o Salida
"""

import pandas as pd
import config
from src.logger import logger


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
    
    def inferir_estados(self, df):
        """
        Infiere todos los estados faltantes en el DataFrame
        
        Args:
            df: DataFrame con los datos
            
        Returns:
            DataFrame con estados inferidos
        """
        logger.log_fase("INFERENCIA DE ESTADOS")
        
        if not config.PERMITIR_INFERENCIA:
            logger.info("Inferencia de estados desactivada")
            return df
        
        df_procesado = df.copy()
        
        # Contar estados faltantes
        estados_nan = df_procesado['ESTADO'].isna().sum()
        logger.info(f"Estados faltantes detectados: {estados_nan}")
        
        if estados_nan == 0:
            logger.info("No hay estados para inferir")
            return df_procesado
        
        # Procesar por empleado
        for codigo in df_procesado['CODIGO'].unique():
            df_empleado = df_procesado[df_procesado['CODIGO'] == codigo].copy()
            
            # Obtener patrón del empleado
            patron = self.inferir_por_patron_empleado(df_empleado)
            
            # Procesar cada registro sin estado
            for idx in df_empleado.index:
                if pd.isna(df_empleado.loc[idx, 'ESTADO']):
                    registro = df_empleado.loc[idx]
                    hora = registro['FECHA_HORA'].hour
                    
                    # Método 1: Por hora
                    estado_inferido = self.inferir_por_hora(hora)
                    metodo = 'hora'
                    
                    # Método 2: Por contexto si método 1 falla
                    if estado_inferido is None:
                        idx_local = df_empleado.index.get_loc(idx)
                        estado_inferido = self.inferir_por_contexto(df_empleado, idx_local)
                        metodo = 'contexto'
                    
                    # Método 3: Por patrón del empleado
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
                        
                        # Registrar en log
                        logger.log_inferencia(
                            empleado=f"{registro['CODIGO']} - {registro['NOMBRE']}",
                            fecha_hora=registro['FECHA_HORA'],
                            estado_inferido=estado_inferido,
                            metodo=metodo
                        )
                        
                        self.inferencias_realizadas.append({
                            'codigo': registro['CODIGO'],
                            'nombre': registro['NOMBRE'],
                            'fecha_hora': registro['FECHA_HORA'],
                            'estado': estado_inferido,
                            'metodo': metodo
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
