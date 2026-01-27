"""
Módulo de Limpieza de Datos
Elimina duplicados y prepara los datos para procesamiento
"""

import pandas as pd
import config
from src.logger import logger


class DataCleaner:
    """Limpia y prepara los datos del huellero"""
    
    def __init__(self):
        """Inicializa el limpiador de datos"""
        self.df_original = None
        self.df_limpio = None
        self.duplicados_eliminados = []
    
    def cargar_archivo(self, ruta_archivo):
        """
        Carga el archivo Excel del huellero
        
        Args:
            ruta_archivo: Ruta al archivo .xls
            
        Returns:
            DataFrame con los datos cargados
        """
        logger.log_fase("CARGA DE ARCHIVO")
        logger.info(f"Cargando archivo: {ruta_archivo}")
        
        try:
            # Leer archivo Excel
            df = pd.read_excel(ruta_archivo)
            
            # Verificar si "ID" ya es columna del DataFrame
            if 'ID' in df.columns:
                # El encabezado ya fue detectado correctamente
                pass
            else:
                # Identificar fila de encabezado (buscar "ID" en los datos)
                header_row = None
                for idx, row in df.iterrows():
                    if 'ID' in str(row.values):
                        header_row = idx
                        break

                if header_row is None:
                    raise ValueError("No se encontró la fila de encabezado con 'ID'")

                # Releer con el encabezado correcto
                df = pd.read_excel(ruta_archivo, header=header_row + 1)
            
            # Renombrar columnas Unnamed basándose en los valores de la fila de encabezado
            # Las columnas son: [vacío, ID, Nombre, Fecha/Hora, Estado, vacío, vacío, Tipo de Registro]
            nuevos_nombres = {}
            for i, col in enumerate(df.columns):
                if 'Unnamed' in str(col):
                    # Buscar el valor en la primera fila válida
                    valor = df.iloc[0, i] if len(df) > 0 else None
                    if pd.notna(valor) and str(valor).strip():
                        nuevos_nombres[col] = str(valor).strip()
            
            if nuevos_nombres:
                df = df.rename(columns=nuevos_nombres)
            
            # Eliminar primera fila si es el encabezado repetido
            if len(df) > 0 and str(df.iloc[0, 1]).strip() == 'ID':
                df = df.iloc[1:]
            
            # Eliminar filas después del pie de página (buscar "Fecha / Hora:")
            pie_idx = None
            for idx, row in df.iterrows():
                if pd.notna(row.iloc[0]) and 'Fecha / Hora:' in str(row.iloc[0]):
                    pie_idx = idx
                    break
            
            if pie_idx:
                df = df.iloc[:pie_idx]
            
            # Reset index
            df = df.reset_index(drop=True)
            
            self.df_original = df
            logger.info(f"✅ Archivo cargado: {len(df)} registros")
            logger.incrementar_stat('registros_procesados', len(df))
            
            return df
            
        except Exception as e:
            logger.error(f"Error al cargar archivo: {str(e)}")
            raise
    
    def limpiar_estructura(self, df):
        """
        Limpia la estructura del DataFrame
        
        Args:
            df: DataFrame a limpiar
            
        Returns:
            DataFrame limpio
        """
        logger.log_fase("LIMPIEZA DE ESTRUCTURA")
        
        # Renombrar columnas
        columnas_nuevas = {
            'ID': 'CODIGO',
            'Nombre': 'NOMBRE',
            'Nombre ': 'NOMBRE',  # Variante con espacio
            'Fecha / Hora': 'FECHA_HORA',
            'Estado': 'ESTADO',
            'Tipo de Registro': 'TIPO'
        }
        
        # Intentar renombrar
        for col_vieja, col_nueva in columnas_nuevas.items():
            if col_vieja in df.columns:
                df = df.rename(columns={col_vieja: col_nueva})
        
        # Seleccionar solo columnas relevantes
        columnas_necesarias = ['CODIGO', 'NOMBRE', 'FECHA_HORA', 'ESTADO', 'TIPO']
        columnas_disponibles = [col for col in columnas_necesarias if col in df.columns]
        
        if not columnas_disponibles:
            # Si no encuentra las columnas, mostrar las disponibles
            logger.error(f"Columnas disponibles: {df.columns.tolist()}")
            raise ValueError("No se encontraron las columnas necesarias")
        
        df = df[columnas_disponibles].copy()
        
        # Convertir tipos de datos
        df['CODIGO'] = pd.to_numeric(df['CODIGO'], errors='coerce')
        df['FECHA_HORA'] = pd.to_datetime(
            df['FECHA_HORA'], 
            format=config.FORMATO_FECHA_INPUT, 
            errors='coerce'
        )
        
        # Eliminar filas sin datos esenciales
        df = df.dropna(subset=['CODIGO', 'FECHA_HORA'])
        
        # Ordenar por código y fecha
        df = df.sort_values(['CODIGO', 'FECHA_HORA']).reset_index(drop=True)
        
        logger.info(f"✅ Estructura limpiada: {len(df)} registros válidos")
        
        return df
    
    def eliminar_duplicados(self, df):
        """
        Elimina marcaciones duplicadas (mismo empleado, < 2 minutos)
        
        Args:
            df: DataFrame a limpiar
            
        Returns:
            DataFrame sin duplicados
        """
        logger.log_fase("ELIMINACIÓN DE DUPLICADOS")
        
        if not config.ELIMINAR_DUPLICADOS_AUTO:
            logger.info("Eliminación automática de duplicados desactivada")
            return df
        
        df_limpio = df.copy()
        indices_eliminar = []
        
        # Calcular diferencia de tiempo con la marcación anterior
        df_limpio['diff_seconds'] = df_limpio.groupby('CODIGO')['FECHA_HORA'].diff().dt.total_seconds()
        
        for idx, row in df_limpio.iterrows():
            if idx == 0:
                continue
            
            # Verificar si es del mismo empleado
            if row['CODIGO'] == df_limpio.iloc[idx-1]['CODIGO']:
                # Verificar si está dentro del umbral
                if row['diff_seconds'] <= config.UMBRAL_DUPLICADOS:
                    # Verificar si es del mismo tipo
                    estado_actual = row['ESTADO']
                    estado_anterior = df_limpio.iloc[idx-1]['ESTADO']
                    
                    if estado_actual == estado_anterior or pd.isna(estado_actual):
                        # Es duplicado - marcar para eliminar
                        indices_eliminar.append(idx)
                        
                        # Registrar en log
                        logger.log_duplicados(
                            empleado=f"{row['CODIGO']} - {row['NOMBRE']}",
                            fecha_hora=row['FECHA_HORA'],
                            cantidad=1
                        )
        
        # Eliminar duplicados
        df_limpio = df_limpio.drop(indices_eliminar).reset_index(drop=True)
        
        # Eliminar columna auxiliar
        df_limpio = df_limpio.drop('diff_seconds', axis=1)
        
        total_eliminados = len(indices_eliminar)
        logger.info(f"✅ Duplicados eliminados: {total_eliminados}")
        
        self.duplicados_eliminados = indices_eliminar
        self.df_limpio = df_limpio
        
        return df_limpio
    
    def procesar(self, ruta_archivo):
        """
        Procesa completo: carga, limpia estructura y elimina duplicados
        
        Args:
            ruta_archivo: Ruta al archivo de entrada
            
        Returns:
            DataFrame limpio
        """
        df = self.cargar_archivo(ruta_archivo)
        df = self.limpiar_estructura(df)
        df = self.eliminar_duplicados(df)
        
        logger.info(config.MENSAJES['limpieza_completa'])
        logger.info(f"Total registros limpios: {len(df)}")
        
        return df
    
    def obtener_resumen(self):
        """
        Obtiene resumen de la limpieza
        
        Returns:
            Dict con estadísticas
        """
        return {
            'registros_originales': len(self.df_original) if self.df_original is not None else 0,
            'registros_limpios': len(self.df_limpio) if self.df_limpio is not None else 0,
            'duplicados_eliminados': len(self.duplicados_eliminados)
        }
