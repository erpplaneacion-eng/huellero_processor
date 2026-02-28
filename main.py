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


def cargar_horarios_por_codigo_excel():
    """
    Lee el Excel maestro y retorna dict {codigo: [(entrada_min, salida_min), ...]}
    para usarlo en la inferencia de estados por horario de cargo.
    """
    import pandas as pd

    ruta = os.path.join(config.DIR_MAESTRO, config.ARCHIVO_MAESTRO)
    if not os.path.exists(ruta):
        return {}

    try:
        xl = pd.ExcelFile(ruta)
        if 'empleados_ejemplo' not in xl.sheet_names or 'cargos_horarios' not in xl.sheet_names or 'horarios' not in xl.sheet_names:
            return {}

        df_emp = pd.read_excel(xl, sheet_name='empleados_ejemplo')
        df_ch  = pd.read_excel(xl, sheet_name='cargos_horarios')
        df_h   = pd.read_excel(xl, sheet_name='horarios')

        # Construir lookup horario_id → (entrada_min, salida_min)
        horario_lookup = {}
        for _, fila in df_h.iterrows():
            def _parse(t):
                partes = str(t).split(':')
                return int(partes[0]) * 60 + int(partes[1])
            horario_lookup[int(fila['id_horario'])] = (
                _parse(fila['hora_inicio']),
                _parse(fila['hora_fin']),
            )

        # Construir lookup cargo → lista de turnos
        cargo_turnos = {}
        for _, fila in df_ch.iterrows():
            cargo_id   = str(fila['id_cargo']).strip()
            horario_id = int(fila['id_horario'])
            if horario_id in horario_lookup:
                cargo_turnos.setdefault(cargo_id, []).append(horario_lookup[horario_id])

        # Mapear codigo empleado → turnos de su cargo
        horarios_por_codigo = {}
        for _, fila in df_emp.iterrows():
            try:
                codigo   = int(fila['CODIGO'])
                cargo_id = str(fila['CARGO']).strip()
                if cargo_id in cargo_turnos:
                    horarios_por_codigo[codigo] = cargo_turnos[cargo_id]
            except (ValueError, TypeError):
                continue

        return horarios_por_codigo

    except Exception as e:
        print(f"⚠️  No se pudieron cargar horarios del maestro: {e}")
        return {}


def cargar_maestro_desde_excel():
    """
    Lee el archivo Excel maestro y retorna DataFrames para el calculator
    y el excel_generator.

    Returns:
        (df_empleados, df_cargos, df_conceptos) — cualquiera puede ser None
        si la hoja no existe o el archivo no se encuentra.
    """
    import pandas as pd

    ruta_maestro = os.path.join(config.DIR_MAESTRO, config.ARCHIVO_MAESTRO)
    if not os.path.exists(ruta_maestro):
        return None, None, None

    xl = pd.ExcelFile(ruta_maestro)

    df_empleados = pd.read_excel(xl, sheet_name='empleados_ejemplo') if 'empleados_ejemplo' in xl.sheet_names else None
    df_cargos = pd.read_excel(xl, sheet_name='horas_cargos') if 'horas_cargos' in xl.sheet_names else None
    df_conceptos = pd.read_excel(xl, sheet_name='conceptos') if 'conceptos' in xl.sheet_names else None

    return df_empleados, df_cargos, df_conceptos


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
        horarios_por_codigo = cargar_horarios_por_codigo_excel() if usar_maestro else {}
        df_con_estados = inference.inferir_estados(df_limpio, horarios_por_codigo)
        
        # ===== FASE 3: CONSTRUCCIÓN DE TURNOS =====
        builder = ShiftBuilder()
        df_turnos = builder.construir_turnos(df_con_estados)
        
        # ===== FASE 4: CÁLCULO DE MÉTRICAS =====
        calculator = Calculator()
        df_resultado = calculator.calcular_metricas(df_turnos, df_con_estados)
        
        # Agregar datos de maestro desde Excel
        df_conceptos = None
        if usar_maestro:
            df_empleados, df_cargos, df_conceptos = cargar_maestro_desde_excel()
            if df_empleados is not None:
                df_resultado = calculator.agregar_datos_maestro(df_resultado, df_empleados, df_cargos)
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
        ruta_salida = generator.generar_excel(df_resultado, stats, df_conceptos=df_conceptos)
        
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
            ruta_maestro_existe = os.path.exists(os.path.join(config.DIR_MAESTRO, config.ARCHIVO_MAESTRO))
            if ruta_maestro_existe:
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
