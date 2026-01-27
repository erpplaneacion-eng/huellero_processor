"""
Módulo Generador de Excel
Crea archivo Excel con formato profesional
"""

import pandas as pd
import os
from datetime import datetime
import config
from src.logger import logger

try:
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl no disponible - formato limitado")


class ExcelGenerator:
    """Genera archivo Excel con formato"""
    
    def __init__(self):
        """Inicializa el generador"""
        self.archivo_salida = None
    
    def generar_nombre_archivo(self):
        """
        Genera nombre para el archivo de salida
        
        Returns:
            String con nombre de archivo
        """
        timestamp = datetime.now().strftime(config.FORMATO_ARCHIVO)
        nombre = f"{config.PREFIJO_OUTPUT}_{timestamp}.xlsx"
        return os.path.join(config.DIR_OUTPUT, nombre)
    
    def crear_hoja_resumen(self, writer, stats):
        """
        Crea hoja de resumen con estadísticas
        
        Args:
            writer: ExcelWriter
            stats: Dict con estadísticas
        """
        if not config.GENERAR_HOJA_RESUMEN:
            return
        
        resumen_data = {
            'Métrica': [
                'Fecha de Procesamiento',
                'Total Empleados',
                'Total Registros',
                'Turnos Completos',
                'Turnos Incompletos',
                'Duplicados Eliminados',
                'Estados Inferidos',
                'Errores',
                'Advertencias'
            ],
            'Valor': [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                stats.get('empleados_unicos', 0),
                stats.get('total_registros', 0),
                stats.get('turnos_completos', 0),
                stats.get('turnos_incompletos', 0),
                stats.get('duplicados_eliminados', 0),
                stats.get('estados_inferidos', 0),
                stats.get('errores', 0),
                stats.get('advertencias', 0)
            ]
        }
        
        df_resumen = pd.DataFrame(resumen_data)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        
        logger.info("Hoja de resumen creada")
    
    def aplicar_formato(self, ruta_archivo, nombre_hoja='Reporte'):
        """
        Aplica formato al archivo Excel
        
        Args:
            ruta_archivo: Ruta al archivo
            nombre_hoja: Nombre de la hoja a formatear
        """
        if not OPENPYXL_AVAILABLE:
            logger.warning("No se puede aplicar formato - openpyxl no disponible")
            return
        
        try:
            wb = load_workbook(ruta_archivo)
            ws = wb[nombre_hoja]
            
            # Colores
            color_encabezado = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            color_ok = PatternFill(start_color=config.COLORES['VERDE'][1:], end_color=config.COLORES['VERDE'][1:], fill_type='solid')
            color_advertencia = PatternFill(start_color=config.COLORES['AMARILLO'][1:], end_color=config.COLORES['AMARILLO'][1:], fill_type='solid')
            color_error = PatternFill(start_color=config.COLORES['NARANJA'][1:], end_color=config.COLORES['NARANJA'][1:], fill_type='solid')
            color_nocturno = PatternFill(start_color=config.COLORES['AZUL'][1:], end_color=config.COLORES['AZUL'][1:], fill_type='solid')
            
            # Fuentes
            font_encabezado = Font(bold=True, color='FFFFFF', size=11)
            font_normal = Font(size=10)
            
            # Alineación
            align_center = Alignment(horizontal='center', vertical='center')
            align_left = Alignment(horizontal='left', vertical='center')
            
            # Bordes
            border_delgado = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Aplicar formato a encabezados
            for col_num, column_title in enumerate(config.COLUMNAS_OUTPUT, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = color_encabezado
                cell.font = font_encabezado
                cell.alignment = align_center
                cell.border = border_delgado
                
                # Ajustar ancho de columna
                col_letter = get_column_letter(col_num)
                ancho = config.ANCHOS_COLUMNAS.get(column_title, 15)
                ws.column_dimensions[col_letter].width = ancho
            
            # Aplicar formato a datos
            for row_num in range(2, ws.max_row + 1):
                # Obtener observación
                obs_cell = ws.cell(row=row_num, column=len(config.COLUMNAS_OUTPUT))
                observacion = obs_cell.value or ''
                
                # Determinar color de fila
                fill_color = None
                if 'OK' in observacion or observacion == config.OBSERVACIONES['OK']:
                    fill_color = color_ok
                elif 'TURNO_NOCTURNO' in observacion:
                    fill_color = color_nocturno
                elif 'ALERTA' in observacion:
                    fill_color = color_error
                elif observacion and observacion != config.OBSERVACIONES['OK']:
                    fill_color = color_advertencia
                
                # Aplicar formato a todas las celdas de la fila
                for col_num in range(1, len(config.COLUMNAS_OUTPUT) + 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.font = font_normal
                    cell.border = border_delgado
                    
                    # Alineación según columna
                    if col_num in [1, 6, 7, 10]:  # Código, marcaciones, horas
                        cell.alignment = align_center
                    else:
                        cell.alignment = align_left
                    
                    # Color de fondo
                    if fill_color:
                        cell.fill = fill_color
            
            # Congelar primera fila
            ws.freeze_panes = 'A2'
            
            # Guardar
            wb.save(ruta_archivo)
            logger.info("Formato aplicado exitosamente")
            
        except Exception as e:
            logger.error(f"Error al aplicar formato: {str(e)}")
    
    def generar_excel(self, df_resultado, stats=None):
        """
        Genera archivo Excel con los resultados
        
        Args:
            df_resultado: DataFrame con resultados finales
            stats: Dict con estadísticas (opcional)
            
        Returns:
            Ruta al archivo generado
        """
        logger.log_fase("GENERACIÓN DE ARCHIVO EXCEL")
        
        # Crear directorio de salida si no existe
        os.makedirs(config.DIR_OUTPUT, exist_ok=True)
        
        # Generar nombre de archivo
        ruta_salida = self.generar_nombre_archivo()
        
        # Crear archivo Excel
        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
            # Hoja principal
            df_resultado.to_excel(writer, sheet_name='Reporte', index=False)
            
            # Hoja de resumen
            if stats:
                self.crear_hoja_resumen(writer, stats)
        
        # Aplicar formato
        self.aplicar_formato(ruta_salida, 'Reporte')
        
        self.archivo_salida = ruta_salida
        
        logger.info(config.MENSAJES['excel_generado'])
        logger.info(f"Archivo guardado en: {ruta_salida}")
        
        return ruta_salida
    
    def generar_casos_especiales(self, df_resultado):
        """
        Genera archivo con casos que requieren revisión manual
        
        Args:
            df_resultado: DataFrame con resultados
            
        Returns:
            Ruta al archivo o None
        """
        if not config.GENERAR_CASOS_ESPECIALES:
            return None
        
        # Filtrar casos especiales
        casos = df_resultado[
            (df_resultado['OBSERVACION'].str.contains('ALERTA', na=False)) |
            (df_resultado['OBSERVACION'].str.contains('REQUIERE', na=False)) |
            (df_resultado['OBSERVACION'].str.contains('INDEFINIDO', na=False)) |
            (df_resultado['OBSERVACION'].str.contains('DATOS_CORRUPTOS', na=False))
        ].copy()
        
        if len(casos) == 0:
            logger.info("No hay casos especiales para revisar")
            return None
        
        # Generar archivo
        timestamp = datetime.now().strftime(config.FORMATO_ARCHIVO)
        nombre = f"CASOS_REVISION_{timestamp}.xlsx"
        ruta = os.path.join(config.DIR_OUTPUT, nombre)
        
        casos.to_excel(ruta, index=False)
        
        logger.info(f"Archivo de casos especiales generado: {ruta}")
        logger.info(f"Total casos para revisión: {len(casos)}")
        
        return ruta
