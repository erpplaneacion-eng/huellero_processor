# Sistema Procesador de Huellero

Sistema web para procesar archivos de control de asistencia (huellero biométrico) y generar reportes de nómina. Construido para Corporación Hacia un Valle Solidario (CHVS).

## Características

- Limpieza automática de marcaciones duplicadas (ventana de 15 min)
- Inferencia inteligente de estados faltantes (Entrada/Salida)
- Detección y manejo de turnos nocturnos
- Generación de reportes Excel con formato profesional y códigos de observación
- Interfaz web con subida de archivos y visualización de resultados
- Base de datos PostgreSQL con historial de asistencia
- Despliegue en Railway

## Estructura del Proyecto

```
huellero_processor/
├── web/
│   ├── manage.py
│   ├── apps/
│   │   ├── logistica/              # App principal
│   │   │   ├── pipeline/           # Módulos del pipeline de procesamiento
│   │   │   │   ├── config.py       # Umbrales, rangos horarios, feature flags
│   │   │   │   ├── data_cleaner.py
│   │   │   │   ├── state_inference.py
│   │   │   │   ├── shift_builder.py
│   │   │   │   ├── calculator.py
│   │   │   │   └── excel_generator.py
│   │   │   ├── processor.py        # Orquestador del pipeline
│   │   │   ├── models.py           # Modelos PostgreSQL
│   │   │   ├── views.py            # API endpoints
│   │   │   └── management/commands/cargar_maestro.py
│   │   └── users/                  # Autenticación y roles
│   └── huellero_web/               # Configuración Django
│
├── data/
│   ├── input/                      # Archivos .xls/.xlsx del huellero
│   ├── output/                     # Reportes generados
│   └── maestro/
│       └── empleados.xlsx          # Maestro de empleados (fuente de cédulas)
│
├── .env                            # Variables de entorno (no versionado)
├── requirements.txt
└── railway.json
```

## Instalación y Desarrollo

```bash
# Instalar dependencias
cd web
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores correspondientes

# Crear base de datos
python manage.py migrate

# Cargar datos maestro de empleados
python manage.py cargar_maestro

# Crear usuario administrador
python manage.py createsuperuser

# Levantar servidor de desarrollo
python manage.py runserver
```

## Cargar Maestro de Empleados

El maestro se carga desde `data/maestro/empleados.xlsx`, que debe tener estas hojas:

| Hoja | Tabla DB | Contenido |
|------|----------|-----------|
| `empleados_ejemplo` | `maestro_empleado` | CODIGO, NOMBRE, DOCUMENTO, CARGO |
| `horas_cargos` | `maestro_cargo` | id_cargo, cargo, horas_dia, horas_semana |
| `horarios` | `maestro_horario` | id_horario, hora_inicio, hora_fin |
| `cargos_horarios` | `maestro_cargo_horario` | id_cargo, id_horario |
| `conceptos` | `maestro_concepto` | observaciones, procesos |

```bash
python manage.py cargar_maestro                        # carga normal
python manage.py cargar_maestro --limpiar              # borra todo y recarga
python manage.py cargar_maestro --ruta /otra/ruta.xlsx # ruta personalizada
```

## Archivo de Salida (Excel)

| Columna | Descripción |
|---------|-------------|
| CODIGO COLABORADOR | ID del empleado (del huellero) |
| NOMBRE COMPLETO DEL COLABORADOR | Nombre completo |
| DOCUMENTO DEL COLABORADOR | Cédula (tomada de `maestro_empleado`) |
| FECHA | Fecha del turno (DD/MM/YYYY) |
| DIA | Día de la semana |
| # MARCACIONES AM | Marcaciones 06:00–11:59 |
| # MARCACIONES PM | Marcaciones 12:00–23:59 |
| HORA DE INGRESO | Hora de entrada |
| HORA DE SALIDA | Hora de salida |
| TOTAL HORAS LABORADAS | Horas trabajadas |
| OBSERVACION | Códigos automáticos de alerta |

## Tipos de Observaciones

| Código | Significado |
|--------|-------------|
| `OK` | Turno completo sin problemas |
| `TURNO_NOCTURNO` | Entrada ≥ 20:00, salida en madrugada |
| `SALIDA_NR` | Salida no registrada |
| `ENTRADA_NR` | Entrada no registrada |
| `ESTADO_INFERIDO` | Estado deducido por contexto |
| `DUPLICADOS_ELIM` | Marcaciones duplicadas eliminadas |
| `TURNO_LARGO` | Más de 16 horas |
| `TURNO_CORTO` | Menos de 4 horas |
| `EXCEDE_JORNADA` | Supera límite de horas del cargo (9.8h) |
| `TRABAJO_DOMINICAL` | Turno en domingo |
| `SIN_REGISTROS` | Día sin marcaciones (entre primer y último registro) |

## Variables de Entorno

Ver `web/.env.example` para la lista completa. Las principales:

```env
DEBUG=True
SECRET_KEY=...
DATABASE_URL=...                        # PostgreSQL en producción
GOOGLE_CREDENTIALS_JSON=...            # Credenciales Google Sheets (producción)
GOOGLE_CREDENTIALS_FILE=credentials/nomina.json  # Alternativa local
GOOGLE_SHEET_ID=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...                # App Password de Google (16 chars)
WEBHOOK_SECRET_TOKEN=...
```

## Despliegue (Railway)

El despliegue es automático vía git push. Railway ejecuta:
1. `python manage.py migrate`
2. `python manage.py collectstatic`
3. `gunicorn huellero_web.wsgi`

---
**Uso interno — Corporación Hacia un Valle Solidario**
