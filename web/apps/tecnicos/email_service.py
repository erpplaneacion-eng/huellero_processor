"""
Servicio de Email para notificaciones
Envía reportes de liquidación de nómina por Gmail
Corporación Hacia un Valle Solidario
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from collections import defaultdict


class EmailService:
    """Servicio para enviar correos via Gmail"""

    DIAS_SEMANA = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    def __init__(self):
        self.smtp_host = 'smtp.gmail.com'
        self.smtp_port = 587
        self.email_user = os.environ.get('EMAIL_HOST_USER')
        self.email_password = os.environ.get('EMAIL_HOST_PASSWORD')
        self.email_coordinador = os.environ.get('EMAIL_COORDINADOR')

        if not all([self.email_user, self.email_password, self.email_coordinador]):
            raise ValueError(
                "Faltan variables de entorno: EMAIL_HOST_USER, "
                "EMAIL_HOST_PASSWORD, EMAIL_COORDINADOR"
            )

    def _parsear_horas(self, valor):
        """Convierte formato HH:MM a horas decimales"""
        try:
            val_str = str(valor).strip()
            if not val_str:
                return 0.0
            if ':' in val_str:
                partes = val_str.split(':')
                horas = int(partes[0]) if partes[0] else 0
                minutos = int(partes[1]) if len(partes) > 1 and partes[1] else 0
                return horas + (minutos / 60.0)
            return float(val_str.replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, valor):
        """Convierte a entero de forma segura"""
        try:
            if isinstance(valor, int):
                return valor
            return int(float(str(valor).replace(',', '.').strip() or 0))
        except (ValueError, TypeError):
            return 0

    def enviar_correo(self, destinatario, asunto, cuerpo_html):
        """Envía un correo electrónico"""
        try:
            mensaje = MIMEMultipart('alternative')
            mensaje['Subject'] = asunto
            mensaje['From'] = self.email_user
            mensaje['To'] = destinatario

            parte_html = MIMEText(cuerpo_html, 'html', 'utf-8')
            mensaje.attach(parte_html)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as servidor:
                servidor.starttls()
                servidor.login(self.email_user, self.email_password)
                servidor.send_message(mensaje)

            return {
                'exito': True,
                'mensaje': f'Correo enviado a {destinatario}'
            }

        except smtplib.SMTPAuthenticationError:
            return {
                'exito': False,
                'mensaje': 'Error de autenticación. Verifica EMAIL_HOST_PASSWORD'
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error al enviar correo: {str(e)}'
            }

    def generar_reporte_liquidacion(self, fecha, registros, resultado):
        """
        Genera el HTML del reporte de liquidación con desglose por supervisor

        Args:
            fecha: date object de la liquidación
            registros: lista de registros generados
            resultado: dict con resultado de la operación

        Returns:
            tuple: (asunto, cuerpo_html)
        """
        dia_semana = self.DIAS_SEMANA.get(fecha.weekday(), '')
        fecha_str = fecha.strftime('%d/%m/%Y')

        # Estructura de registros (con ID en index 0):
        # [ID, SUPERVISOR, SEDE, FECHA, DIA, CANT_MANIP, TOTAL_HORAS,
        #  HUBO_RACIONES, COMP_AMPM, COMP_PM, ALMUERZO, IND,
        #  TOTAL_RACIONES, OBSERVACION, NOVEDAD]
        # Índices: 1=SUP, 2=SEDE, 5=CANT, 6=HORAS, 7=HUBO_RAC, 12=TOT_RAC, 13=OBS, 14=NOV

        # Agrupar por supervisor
        supervisores = defaultdict(list)
        totales = {
            'sedes': 0,
            'manipuladoras': 0,
            'raciones': 0,
            'dias_nomina': 0,
            'dias_raciones': 0,
            'inconsistencias': 0
        }

        for reg in registros:
            supervisor = reg[1] if len(reg) > 1 else 'Sin Supervisor'
            sede = reg[2] if len(reg) > 2 else ''
            cant_manip = self._safe_int(reg[5]) if len(reg) > 5 else 0
            total_horas = reg[6] if len(reg) > 6 else ''
            horas_decimal = self._parsear_horas(total_horas)
            hubo_raciones = reg[7] if len(reg) > 7 else ''
            total_raciones = self._safe_int(reg[12]) if len(reg) > 12 else 0
            observacion = reg[13] if len(reg) > 13 else ''
            novedad = reg[14] if len(reg) > 14 else ''

            # Determinar estado
            tiene_inconsistencia = False
            tipo_inconsistencia = ''

            if total_raciones > 0 and horas_decimal == 0:
                tiene_inconsistencia = True
                tipo_inconsistencia = 'Raciones sin horas'
            elif horas_decimal > 0 and total_raciones == 0:
                tiene_inconsistencia = True
                tipo_inconsistencia = 'Horas sin raciones'

            # Agregar a supervisor
            supervisores[supervisor].append({
                'sede': sede,
                'manipuladoras': cant_manip,
                'horas': total_horas,
                'horas_decimal': horas_decimal,
                'raciones': total_raciones,
                'hubo_raciones': hubo_raciones,
                'observacion': observacion,
                'novedad': novedad,
                'inconsistencia': tiene_inconsistencia,
                'tipo_inconsistencia': tipo_inconsistencia
            })

            # Acumular totales
            totales['sedes'] += 1
            totales['manipuladoras'] += cant_manip
            totales['raciones'] += total_raciones
            if horas_decimal > 0:
                totales['dias_nomina'] += 1
            if total_raciones > 0:
                totales['dias_raciones'] += 1
            if tiene_inconsistencia:
                totales['inconsistencias'] += 1

        # Construir HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #2c5aa0 0%, #1e3d6f 100%);
                    color: white;
                    padding: 25px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .header h1 {{
                    margin: 0 0 10px 0;
                    font-size: 24px;
                }}
                .header h2 {{
                    margin: 0;
                    font-size: 18px;
                    font-weight: normal;
                    opacity: 0.9;
                }}
                .content {{
                    background-color: #fff;
                    padding: 25px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .kpi-grid {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-bottom: 25px;
                }}
                .kpi-card {{
                    flex: 1;
                    min-width: 120px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    text-align: center;
                    border-left: 4px solid #2c5aa0;
                }}
                .kpi-card.success {{
                    border-left-color: #28a745;
                }}
                .kpi-card.warning {{
                    border-left-color: #ffc107;
                }}
                .kpi-card.danger {{
                    border-left-color: #dc3545;
                }}
                .kpi-value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #2c5aa0;
                }}
                .kpi-card.success .kpi-value {{
                    color: #28a745;
                }}
                .kpi-card.danger .kpi-value {{
                    color: #dc3545;
                }}
                .kpi-label {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 5px;
                }}
                .supervisor-section {{
                    margin: 20px 0;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                .supervisor-header {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 12px 15px;
                    font-weight: bold;
                    color: #2c5aa0;
                    border-bottom: 1px solid #e0e0e0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .supervisor-stats {{
                    font-size: 12px;
                    color: #666;
                    font-weight: normal;
                }}
                .sede-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }}
                .sede-table th {{
                    background-color: #2c5aa0;
                    color: white;
                    padding: 10px 8px;
                    text-align: left;
                    font-weight: 600;
                }}
                .sede-table td {{
                    padding: 10px 8px;
                    border-bottom: 1px solid #eee;
                }}
                .sede-table tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .sede-table tr:hover {{
                    background-color: #e8f4f8;
                }}
                .sede-table tr.row-alert {{
                    background-color: #fff3cd;
                }}
                .sede-table tr.row-alert:hover {{
                    background-color: #ffe8a1;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                .badge-success {{
                    background-color: #d4edda;
                    color: #155724;
                }}
                .badge-danger {{
                    background-color: #f8d7da;
                    color: #721c24;
                }}
                .badge-warning {{
                    background-color: #fff3cd;
                    color: #856404;
                }}
                .text-center {{
                    text-align: center;
                }}
                .text-right {{
                    text-align: right;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                    background-color: #f8f9fa;
                    border-radius: 0 0 10px 10px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Reporte de Liquidación de Nómina</h1>
                <h2>{dia_semana} {fecha_str}</h2>
            </div>

            <div class="content">
                <!-- KPIs Generales -->
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-value">{totales['sedes']}</div>
                        <div class="kpi-label">Total Sedes</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{totales['manipuladoras']}</div>
                        <div class="kpi-label">Manipuladoras</div>
                    </div>
                    <div class="kpi-card success">
                        <div class="kpi-value">{totales['dias_nomina']}</div>
                        <div class="kpi-label">Con Horas</div>
                    </div>
                    <div class="kpi-card success">
                        <div class="kpi-value">{totales['dias_raciones']}</div>
                        <div class="kpi-label">Con Raciones</div>
                    </div>
                    <div class="kpi-card danger">
                        <div class="kpi-value">{totales['inconsistencias']}</div>
                        <div class="kpi-label">Inconsistencias</div>
                    </div>
                </div>

                <!-- Detalle por Supervisor -->
                <h3 style="color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 10px;">
                    Detalle por Supervisor
                </h3>
        """

        # Generar sección por cada supervisor
        for supervisor, sedes in sorted(supervisores.items()):
            # Calcular stats del supervisor
            sup_manipuladoras = sum(s['manipuladoras'] for s in sedes)
            sup_raciones = sum(s['raciones'] for s in sedes)
            sup_inconsistencias = sum(1 for s in sedes if s['inconsistencia'])

            html += f"""
                <div class="supervisor-section">
                    <div class="supervisor-header">
                        <span>{supervisor or 'Sin Supervisor'}</span>
                        <span class="supervisor-stats">
                            {len(sedes)} sedes | {sup_manipuladoras} manip. | {sup_raciones:,} raciones
                            {f' | <span style="color: #dc3545;">{sup_inconsistencias} inconsist.</span>' if sup_inconsistencias > 0 else ''}
                        </span>
                    </div>
                    <table class="sede-table">
                        <thead>
                            <tr>
                                <th>Sede</th>
                                <th class="text-center">Manip.</th>
                                <th class="text-center">Horas</th>
                                <th class="text-center">Raciones</th>
                                <th class="text-center">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
            """

            for sede_data in sedes:
                row_class = 'row-alert' if sede_data['inconsistencia'] else ''

                if sede_data['inconsistencia']:
                    estado = f'<span class="badge badge-danger">{sede_data["tipo_inconsistencia"]}</span>'
                elif sede_data['novedad'] == 'SI':
                    estado = '<span class="badge badge-warning">Novedad</span>'
                else:
                    estado = '<span class="badge badge-success">OK</span>'

                html += f"""
                            <tr class="{row_class}">
                                <td>{sede_data['sede']}</td>
                                <td class="text-center">{sede_data['manipuladoras']}</td>
                                <td class="text-center">{sede_data['horas'] or '-'}</td>
                                <td class="text-center">{sede_data['raciones']:,}</td>
                                <td class="text-center">{estado}</td>
                            </tr>
                """

            html += """
                        </tbody>
                    </table>
                </div>
            """

        html += f"""
            </div>

            <div class="footer">
                <p><strong>Corporación Hacia un Valle Solidario</strong></p>
                <p>Este es un correo automático generado por el sistema de liquidación de nómina.</p>
                <p>Generado: {date.today().strftime('%d/%m/%Y')}</p>
            </div>
        </body>
        </html>
        """

        asunto = f"Liquidación Nómina - {dia_semana} {fecha_str}"

        if totales['inconsistencias'] > 0:
            asunto += f" - {totales['inconsistencias']} INCONSISTENCIAS"

        return asunto, html

    def enviar_reporte_liquidacion(self, fecha, registros, resultado):
        """Genera y envía el reporte de liquidación al coordinador"""
        asunto, cuerpo_html = self.generar_reporte_liquidacion(
            fecha, registros, resultado
        )

        return self.enviar_correo(
            destinatario=self.email_coordinador,
            asunto=asunto,
            cuerpo_html=cuerpo_html
        )


def enviar_reporte_liquidacion_hoy(registros, resultado):
    """Función helper para enviar reporte del día actual"""
    service = EmailService()
    return service.enviar_reporte_liquidacion(
        fecha=date.today(),
        registros=registros,
        resultado=resultado
    )


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    try:
        service = EmailService()
        print("Configuración de email correcta")
        print(f"  Remitente: {service.email_user}")
        print(f"  Destinatario: {service.email_coordinador}")
    except Exception as e:
        print(f"Error: {e}")
