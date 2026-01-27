"""
SISTEMA PROCESADOR DE HUELLERO
Corporación Hacia un Valle Solidario

Archivo Principal - Ejecutar este archivo para procesar huellero
"""

import os
import sys
import argparse
from datetime import datetime
import glob

import config
from src.logger import logger
from src.data_cleaner import DataCleaner
from src.state_inference import StateInference
from src.shift_builder import ShiftBuilder
from src.calculator import Calculator
from src.excel_generator import ExcelGenerator


def obtener_archivo_entrada(ruta_especifica=None):
    """
    Obtiene el archivo de entrada a procesar
    
    Args:
        ruta_especifica: Ruta específica al archivo (opcional)
        
    Returns:
        Ruta al archivo de entrada
    """
    if ruta_especifica and os.path.exists(ruta_especifica):
        return ruta_especifica
    
    # Buscar archivos en directorio de entrada
    patron = os.path.join(config.DIR_INPUT, "*.xls*")
    archivos = glob.glob(patron)
    
    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron archivos en {config.DIR_INPUT}\n"
            f"Coloque el archivo de huellero en ese directorio."
        )
    
    if len(archivos) == 1:
        return archivos[0]
    
    # Si hay múltiples, tomar el más reciente
    archivo_mas_reciente = max(archivos, key=os.path.getmtime)
    logger.info(f"Múltiples archivos encontrados, procesando el más reciente")
    
    return archivo_mas_reciente


def obtener_archivo_maestro():
    """
    Obtiene ruta al archivo maestro de empleados
    
    Returns:
        Ruta al archivo maestro o None
    """
    ruta_maestro = os.path.join(config.DIR_MAESTRO, config.ARCHIVO_MAESTRO)
    
    if os.path.exists(ruta_maestro):
        return ruta_maestro
    
    return None


def procesar_huellero(ruta_archivo, usar_maestro=True):
    """
    Procesa el archivo de huellero completo
    
    Args:
        ruta_archivo: Ruta al archivo de entrada
        usar_maestro: Si debe usar archivo maestro
        
    Returns:
        Ruta al archivo de salida
    """
    logger.log_inicio_proceso(ruta_archivo)
    
    try:
        # ===== FASE 1: LIMPIEZA DE DATOS =====
        cleaner = DataCleaner()
        df_limpio = cleaner.procesar(ruta_archivo)
        
        # ===== FASE 2: INFERENCIA DE ESTADOS =====
        inference = StateInference()
        df_con_estados = inference.inferir_estados(df_limpio)
        
        # ===== FASE 3: CONSTRUCCIÓN DE TURNOS =====
        builder = ShiftBuilder()
        df_turnos = builder.construir_turnos(df_con_estados)
        
        # ===== FASE 4: CÁLCULO DE MÉTRICAS =====
        calculator = Calculator()
        df_resultado = calculator.calcular_metricas(df_turnos, df_con_estados)
        
        # Agregar datos de maestro si está disponible
        if usar_maestro:
            ruta_maestro = obtener_archivo_maestro()
            if ruta_maestro:
                df_resultado = calculator.agregar_datos_maestro(df_resultado, ruta_maestro)
            else:
                logger.warning("Archivo maestro no encontrado - documentos quedarán vacíos")
        
        # ===== FASE 5: GENERACIÓN DE EXCEL =====
        generator = ExcelGenerator()
        
        # Preparar estadísticas
        stats_logger = logger.obtener_estadisticas()
        stats_cleaner = cleaner.obtener_resumen()
        stats_inference = inference.obtener_resumen()
        stats_builder = builder.obtener_resumen()
        
        stats = {
            'empleados_unicos': df_resultado['CODIGO COLABORADOR'].nunique(),
            'total_registros': len(df_resultado),
            'turnos_completos': stats_builder.get('turnos_completos', 0),
            'turnos_incompletos': stats_builder.get('turnos_incompletos', 0),
            'duplicados_eliminados': stats_cleaner.get('duplicados_eliminados', 0),
            'estados_inferidos': stats_inference.get('total_inferencias', 0),
            'errores': stats_logger.get('errores', 0),
            'advertencias': stats_logger.get('advertencias', 0)
        }
        
        # Generar Excel
        ruta_salida = generator.generar_excel(df_resultado, stats)
        
        # Generar casos especiales
        generator.generar_casos_especiales(df_resultado)
        
        # ===== FIN DEL PROCESO =====
        logger.log_fin_proceso(exito=True)
        
        return ruta_salida
        
    except Exception as e:
        logger.error(f"Error durante el procesamiento: {str(e)}")
        logger.log_fin_proceso(exito=False)
        raise


def main():
    """Función principal"""
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description='Procesador de Archivos de Huellero',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                          # Procesar archivo en data/input/
  python main.py --archivo miarchivo.xls  # Procesar archivo específico
  python main.py --sin-maestro            # Procesar sin archivo maestro
  python main.py --interactivo            # Modo interactivo
        """
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        help='Ruta al archivo de huellero a procesar'
    )
    
    parser.add_argument(
        '--sin-maestro',
        action='store_true',
        help='No usar archivo maestro de empleados'
    )
    
    parser.add_argument(
        '--interactivo',
        action='store_true',
        help='Modo interactivo con menús'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*80)
    print("  🕐 SISTEMA PROCESADOR DE HUELLERO")
    print("  Corporación Hacia un Valle Solidario")
    print("="*80 + "\n")
    
    try:
        # Modo interactivo
        if args.interactivo:
            print("📁 Buscando archivos de huellero...")
            patron = os.path.join(config.DIR_INPUT, "*.xls*")
            archivos = glob.glob(patron)
            
            if not archivos:
                print(f"\n❌ No se encontraron archivos en {config.DIR_INPUT}")
                print(f"   Coloque el archivo de huellero en ese directorio.")
                return
            
            print(f"\nArchivos encontrados:")
            for i, archivo in enumerate(archivos, 1):
                nombre = os.path.basename(archivo)
                tamaño = os.path.getsize(archivo) / 1024
                print(f"  {i}. {nombre} ({tamaño:.1f} KB)")
            
            if len(archivos) == 1:
                seleccion = 0
            else:
                try:
                    seleccion = int(input(f"\nSeleccione archivo (1-{len(archivos)}): ")) - 1
                    if seleccion < 0 or seleccion >= len(archivos):
                        print("❌ Selección inválida")
                        return
                except ValueError:
                    print("❌ Entrada inválida")
                    return
            
            archivo = archivos[seleccion]
            
            # Preguntar por maestro
            usar_maestro = True
            ruta_maestro = obtener_archivo_maestro()
            if ruta_maestro:
                respuesta = input("\n¿Usar archivo maestro de empleados? (S/n): ").strip().lower()
                usar_maestro = respuesta != 'n'
            else:
                print("\n⚠️  Archivo maestro no encontrado")
                usar_maestro = False
        
        else:
            # Modo automático
            archivo = obtener_archivo_entrada(args.archivo)
            usar_maestro = not args.sin_maestro
        
        # Procesar
        print(f"\n📂 Procesando: {os.path.basename(archivo)}")
        print(f"⏳ Iniciando procesamiento...\n")
        
        ruta_salida = procesar_huellero(archivo, usar_maestro)
        
        # Éxito
        print("\n" + "="*80)
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
        print("="*80)
        print(f"\n📊 Archivo generado:")
        print(f"   {ruta_salida}")
        print(f"\n📋 Log del procesamiento:")
        log_files = glob.glob(os.path.join(config.DIR_LOGS, "*.log"))
        if log_files:
            ultimo_log = max(log_files, key=os.path.getmtime)
            print(f"   {ultimo_log}")
        print()
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {str(e)}\n")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento:")
        print(f"   {str(e)}\n")
        print("📋 Revise el archivo de log para más detalles.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
