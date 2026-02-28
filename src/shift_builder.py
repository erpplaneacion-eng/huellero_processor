"""
Módulo de Construcción de Turnos
Empareja entradas con salidas y construye turnos completos
"""

import pandas as pd
from datetime import datetime, timedelta
import config
from src.logger import logger


class ShiftBuilder:
    """Construye turnos a partir de marcaciones"""
    
    def __init__(self):
        """Inicializa el constructor de turnos"""
        self.turnos = []
        self.casos_especiales = []

    def _hora_decimal(self, fecha_hora):
        """Convierte datetime a hora decimal (ej: 16:30 -> 16.5)."""
        return fecha_hora.hour + fecha_hora.minute / 60

    def _es_vigilante_castigo(self, codigo):
        """Valida si el código está en la regla especial de castigo para vigilantes."""
        if not config.VIGILANTE_CASTIGO_HABILITADO:
            return False
        try:
            return int(codigo) in set(config.VIGILANTE_CASTIGO_CODIGOS)
        except (TypeError, ValueError):
            return False

    def _en_ventana(self, fecha_hora, ventana):
        """Valida si una hora cae dentro de una ventana decimal [inicio, fin]."""
        hora = self._hora_decimal(fecha_hora)
        inicio, fin = ventana
        return inicio <= hora <= fin

    def _horas_entre(self, inicio, fin):
        """Calcula horas entre dos datetimes."""
        return (fin - inicio).total_seconds() / 3600
    
    def es_turno_nocturno(self, fecha_hora_entrada):
        """
        Determina si un turno es nocturno basándose en hora de entrada

        Args:
            fecha_hora_entrada: datetime de entrada o hora como entero/float

        Returns:
            True si es nocturno
        """
        if hasattr(fecha_hora_entrada, 'hour'):
            # Es un datetime, convertir a hora decimal
            hora_decimal = fecha_hora_entrada.hour + fecha_hora_entrada.minute / 60
        else:
            # Es un número (hora)
            hora_decimal = fecha_hora_entrada
        return hora_decimal >= config.HORA_INICIO_TURNO_NOCTURNO
    
    def construir_turnos_empleado(self, df_empleado):
        """
        Construye turnos para un empleado específico
        
        Args:
            df_empleado: DataFrame con marcaciones del empleado
            
        Returns:
            Lista de dict con turnos construidos
        """
        turnos_empleado = []
        df_emp = df_empleado.sort_values('FECHA_HORA').reset_index(drop=True)
        codigo_empleado = df_emp.iloc[0]['CODIGO'] if len(df_emp) > 0 else None
        aplicar_castigo_vigilante = self._es_vigilante_castigo(codigo_empleado)
        
        i = 0
        while i < len(df_emp):
            registro = df_emp.iloc[i]
            
            # Si es una entrada
            if registro['ESTADO'] == 'Entrada':
                entrada = registro
                entrada_fecha_hora = entrada['FECHA_HORA']
                entrada_hora = entrada_fecha_hora.hour
                castigo_marcacion_diurna = False
                
                # Buscar la salida correspondiente
                salida = None
                salida_idx = None
                salida_corregida = False

                # Regla especial (castigo vigilantes):
                # Si hay marca AM + PM el mismo día, liquidar como diurno.
                if (
                    aplicar_castigo_vigilante
                    and self._en_ventana(entrada_fecha_hora, config.VIGILANTE_VENTANA_AM)
                ):
                    for j in range(i + 1, len(df_emp)):
                        siguiente = df_emp.iloc[j]
                        if siguiente['FECHA_HORA'].date() != entrada_fecha_hora.date():
                            break
                        if self._en_ventana(siguiente['FECHA_HORA'], config.VIGILANTE_VENTANA_PM):
                            horas_candidatas = self._horas_entre(entrada_fecha_hora, siguiente['FECHA_HORA'])
                            if horas_candidatas <= 0 or horas_candidatas > config.HORAS_MAXIMAS_TURNO:
                                continue
                            salida = siguiente
                            salida_idx = j
                            salida_corregida = siguiente['ESTADO'] == 'Entrada'
                            castigo_marcacion_diurna = True
                            break

                if salida is None:
                    for j in range(i + 1, len(df_emp)):
                        siguiente = df_emp.iloc[j]

                        if siguiente['ESTADO'] == 'Salida':
                            horas_candidatas = self._horas_entre(entrada_fecha_hora, siguiente['FECHA_HORA'])
                            if horas_candidatas <= 0:
                                continue
                            if horas_candidatas > config.HORAS_MAXIMAS_TURNO:
                                # Si la primera salida válida está demasiado lejos, no forzar emparejamiento.
                                break
                            salida = siguiente
                            salida_idx = j
                            break
                        elif siguiente['ESTADO'] == 'Entrada':
                            # Encontró otra entrada antes de salida
                            # Si es el mismo día, tratar como salida
                            if siguiente['FECHA_HORA'].date() == entrada_fecha_hora.date():
                                # NO parear si la primera entrada es madrugada temprana (<8:00)
                                # y la segunda es claramente nocturna (>=19:00)
                                # Esto indica patrón de turno nocturno: la primera es salida del día anterior
                                entrada_es_madrugada_temprana = entrada_hora < 8
                                hora_siguiente = self._hora_decimal(siguiente['FECHA_HORA'])
                                siguiente_es_nocturno_claro = hora_siguiente >= 19

                                if entrada_es_madrugada_temprana and siguiente_es_nocturno_claro:
                                    # No parear - la entrada de madrugada será salida de turno nocturno anterior
                                    break

                                horas_candidatas = self._horas_entre(entrada_fecha_hora, siguiente['FECHA_HORA'])
                                if horas_candidatas <= 0 or horas_candidatas > config.HORAS_MAXIMAS_TURNO:
                                    break
                                salida = siguiente
                                salida_idx = j
                                salida_corregida = True
                            break
                
                # Construir turno
                if salida is not None:
                    # Turno completo
                    salida_fecha_hora = salida['FECHA_HORA']
                    horas_laboradas = (salida_fecha_hora - entrada_fecha_hora).total_seconds() / 3600
                    
                    # Determinar fecha del turno (fecha de entrada)
                    fecha_turno = entrada_fecha_hora.date()
                    
                    # Determinar si es nocturno
                    es_nocturno = False if castigo_marcacion_diurna else self.es_turno_nocturno(entrada_fecha_hora)
                    
                    turno = {
                        'codigo': entrada['CODIGO'],
                        'nombre': entrada['NOMBRE'],
                        'fecha': fecha_turno,
                        'entrada': entrada_fecha_hora,
                        'salida': salida_fecha_hora,
                        'horas': round(horas_laboradas, 2),
                        'es_nocturno': es_nocturno,
                        'completo': True,
                        'entrada_inferida': entrada.get('ESTADO_INFERIDO', False),
                        'salida_inferida': salida.get('ESTADO_INFERIDO', False),
                        'salida_corregida': salida_corregida,
                        'castigo_marcacion_diurna': castigo_marcacion_diurna,
                        'nocturno_prospectivo': False,
                        'salida_estandar_nocturna': False
                    }
                    
                    turnos_empleado.append(turno)
                    
                    # Saltar a después de la salida
                    i = salida_idx + 1
                    
                else:
                    # Entrada sin salida
                    fecha_turno = entrada_fecha_hora.date()
                    salida_inferida_dt = None
                    es_nocturno_inferido = self.es_turno_nocturno(entrada_fecha_hora)

                    # Regla especial vigilantes:
                    # Si quedó marca única en ventana AM/PM, cerrar a +12h.
                    if aplicar_castigo_vigilante:
                        if self._en_ventana(entrada_fecha_hora, config.VIGILANTE_VENTANA_AM):
                            salida_inferida_dt = entrada_fecha_hora + timedelta(hours=12)
                            es_nocturno_inferido = False
                        elif self._en_ventana(entrada_fecha_hora, config.VIGILANTE_VENTANA_PM):
                            salida_inferida_dt = entrada_fecha_hora + timedelta(hours=12)
                            es_nocturno_inferido = True

                    if salida_inferida_dt is not None:
                        turno = {
                            'codigo': entrada['CODIGO'],
                            'nombre': entrada['NOMBRE'],
                            'fecha': fecha_turno,
                            'entrada': entrada_fecha_hora,
                            'salida': salida_inferida_dt,
                            'horas': round(self._horas_entre(entrada_fecha_hora, salida_inferida_dt), 2),
                            'es_nocturno': es_nocturno_inferido,
                            'completo': True,
                            'entrada_inferida': entrada.get('ESTADO_INFERIDO', False),
                            'salida_inferida': True,
                            'salida_corregida': False,
                            'castigo_marcacion_diurna': False,
                            'nocturno_prospectivo': False,
                            'salida_estandar_nocturna': False
                        }
                        turnos_empleado.append(turno)
                        i += 1
                        continue
                     
                    turno = {
                        'codigo': entrada['CODIGO'],
                        'nombre': entrada['NOMBRE'],
                        'fecha': fecha_turno,
                        'entrada': entrada_fecha_hora,
                        'salida': None,
                        'horas': None,
                        'es_nocturno': es_nocturno_inferido,
                        'completo': False,
                        'entrada_inferida': entrada.get('ESTADO_INFERIDO', False),
                        'salida_inferida': False,
                        'salida_corregida': False,
                        'castigo_marcacion_diurna': False,
                        'nocturno_prospectivo': False,
                        'salida_estandar_nocturna': False
                    }
                    
                    turnos_empleado.append(turno)
                    i += 1
            
            elif registro['ESTADO'] == 'Salida':
                # Salida sin entrada previa
                salida_fecha_hora = registro['FECHA_HORA']
                
                # Verificar si puede ser parte de un turno nocturno
                # (salida en madrugada sin entrada en el mismo día)
                if salida_fecha_hora.hour < 10:
                    # Buscar si hay entrada del día anterior
                    fecha_anterior = salida_fecha_hora.date() - timedelta(days=1)
                    
                    # Buscar entrada en turnos ya construidos
                    entrada_previa = None
                    for turno_prev in reversed(turnos_empleado):
                        if turno_prev['fecha'] == fecha_anterior and turno_prev['salida'] is None:
                            entrada_previa = turno_prev
                            break
                    
                    if entrada_previa:
                        # Actualizar turno previo con esta salida
                        entrada_previa['salida'] = salida_fecha_hora
                        horas = (salida_fecha_hora - entrada_previa['entrada']).total_seconds() / 3600
                        entrada_previa['horas'] = round(horas, 2)
                        entrada_previa['completo'] = True
                        entrada_previa['salida_inferida'] = registro.get('ESTADO_INFERIDO', False)
                        i += 1
                        continue
                
                # Salida huérfana
                # Asignar a la fecha de la salida
                fecha_turno = salida_fecha_hora.date()
                
                turno = {
                    'codigo': registro['CODIGO'],
                    'nombre': registro['NOMBRE'],
                    'fecha': fecha_turno,
                    'entrada': None,
                    'salida': salida_fecha_hora,
                    'horas': None,
                    'es_nocturno': False,
                    'completo': False,
                    'entrada_inferida': False,
                    'salida_inferida': registro.get('ESTADO_INFERIDO', False),
                    'salida_corregida': False,
                    'castigo_marcacion_diurna': False,
                    'nocturno_prospectivo': False
                }
                
                turnos_empleado.append(turno)
                i += 1
            
            else:
                # Estado indefinido u otro
                i += 1
        
        # Post-procesamiento: parear entradas PM incompletas con registros AM del día siguiente
        indices_a_eliminar = set()
        for idx_t, turno_t in enumerate(turnos_empleado):
            if idx_t in indices_a_eliminar:
                continue
            if (not turno_t['completo']
                    and turno_t['entrada'] is not None
                    and turno_t['salida'] is None
                    and self.es_turno_nocturno(turno_t['entrada'])):
                
                encontro_marca_real = False
                fecha_siguiente = turno_t['fecha'] + timedelta(days=1)
                
                # --- PASO 1: Buscar marca real en la mañana (Azul) ---
                for idx_s, turno_s in enumerate(turnos_empleado):
                    if idx_s in indices_a_eliminar or idx_s == idx_t:
                        continue
                    if (not turno_s['completo']
                            and turno_s['fecha'] == fecha_siguiente
                            and turno_s['entrada'] is not None
                            and turno_s['entrada'].hour < 10):
                        # Parear como turno nocturno (MARCA REAL)
                        salida_dt = turno_s['entrada']
                        horas = (salida_dt - turno_t['entrada']).total_seconds() / 3600
                        turno_t['salida'] = salida_dt
                        turno_t['horas'] = round(horas, 2)
                        turno_t['completo'] = True
                        turno_t['es_nocturno'] = True
                        turno_t['nocturno_prospectivo'] = True
                        turno_t['salida_estandar_nocturna'] = False # Azul estándar
                        indices_a_eliminar.add(idx_s)
                        encontro_marca_real = True
                        break
                
                # --- PASO 2: Si NO hubo marca real, inferir 6 AM (Morado) ---
                if not encontro_marca_real:
                    salida_inferida = datetime.combine(
                        fecha_siguiente, 
                        datetime.min.time()
                    ).replace(hour=config.HORA_SALIDA_ESTANDAR_NOCTURNA)
                    
                    horas = (salida_inferida - turno_t['entrada']).total_seconds() / 3600
                    turno_t['salida'] = salida_inferida
                    turno_t['horas'] = round(horas, 2)
                    turno_t['completo'] = True
                    turno_t['es_nocturno'] = True
                    turno_t['salida_estandar_nocturna'] = True # Morado
                    turno_t['salida_inferida'] = True

        if indices_a_eliminar:
            turnos_empleado = [t for idx, t in enumerate(turnos_empleado) if idx not in indices_a_eliminar]

        return turnos_empleado
    
    def construir_turnos(self, df):
        """
        Construye turnos para todos los empleados
        
        Args:
            df: DataFrame con marcaciones limpias
            
        Returns:
            DataFrame con turnos construidos
        """
        logger.log_fase("CONSTRUCCIÓN DE TURNOS")
        
        todos_los_turnos = []
        
        # Procesar por empleado
        for codigo in df['CODIGO'].unique():
            df_empleado = df[df['CODIGO'] == codigo].copy()
            turnos_empleado = self.construir_turnos_empleado(df_empleado)
            
            # Registrar en log
            for turno in turnos_empleado:
                logger.log_turno(
                    empleado=f"{turno['codigo']} - {turno['nombre']}",
                    fecha=turno['fecha'],
                    entrada=turno['entrada'].strftime('%H:%M') if turno['entrada'] else None,
                    salida=turno['salida'].strftime('%H:%M') if turno['salida'] else None,
                    horas=turno['horas'],
                    es_completo=turno['completo']
                )
            
            todos_los_turnos.extend(turnos_empleado)
        
        # Convertir a DataFrame
        df_turnos = pd.DataFrame(todos_los_turnos)
        
        logger.info(config.MENSAJES['turnos_construidos'])
        logger.info(f"Total turnos: {len(df_turnos)}")
        logger.info(f"Turnos completos: {df_turnos['completo'].sum()}")
        logger.info(f"Turnos incompletos: {(~df_turnos['completo']).sum()}")
        
        self.turnos = todos_los_turnos
        
        return df_turnos
    
    def obtener_resumen(self):
        """
        Obtiene resumen de la construcción de turnos
        
        Returns:
            Dict con estadísticas
        """
        if not self.turnos:
            return {'total_turnos': 0}
        
        df_turnos = pd.DataFrame(self.turnos)
        
        return {
            'total_turnos': len(self.turnos),
            'turnos_completos': df_turnos['completo'].sum(),
            'turnos_incompletos': (~df_turnos['completo']).sum(),
            'turnos_nocturnos': df_turnos['es_nocturno'].sum() if 'es_nocturno' in df_turnos else 0
        }
