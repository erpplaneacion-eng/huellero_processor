"""
Servicio de Nómina Cali
Genera registros diarios de nómina para manipuladoras de Cali
Corporación Hacia un Valle Solidario
"""

import os
from datetime import datetime, date
from collections import defaultdict
from apps.tecnicos.google_sheets import GoogleSheetsService
from apps.tecnicos.constantes import obtener_id_hoja


class NominaCaliService:
    """Servicio para generar registros de nómina diaria (Cali/Yumbo)"""

    DIAS_SEMANA = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    # Constantes
    MODALIDAD = 'COMPLEMENTO AM/PM PREPARADO'
    TIPO_TIEMPO_LABORADO = 'P. ALIMENTOS'
    NOMBRE_HOJA = 'nomina_cali'

    # Encabezados de la hoja (17 columnas)
    HEADERS = [
        'ID',
        'SUPERVISOR',
        'user',
        'MODALIDAD',
        'DESCRIPCION PROYECTO',
        'TIPO TIEMPO LABORADO',
        'CEDULA',
        'NOMBRE COLABORADOR',
        'FECHA',
        'DIA',
        'HORA INICIAL',
        'HORA FINAL',
        'TOTAL_HORAS',
        'NOVEDAD',
        'FECHA FINAL',
        'DIA FINAL',
        'OBSERVACIONES'
    ]

    def __init__(self, sede='CALI'):
        self.sede = sede
        self.sheets_service = GoogleSheetsService()
        self.sheet_id = obtener_id_hoja(sede)
        self.libro = self.sheets_service.abrir_libro(self.sheet_id)

    def obtener_manipuladoras_activas(self):
        """Obtiene las manipuladoras activas de la hoja Manipuladoras"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'Manipuladoras')
        datos = hoja.get_all_records()

        # Filtrar solo activas y excluir incapacitadas
        manipuladoras_activas = [
            m for m in datos
            if m.get('Estado', '').strip().lower() == 'activo'
            and m.get('Estado', '').strip().lower() != 'incapacitada'
            and m.get('Nombre')
            and m.get('No. Documento')
        ]
        return manipuladoras_activas

    def obtener_supervisores(self):
        """Obtiene los supervisores con su user (correo)"""
        hoja = self.sheets_service.obtener_hoja(self.libro, 'sedes_supevisor')
        datos = hoja.get_all_records()

        # Crear diccionario por nombre de supervisor
        supervisores = {}
        for sup in datos:
            nombre = sup.get('nombre', '').strip()
            if nombre:
                supervisores[nombre.upper()] = {
                    'nombre': nombre,
                    'user': sup.get('user', '')
                }
        return supervisores

    def obtener_horarios(self):
        """
        Obtiene los horarios por sede, soportando múltiples turnos.

        Returns:
            dict: {sede_upper: [{'turno': 'A', 'hora_entrada': '', 'hora_salida': ''}, ...]}
        """
        hoja = self.sheets_service.obtener_hoja(self.libro, 'HORARIOS')
        datos = hoja.get_all_records()

        # Crear diccionario con LISTA de turnos por sede
        horarios = defaultdict(list)
        for h in datos:
            sede = h.get('SEDE', '').strip()
            if sede:
                horarios[sede.upper()].append({
                    'turno': h.get('TURNOS', 'A'),
                    'hora_entrada': h.get('HORA ENTRADA', ''),
                    'hora_salida': h.get('HORA SALIDA', '')
                })

        # Ordenar turnos por nombre (A, B, C...)
        for sede in horarios:
            horarios[sede].sort(key=lambda x: x['turno'])

        return dict(horarios)

    def crear_hoja_si_no_existe(self):
        """Crea la hoja nomina_cali si no existe y agrega los encabezados"""
        try:
            hoja = self.sheets_service.obtener_hoja(self.libro, self.NOMBRE_HOJA)
            return hoja
        except Exception:
            # La hoja no existe, crearla
            hoja = self.libro.add_worksheet(
                title=self.NOMBRE_HOJA,
                rows=1000,
                cols=len(self.HEADERS)
            )
            # Agregar encabezados
            hoja.update(values=[self.HEADERS], range_name='A1:Q1')
            print(f"Hoja '{self.NOMBRE_HOJA}' creada con encabezados")
            return hoja

    def _calcular_total_horas(self, hora_entrada, hora_salida):
        """
        Calcula el total de horas entre hora de entrada y salida.

        Args:
            hora_entrada: string en formato HH:MM o HH:MM:SS
            hora_salida: string en formato HH:MM o HH:MM:SS

        Returns:
            string: total de horas en formato decimal (ej: "5.50") o vacío si no se puede calcular
        """
        try:
            if not hora_entrada or not hora_salida:
                return ''

            def parse_hora_a_minutos(h):
                h = str(h).strip()
                if not h:
                    return None
                partes = h.split(':')
                horas = int(partes[0])
                minutos = int(partes[1]) if len(partes) > 1 else 0
                return horas * 60 + minutos

            inicio_min = parse_hora_a_minutos(hora_entrada)
            fin_min = parse_hora_a_minutos(hora_salida)

            if inicio_min is None or fin_min is None:
                return ''

            diff_min = fin_min - inicio_min
            # Manejar turnos nocturnos (salida al día siguiente)
            if diff_min < 0:
                diff_min += 24 * 60

            # Convertir a decimal
            total_horas = diff_min / 60
            return f"{total_horas:.2f}"

        except Exception:
            return ''

    def _calcular_turno_rotativo(self, dia_semana_num, indice_manipuladora, cantidad_turnos):
        """
        Calcula qué turno corresponde a una manipuladora según el día y su índice.

        Fórmula: turno_index = (día_semana + índice_manipuladora) % cantidad_turnos

        Args:
            dia_semana_num: número del día (0=Lunes, 5=Sábado)
            indice_manipuladora: índice de la manipuladora dentro de su sede (0, 1, 2...)
            cantidad_turnos: número de turnos disponibles para la sede

        Returns:
            int: índice del turno a asignar (0, 1, 2...)
        """
        return (dia_semana_num + indice_manipuladora) % cantidad_turnos

    def obtener_novedades_activas(self, fecha_proceso):
        """
        Obtiene novedades activas desde la hoja 'novedades_cali'.
        Retorna {cedula_limpia: datos_novedad} si la fecha_proceso está en rango [FECHA, FECHA FINAL].
        """
        try:
            hoja = self.sheets_service.obtener_hoja(self.libro, 'novedades_cali')
            registros = hoja.get_all_records()
        except Exception:
            # Si falla (hoja no existe o error), asumimos sin novedades
            return {}

        novedades = {}
        fecha_proceso_date = fecha_proceso if isinstance(fecha_proceso, date) else date.today()

        for fila in registros:
            # Obtener fechas y cédula
            f_inicio_str = str(fila.get('FECHA', '')).strip()
            f_fin_str = str(fila.get('FECHA FINAL', '')).strip()
            cedula = str(fila.get('CEDULA', '')).strip()

            if not f_inicio_str or not f_fin_str or not cedula:
                continue
            
            # Normalizar cédula (quitar puntos) para comparación robusta
            cedula_limpia = cedula.replace('.', '').replace(',', '').strip()

            try:
                # Intentar parsear YYYY-MM-DD (ISO) o DD/MM/YYYY
                try:
                    f_inicio = datetime.strptime(f_inicio_str, '%Y-%m-%d').date()
                except ValueError:
                    f_inicio = datetime.strptime(f_inicio_str, '%d/%m/%Y').date()

                try:
                    f_fin = datetime.strptime(f_fin_str, '%Y-%m-%d').date()
                except ValueError:
                    f_fin = datetime.strptime(f_fin_str, '%d/%m/%Y').date()
                
                # Verificar rango (inclusive)
                if f_inicio <= fecha_proceso_date <= f_fin:
                    novedades[cedula_limpia] = {
                        'tipo_tiempo': fila.get('TIPO TIEMPO LABORADO', ''),
                        'fecha_final': f_fin_str,
                        'dia_final': fila.get('DIA FINAL', ''),
                        'observaciones': fila.get('OBSERVACIONES', '') or fila.get('OBSERVACION', '')
                    }
            except ValueError:
                continue

        return novedades

    def generar_registros_dia(self, fecha=None):
        """
        Genera los registros de nómina para un día específico.
        Verifica novedades activas antes de asignar turnos rotativos.

        Para sedes con múltiples turnos y manipuladoras, rota los turnos
        usando la fórmula: (día_semana + índice_manipuladora) % cantidad_turnos

        Args:
            fecha: date object, si es None usa fecha actual

        Returns:
            tuple: (registros_generados, mensaje)
        """
        if fecha is None:
            fecha = date.today()

        # Verificar si es domingo (no se crean registros)
        dia_semana_num = fecha.weekday()
        if dia_semana_num == 6:  # Domingo
            return [], f"No se crean registros los domingos ({fecha})"

        dia_semana = self.DIAS_SEMANA[dia_semana_num]
        es_sabado = dia_semana_num == 5
        fecha_str = fecha.strftime('%Y-%m-%d')

        # Obtener datos
        manipuladoras = self.obtener_manipuladoras_activas()
        supervisores = self.obtener_supervisores()
        horarios = self.obtener_horarios()
        novedades_activas = self.obtener_novedades_activas(fecha)

        # Agrupar manipuladoras por sede para asignar índices
        manip_por_sede = defaultdict(list)
        for manip in manipuladoras:
            sede = manip.get('sede educativa', '').strip().upper()
            manip_por_sede[sede].append(manip)

        # Generar registros
        registros = []
        consecutivo = 1

        for sede_upper, manips_sede in manip_por_sede.items():
            # Obtener turnos de esta sede
            turnos_sede = horarios.get(sede_upper, [])

            for indice_manip, manip in enumerate(manips_sede):
                # Generar ID único
                id_registro = f"NOM-{fecha.strftime('%Y%m%d')}-{consecutivo:04d}"
                consecutivo += 1

                # Datos de la manipuladora
                nombre = manip.get('Nombre', '')
                cedula_raw = str(manip.get('No. Documento', '')).strip()
                cedula_limpia = cedula_raw.replace('.', '').replace(',', '').strip()
                
                sede = manip.get('sede educativa', '')
                supervisor_nombre = manip.get('SUPERVISOR', '')

                # Buscar user del supervisor
                sup_info = supervisores.get(supervisor_nombre.upper(), {})
                user = sup_info.get('user', '')

                # --- VERIFICAR NOVEDAD ACTIVA ---
                # Buscar usando la cédula normalizada
                novedad_info = novedades_activas.get(cedula_limpia)
                
                if novedad_info:
                    # CASO: Novedad Activa
                    # Se mantiene la novedad y fecha final hasta que expire
                    tipo_tiempo = novedad_info['tipo_tiempo']
                    novedad_val = 'SI'
                    fecha_final = novedad_info['fecha_final']
                    dia_final = novedad_info['dia_final']
                    observaciones = novedad_info['observaciones']
                    
                    hora_entrada = ''
                    hora_salida = ''
                    total_horas = '0'
                    
                else:
                    # CASO: Normal (P. ALIMENTOS)
                    tipo_tiempo = self.TIPO_TIEMPO_LABORADO
                    novedad_val = ''
                    fecha_final = fecha_str
                    dia_final = dia_semana
                    observaciones = ''

                    # Determinar horario según rotación de turnos
                    if es_sabado:
                        # Sábados: horas vacías
                        hora_entrada = ''
                        hora_salida = ''
                    elif not turnos_sede:
                        # Sede sin horario registrado
                        hora_entrada = ''
                        hora_salida = ''
                    elif len(turnos_sede) == 1:
                        # Sede con un solo turno - asignar directamente
                        hora_entrada = turnos_sede[0].get('hora_entrada', '')
                        hora_salida = turnos_sede[0].get('hora_salida', '')
                    else:
                        # Sede con múltiples turnos
                        # 1. Verificar si tiene TURNO FIJO asignado en hoja Manipuladoras
                        turno_fijo = str(manip.get('TURNOS', '')).strip().upper()
                        turno_encontrado = None

                        if turno_fijo:
                            # Buscar si el turno fijo existe en los horarios de la sede
                            for t in turnos_sede:
                                if t.get('turno', '').upper() == turno_fijo:
                                    turno_encontrado = t
                                    break
                        
                        if turno_encontrado:
                            # USAR TURNO FIJO
                            hora_entrada = turno_encontrado.get('hora_entrada', '')
                            hora_salida = turno_encontrado.get('hora_salida', '')
                        else:
                            # USAR ROTACIÓN AUTOMÁTICA (Fallback)
                            turno_idx = self._calcular_turno_rotativo(
                                dia_semana_num,
                                indice_manip,
                                len(turnos_sede)
                            )
                            turno_asignado = turnos_sede[turno_idx]
                            hora_entrada = turno_asignado.get('hora_entrada', '')
                            hora_salida = turno_asignado.get('hora_salida', '')

                    # Calcular total de horas
                    total_horas = self._calcular_total_horas(hora_entrada, hora_salida)

                registro = [
                    id_registro,                # ID
                    supervisor_nombre,          # SUPERVISOR
                    user,                       # user
                    self.MODALIDAD,             # MODALIDAD (constante)
                    sede,                       # DESCRIPCION PROYECTO
                    tipo_tiempo,                # TIPO TIEMPO LABORADO
                    cedula_raw,                 # CEDULA (usamos la original)
                    nombre,                     # NOMBRE COLABORADOR
                    fecha_str,                  # FECHA
                    dia_semana,                 # DIA
                    hora_entrada,               # HORA INICIAL
                    hora_salida,                # HORA FINAL
                    total_horas,                # TOTAL_HORAS
                    novedad_val,                # NOVEDAD
                    fecha_final,                # FECHA FINAL
                    dia_final,                  # DIA FINAL
                    observaciones               # OBSERVACIONES
                ]
                registros.append(registro)

        return registros, f"Generados {len(registros)} registros para {dia_semana} {fecha_str}"

    def verificar_registros_existentes(self, fecha):
        """Verifica si ya existen registros para una fecha"""
        hoja = self.crear_hoja_si_no_existe()
        datos = hoja.get_all_values()

        fecha_str = fecha.strftime('%Y-%m-%d')

        # Buscar si hay registros con esta fecha (columna 9 = FECHA, índice 8)
        for fila in datos[1:]:  # Skip header
            if len(fila) > 8 and fila[8] == fecha_str:
                return True
        return False

    def insertar_registros(self, registros):
        """Inserta los registros en la hoja de nómina"""
        if not registros:
            return 0

        hoja = self.crear_hoja_si_no_existe()

        # Obtener última fila con datos
        datos_actuales = hoja.get_all_values()
        ultima_fila = len(datos_actuales) + 1

        # Insertar registros
        rango = f"A{ultima_fila}:Q{ultima_fila + len(registros) - 1}"
        hoja.update(values=registros, range_name=rango)

        return len(registros)

    def ejecutar_nomina_diaria(self, fecha=None, forzar=False):
        """
        Ejecuta el proceso completo de nómina diaria

        Args:
            fecha: date object, si es None usa fecha actual
            forzar: si es True, crea registros aunque ya existan

        Returns:
            dict con resultado de la operación
        """
        if fecha is None:
            fecha = date.today()

        resultado = {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'dia': self.DIAS_SEMANA.get(fecha.weekday(), ''),
            'exito': False,
            'mensaje': '',
            'registros_creados': 0
        }

        # Verificar domingo
        if fecha.weekday() == 6:
            resultado['mensaje'] = 'No se crean registros los domingos'
            resultado['exito'] = True
            return resultado

        # Verificar si ya existen registros
        if not forzar and self.verificar_registros_existentes(fecha):
            resultado['mensaje'] = f'Ya existen registros para {fecha}'
            return resultado

        # Generar registros
        registros, mensaje = self.generar_registros_dia(fecha)

        if not registros:
            resultado['mensaje'] = mensaje
            return resultado

        # Insertar registros
        cantidad = self.insertar_registros(registros)

        resultado['exito'] = True
        resultado['mensaje'] = mensaje
        resultado['registros_creados'] = cantidad

        return resultado


def ejecutar_nomina_cali_hoy(sede='CALI'):
    """Función helper para ejecutar nómina del día actual"""
    service = NominaCaliService(sede=sede)
    resultado = service.ejecutar_nomina_diaria()
    return resultado


if __name__ == '__main__':
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    resultado = ejecutar_nomina_cali_hoy()
    print(f"Resultado: {resultado}")
