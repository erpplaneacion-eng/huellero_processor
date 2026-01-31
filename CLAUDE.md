# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Huellero Processor is a Python data pipeline that transforms raw biometric fingerprint reader (huellero) attendance Excel files into clean, formatted attendance reports. Built for Corporación Hacia un Valle Solidario (CHVS). All user-facing text is in Spanish.

## Commands

### CLI (main processor)

```bash
# Install dependencies
pip install -r requirements.txt

# Run (auto-detects newest file in data/input/)
python main.py

# Run with specific file
python main.py --archivo path/to/file.xls

# Run without employee master file
python main.py --sin-maestro

# Interactive mode (file selection prompt)
python main.py --interactivo
```

### Django Web Interface

```bash
cd web

# Install web dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Nómina Management Commands

```bash
cd web

# Generate daily facturacion records (run at 8 AM)
python manage.py facturacion_diaria [--fecha YYYY-MM-DD] [--forzar]

# Generate daily nomina_cali records (run at 8 AM)
python manage.py nomina_cali_diaria [--fecha YYYY-MM-DD] [--forzar]

# Generate liquidacion_nomina crossing nomina_cali + facturacion (run at 10 PM)
# Also sends email notification to coordinator
python manage.py liquidacion_nomina_diaria [--fecha YYYY-MM-DD] [--forzar] [--sin-email]
```

### Cron HTTP Endpoints (for Railway/external schedulers)

Token authentication via query param `?token=<WEBHOOK_SECRET_TOKEN>` or header `Authorization: Bearer <token>`.

```bash
# Facturacion diaria
GET/POST /supervision/cron/facturacion/?token=<token>

# Nomina Cali diaria
GET/POST /supervision/cron/nomina-cali/?token=<token>

# Liquidacion diaria (add ?sin_email=1 to skip email)
GET/POST /supervision/cron/liquidacion/?token=<token>
```

### Google Sheets Initialization

```bash
# Initialize/sync Google Sheets headers (run once or after schema changes)
python init_sheets_headers.py
```

### Running Tests

```bash
cd web

# Run all tests
python manage.py test

# Run tecnicos app tests (metrics calculations)
python manage.py test apps.tecnicos.tests

# Run a single test class
python manage.py test apps.tecnicos.tests.ParsearHorasFormatoTest

# Run a single test method
python manage.py test apps.tecnicos.tests.ParsearHorasFormatoTest.test_formato_hhmm_simple
```

Test classes: `ParsearHorasFormatoTest`, `SafeFloatTest`, `ParsearHoraTest`, `CalculoMetricasLiquidacionTest`.

## Architecture

### Core Pipeline

The system is a 5-phase sequential pipeline defined in `main.py`:

```
Input Excel → DataCleaner → StateInference → ShiftBuilder → Calculator → ExcelGenerator → Output Excel
```

### Module responsibilities (`src/`)

- **data_cleaner.py** — Loads Excel, standardizes columns (ID→CODIGO, Nombre→NOMBRE, Fecha/Hora→FECHA_HORA, Estado→ESTADO), converts types, removes duplicate records within 15 minutes keeping the LAST record of each group.
- **state_inference.py** — Fills missing Entrada/Salida states using three methods in order: time-range heuristics, context from adjacent records, and employee historical patterns. Falls back to `INDEFINIDO`.
- **shift_builder.py** — Pairs entry/exit records into shifts per employee per day. Handles nocturnal shifts (entry ≥16:00, exit next morning before 10:00) by assigning to the entry date. Produces complete and incomplete shift records.
- **calculator.py** — Counts AM/PM clock-ins, generates observation codes (OK, TURNO_NOCTURNO, SALIDA_NR, TURNO_LARGO, TRABAJO_DOMINICAL, etc.), and optionally merges employee master data (DOCUMENTO field) from `data/maestro/`.
- **excel_generator.py** — Writes the 11-column report with color-coded rows (green=OK, blue=nocturnal, yellow=minor, orange=alert), frozen headers, and a summary sheet. Also generates a separate `CASOS_REVISION_*.xlsx` for records needing manual review.
- **logger.py** — Dual-output logging (file + console) with statistics tracking across all phases.

### Django Web App (`web/`)

Browser-based interface for file upload and processing. Deployed to Railway.

#### Apps Structure

- **apps/users/** — Authentication with role-based access (Logística, Supervisión, Admin, etc.). Users with area "supervision" are redirected to `/supervision/`.
- **apps/logistica/** — File upload UI and processing API. Uses `processor.py` to wrap the core pipeline.
- **apps/tecnicos/** — Nómina management module with Google Sheets integration. Accessible via `/supervision/` URL.
- **huellero_web/settings.py** — Django config with Railway deployment support, PostgreSQL in production, SQLite in development.

#### Key Endpoints

**Logística (`/logistica/`):**
- `/logistica/` — Main dashboard (requires login)
- `/logistica/api/procesar/` — POST endpoint for file processing
- `/logistica/api/descargar/<filename>/` — Download generated reports

**Supervisión (`/supervision/`):**
- `/supervision/` — Dashboard with module links
- `/supervision/liquidacion-nomina/` — View liquidacion_nomina Google Sheet
- `/supervision/nomina-cali/` — View nomina_cali Google Sheet with hour calculations
- `/supervision/facturacion/` — View facturacion Google Sheet

### App Tecnicos (`web/apps/tecnicos/`)

Manages payroll data through Google Sheets integration.

#### Services

- **google_sheets.py** — Connection service for Google Sheets API using gspread. Requires `credentials/nomina.json` service account file.
- **facturacion_service.py** — Generates daily ration records per sede. Creates records in `facturacion` sheet.
- **nomina_cali_service.py** — Generates daily records for manipuladoras with schedules from `HORARIOS` sheet. Supports multiple shifts per sede with automatic rotation.
- **liquidacion_nomina_service.py** — Crosses `nomina_cali` + `facturacion` to generate payroll liquidation aggregated by sede.
- **email_service.py** — Sends email notifications via Gmail SMTP. Reports include:
  - KPI summary cards (Total Sedes, Manipuladoras, Con Horas, Con Raciones, Inconsistencias)
  - Breakdown by supervisor with per-sede details (Manipuladoras, Horas, Raciones, Estado)
  - Color-coded status badges (OK/green, Inconsistencia/red, Novedad/yellow)
- **webhooks.py** — Handles AppSheet webhook for NOVEDAD notifications.
- **cron.py** — HTTP endpoints for external schedulers (Railway cron jobs).

#### Google Sheets Structure

The system reads/writes to a Google Sheets workbook with these sheets:

| Sheet | Purpose |
|-------|---------|
| `Sedes` | Master list of sedes with ration quotas |
| `Manipuladoras` | Employee list with Estado (activo/inactivo), sede, supervisor |
| `HORARIOS` | Work schedules per sede. Columns: INSTITUCION, SEDE, HORA ENTRADA, HORA SALIDA, TOTAL HORAS, TURNOS (A/B/C). 15 sedes have multiple shifts. |
| `sedes_supevisor` | Supervisor-sede assignments with email |
| `facturacion` | Daily ration records per sede (generated at 8 AM) |
| `nomina_cali` | Daily manipuladora records with hours (generated at 8 AM) |
| `liquidacion_nomina` | Aggregated payroll by sede (generated at 10 PM) |
| `novedades_cali` | Novedades received via webhook from AppSheet |

**nomina_cali columns (17):**
`ID, SUPERVISOR, user, MODALIDAD, DESCRIPCION PROYECTO, TIPO TIEMPO LABORADO, CEDULA, NOMBRE COLABORADOR, FECHA, DIA, HORA INICIAL, HORA FINAL, TOTAL_HORAS, NOVEDAD, FECHA FINAL, DIA FINAL, OBSERVACIONES`

**novedades_cali columns (18):**
`ID, FECHA_REGISTRO, SUPERVISOR, SEDE, TIPO TIEMPO LABORADO, CEDULA, NOMBRE_COLABORADOR, FECHA, DIA, HORA_INICIAL, HORA_FINAL, TOTAL_HORAS, FECHA FINAL, DIA FINAL, OBSERVACIONES, OBSERVACION, ESTADO, PROCESADO_POR`

#### Webhooks

- **`/supervision/api/webhook/novedad-nomina/`** — Receives AppSheet notifications when NOVEDAD=SI. Creates records in `novedades_cali` sheet. Requires `WEBHOOK_SECRET_TOKEN` in payload.

#### Daily Workflow

1. **8:00 AM** — `facturacion_diaria` and `nomina_cali_diaria` create default records
2. **During day** — Supervisors edit via AppSheet, mark NOVEDAD=SI for changes (triggers webhook)
3. **10:00 PM** — `liquidacion_nomina_diaria` crosses data, generates liquidation, sends email

#### Views (`views.py`)

Uses `_obtener_datos_filtrados()` helper function for common filtering logic:
- Filters by supervisor, sede, mes (month)
- Reads from Google Sheets dynamically
- Processes rows with custom transformers
- **Header normalization:** Column names are normalized (uppercase, no spaces/underscores) for matching. Custom row processors must normalize column names when accessing `headers_dict`.

**Liquidación Nómina Metrics:**
- Días Nómina: Count of records with `TOTAL HORAS > 0`
- Días Raciones: Count of records with `TOTAL RACIONES > 0`
- Inconsistencias: Records with hours but no rations OR rations but no hours

**Nómina Cali Features:**
- Calculates total hours from HORA INICIAL/HORA FINAL
- Shows supervisor chips with days reported per supervisor
- Handles nocturnal shifts (entry one day, exit next morning)

**Shift Rotation (Multiple Turnos):**

For sedes with multiple shifts and manipuladoras, the system rotates shifts using:
```
turno_index = (día_semana + índice_manipuladora) % cantidad_turnos
```

Example for sede with 2 shifts (A, B) and 3 manipuladoras:
| Manipuladora | Lun | Mar | Mié | Jue | Vie |
|--------------|-----|-----|-----|-----|-----|
| [0] María    |  A  |  B  |  A  |  B  |  A  |
| [1] Carmen   |  B  |  A  |  B  |  A  |  B  |
| [2] Rosa     |  A  |  B  |  A  |  B  |  A  |

5 sedes currently have both multiple shifts AND multiple manipuladoras.

**Hour Parsing:**
- `_parsear_horas_formato()`: Converts "HH:MM" to decimal (e.g., "5:30" → 5.5)
- `_parsear_hora()`: Parses time strings to datetime objects

### Templates and Static Files

- Templates: `web/templates/{users,logistica,tecnicos}/` — Keep CSS/JS separate, use `{% static %}` tags
- Static: `web/static/css/` (styles.css for logística, supervision.css for supervisión), `web/static/js/app.js`
- Key CSS patterns in supervision.css: `.stat-card--{info,success,danger,warning}`, `.sup-chip`, `.row-alert`

### Configuration (`config.py`)

All thresholds, time ranges, feature flags, directory paths, and format strings are centralized here. Key settings:
- `UMBRAL_DUPLICADOS` (900s / 15 min) — duplicate detection window, keeps LAST record
- `RANGO_INFERENCIA_ENTRADA` / `RANGO_INFERENCIA_SALIDA` — hour ranges for time-based state inference
- `HORA_INICIO_TURNO_NOCTURNO` (17.5 / 17:30) — nocturnal shift detection threshold
- `HORAS_MINIMAS_TURNO` / `HORAS_MAXIMAS_TURNO` (4/16) — shift duration validation bounds
- Feature flags: `PERMITIR_INFERENCIA`, `ELIMINAR_DUPLICADOS_AUTO`, `GENERAR_HOJA_RESUMEN`, `GENERAR_CASOS_ESPECIALES`

### Environment Variables (`web/.env`)

```env
# Google Sheets
GOOGLE_CREDENTIALS_FILE=credentials/nomina.json
GOOGLE_SHEET_ID=<spreadsheet-id>

# Django
DEBUG=True
SECRET_KEY=<secret-key>

# Email Gmail (notifications)
EMAIL_HOST_USER=<gmail-address>
EMAIL_HOST_PASSWORD=<app-password-16-chars>
EMAIL_COORDINADOR=<recipient-email>

# Webhooks & Cron authentication
WEBHOOK_SECRET_TOKEN=<secret-token>
```

### Data directories

- `data/input/` — Place source `.xls`/`.xlsx` files here
- `data/output/` — Generated reports land here
- `data/maestro/` — Optional employee master file (CODIGO, NOMBRE, DOCUMENTO, CARGO)
- `logs/` — Processing logs (`procesamiento_YYYYMMDD_HHMMSS.log`)
- `web/credentials/` — Google service account JSON file

## Key Implementation Details

- Input Excel header detection is flexible: scans rows to find the one containing "ID".
- Datetime format is `DD/MM/YYYY HH:MM` (Colombian convention).
- Observations are pipe-separated (`|`) when multiple apply to one shift.
- Nocturnal exit records (00:00–10:00) are paired with the previous day's entry and attributed to the entry date.
- The shift dict structure includes `es_nocturno`, `completo`, `entrada_inferida`, `salida_inferida`, `salida_corregida`, `nocturno_prospectivo` boolean flags.
- Dependencies: pandas, openpyxl, xlrd, XlsxWriter, python-dateutil, gspread, google-auth, whitenoise. Python 3.8+.
- 15 sedes in HORARIOS have multiple shifts (AM/PM). `nomina_cali_service` rotates shifts automatically per manipuladora and day.

## Recent Changes

- **Shift rotation**: Implemented automatic shift rotation for sedes with multiple turnos. Uses formula `(day + manip_index) % num_shifts` to distribute shifts fairly.
- Webhook integration added for external notifications (see git log for details)
