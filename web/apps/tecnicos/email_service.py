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

    def enviar_correo(self, destinatario, asunto, cuerpo_html):
        """
        Envía un correo electrónico

        Args:
            destinatario: Email del destinatario
            asunto: Asunto del correo
            cuerpo_html: Contenido HTML del correo

        Returns:
            dict con resultado de la operación
        """
        try:
            # Crear mensaje
            mensaje = MIMEMultipart('alternative')
            mensaje['Subject'] = asunto
            mensaje['From'] = self.email_user
            mensaje['To'] = destinatario

            # Adjuntar cuerpo HTML
            parte_html = MIMEText(cuerpo_html, 'html', 'utf-8')
            mensaje.attach(parte_html)

            # Conectar y enviar
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
        Genera el HTML del reporte de liquidación

        Args:
            fecha: date object de la liquidación
            registros: lista de registros generados
            resultado: dict con resultado de la operación

        Returns:
            tuple: (asunto, cuerpo_html)
        """
        dia_semana = self.DIAS_SEMANA.get(fecha.weekday(), '')
        fecha_str = fecha.strftime('%d/%m/%Y')

        # Análisis de registros
        total_sedes = len(registros)
        sedes_con_novedad = []
        sedes_sin_raciones = []
        total_manipuladoras = 0
        total_raciones = 0

        for reg in registros:
            # Estructura: [SUPERVISOR, SEDE, FECHA, DIA, CANT_MANIP, TOTAL_HORAS,
            #              HUBO_RACIONES, COMP_AMPM, COMP_PM, ALMUERZO, IND,
            #              TOTAL_RACIONES, OBSERVACION, NOVEDAD]
            sede = reg[1]
            cant_manip = reg[4] if isinstance(reg[4], int) else 0
            hubo_raciones = reg[6]
            raciones = reg[11] if isinstance(reg[11], int) else 0
            observacion = reg[12]
            novedad = reg[13]

            total_manipuladoras += cant_manip
            total_raciones += raciones

            if novedad == 'SI':
                sedes_con_novedad.append(sede)

            if hubo_raciones == 'NO' or observacion == 'ASEO/LIMPIEZA':
                sedes_sin_raciones.append(sede)

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
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2c5aa0;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 20px;
                    border: 1px solid #ddd;
                }}
                .resumen {{
                    background-color: #fff;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                    border-left: 4px solid #2c5aa0;
                }}
                .alerta {{
                    background-color: #fff3cd;
                    border-left-color: #ffc107;
                }}
                .success {{
                    background-color: #d4edda;
                    border-left-color: #28a745;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #2c5aa0;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .footer {{
                    text-align: center;
                    padding: 15px;
                    color: #666;
                    font-size: 12px;
                }}
                .numero {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c5aa0;
                }}
                .lista-sedes {{
                    background-color: #fff;
                    padding: 10px;
                    border-radius: 4px;
                    margin-top: 10px;
                }}
                .lista-sedes li {{
                    margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Reporte de Liquidación de Nómina</h1>
                <h2>{dia_semana} {fecha_str}</h2>
            </div>

            <div class="content">
                <div class="resumen success">
                    <h3>Resumen General</h3>
                    <table>
                        <tr>
                            <td>Total de Sedes</td>
                            <td class="numero">{total_sedes}</td>
                        </tr>
                        <tr>
                            <td>Total de Manipuladoras</td>
                            <td class="numero">{total_manipuladoras}</td>
                        </tr>
                        <tr>
                            <td>Total de Raciones</td>
                            <td class="numero">{total_raciones:,}</td>
                        </tr>
                    </table>
                </div>
        """

        # Sedes con novedades
        if sedes_con_novedad:
            html += f"""
                <div class="resumen alerta">
                    <h3>Sedes con Novedades ({len(sedes_con_novedad)})</h3>
                    <p>Las siguientes sedes reportaron novedades que requieren revisión:</p>
                    <ul class="lista-sedes">
            """
            for sede in sedes_con_novedad:
                html += f"<li>{sede}</li>"
            html += """
                    </ul>
                </div>
            """

        # Sedes sin raciones (aseo/limpieza)
        if sedes_sin_raciones:
            html += f"""
                <div class="resumen">
                    <h3>Sedes sin Raciones - Aseo/Limpieza ({len(sedes_sin_raciones)})</h3>
                    <p>Las siguientes sedes no tuvieron raciones (solo aseo/limpieza):</p>
                    <ul class="lista-sedes">
            """
            for sede in sedes_sin_raciones:
                html += f"<li>{sede}</li>"
            html += """
                    </ul>
                </div>
            """

        # Si no hay novedades ni sedes sin raciones
        if not sedes_con_novedad and not sedes_sin_raciones:
            html += """
                <div class="resumen success">
                    <h3>Sin Novedades</h3>
                    <p>No se reportaron novedades ni anomalías en el día.</p>
                </div>
            """

        html += f"""
            </div>

            <div class="footer">
                <p>Corporación Hacia un Valle Solidario</p>
                <p>Este es un correo automático generado por el sistema de liquidación de nómina.</p>
                <p>Generado: {date.today().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
        </body>
        </html>
        """

        asunto = f"Liquidación Nómina - {dia_semana} {fecha_str}"

        if sedes_con_novedad:
            asunto += f" - {len(sedes_con_novedad)} NOVEDADES"

        return asunto, html

    def enviar_reporte_liquidacion(self, fecha, registros, resultado):
        """
        Genera y envía el reporte de liquidación al coordinador

        Args:
            fecha: date object de la liquidación
            registros: lista de registros generados
            resultado: dict con resultado de la operación

        Returns:
            dict con resultado del envío
        """
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
    # Para probar desde línea de comandos
    from dotenv import load_dotenv
    load_dotenv()

    # Test de conexión
    try:
        service = EmailService()
        print("Configuración de email correcta")
        print(f"  Remitente: {service.email_user}")
        print(f"  Destinatario: {service.email_coordinador}")
    except Exception as e:
        print(f"Error: {e}")
