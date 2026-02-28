"""
Módulo de Logging
Sistema de registro de eventos del procesamiento
"""

import logging
import os
from datetime import datetime
from . import config


class HuelleroLogger:
    """Gestiona el logging del sistema de procesamiento"""

    def __init__(self, nombre_modulo='HuelleroProcessor'):
        """
        Inicializa el logger

        Args:
            nombre_modulo: Nombre del módulo que usa el logger
        """
        self.logger = logging.getLogger(nombre_modulo)
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))

        # Crear directorio de logs si no existe
        os.makedirs(config.DIR_LOGS, exist_ok=True)

        # Crear nombre de archivo de log
        timestamp = datetime.now().strftime(config.FORMATO_ARCHIVO)
        log_file = os.path.join(config.DIR_LOGS, f'procesamiento_{timestamp}.log')

        # Configurar handlers
        self._configurar_handlers(log_file)

        # Estadísticas del procesamiento
        self.stats = {
            'registros_procesados': 0,
            'duplicados_eliminados': 0,
            'estados_inferidos': 0,
            'turnos_completos': 0,
            'turnos_incompletos': 0,
            'errores': 0,
            'advertencias': 0
        }

    def _configurar_handlers(self, log_file):
        """Configura los handlers de archivo y consola"""

        # Limpiar handlers existentes
        self.logger.handlers.clear()

        # Formatter
        formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )

        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, mensaje):
        """Log nivel INFO"""
        self.logger.info(mensaje)

    def debug(self, mensaje):
        """Log nivel DEBUG"""
        self.logger.debug(mensaje)

    def warning(self, mensaje):
        """Log nivel WARNING"""
        self.logger.warning(mensaje)
        self.stats['advertencias'] += 1

    def error(self, mensaje):
        """Log nivel ERROR"""
        self.logger.error(mensaje)
        self.stats['errores'] += 1

    def critical(self, mensaje):
        """Log nivel CRITICAL"""
        self.logger.critical(mensaje)
        self.stats['errores'] += 1

    def incrementar_stat(self, stat_name, cantidad=1):
        """Incrementa una estadística"""
        if stat_name in self.stats:
            self.stats[stat_name] += cantidad

    def obtener_estadisticas(self):
        """Retorna las estadísticas actuales"""
        return self.stats.copy()

    def log_inicio_proceso(self, archivo):
        """Registra el inicio del proceso"""
        self.info("="*80)
        self.info(config.MENSAJES['inicio'])
        self.info(f"Archivo: {archivo}")
        self.info(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info("="*80)

    def log_fin_proceso(self, exito=True):
        """Registra el fin del proceso con estadísticas"""
        self.info("="*80)

        if exito:
            self.info(config.MENSAJES['proceso_completo'])
        else:
            self.error("Proceso finalizado con errores")

        self.info("\n📊 ESTADÍSTICAS DEL PROCESAMIENTO:")
        self.info(f"  - Registros procesados: {self.stats['registros_procesados']}")
        self.info(f"  - Duplicados eliminados: {self.stats['duplicados_eliminados']}")
        self.info(f"  - Estados inferidos: {self.stats['estados_inferidos']}")
        self.info(f"  - Turnos completos: {self.stats['turnos_completos']}")
        self.info(f"  - Turnos incompletos: {self.stats['turnos_incompletos']}")
        self.info(f"  - Advertencias: {self.stats['advertencias']}")
        self.info(f"  - Errores: {self.stats['errores']}")
        self.info("="*80)

    def log_fase(self, nombre_fase):
        """Registra el inicio de una fase del procesamiento"""
        self.info(f"\n{'─'*80}")
        self.info(f"📌 FASE: {nombre_fase}")
        self.info(f"{'─'*80}")

    def log_duplicados(self, empleado, fecha_hora, cantidad):
        """Registra eliminación de duplicados"""
        self.debug(
            f"Duplicados eliminados - Empleado: {empleado}, "
            f"Fecha/Hora: {fecha_hora}, Cantidad: {cantidad}"
        )
        self.incrementar_stat('duplicados_eliminados', cantidad)

    def log_inferencia(self, empleado, fecha_hora, estado_inferido, metodo):
        """Registra inferencia de estado"""
        self.debug(
            f"Estado inferido - Empleado: {empleado}, "
            f"Fecha/Hora: {fecha_hora}, Estado: {estado_inferido}, "
            f"Método: {metodo}"
        )
        self.incrementar_stat('estados_inferidos')

    def log_turno(self, empleado, fecha, entrada, salida, horas, es_completo):
        """Registra construcción de turno"""
        tipo = "completo" if es_completo else "incompleto"
        self.debug(
            f"Turno {tipo} - Empleado: {empleado}, Fecha: {fecha}, "
            f"Entrada: {entrada}, Salida: {salida}, Horas: {horas}"
        )

        if es_completo:
            self.incrementar_stat('turnos_completos')
        else:
            self.incrementar_stat('turnos_incompletos')


# Instancia global del logger
logger = HuelleroLogger()
