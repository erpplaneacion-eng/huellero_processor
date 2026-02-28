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

### Logística Management Commands

```bash
cd web

# Load employee master data from Excel into PostgreSQL
# Reads from data/maestro/empleados.xlsx (sheets: empleados_ejemplo, horas_cargos, horarios, cargos_horarios, conceptos)
python manage.py cargar_maestro
```

### Nómina Management Commands

```bash
cd web

# Generate daily facturacion records (run at 8 AM)
python manage.py facturacion_diaria [--fecha YYYY-MM-DD] [--forzar]

# Generate daily nomina_cali records (run at 8 AM)
python manage.py nomina_cali_diaria [--fecha YYYY-MM-DD] [--forzar] [--sede CALI|YUMBO]

# Generate liquidacion_nomina crossing nomina_cali + facturacion (run at 10 PM)
# Also sends email notification to coordinator
python manage.py liquidacion_nomina_diaria [--fecha YYYY-MM-DD] [--forzar] [--sin-email] [--sede CALI|YUMBO]
```

Omitting `--sede` runs both CALI and YUMBO sequentially.

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

Test classes: `ParsearHorasFormatoTest`, `SafeFloatTest`, `ParsearHoraTest`, `CalculoMetricasLiquidacionTest`, `NominaCaliFiltroDiasTest`, `ParsearFechaTest`.

## Architecture

### Core Pipeline

The system is a 5-phase sequential pipeline defined in `main.py`:

```
Input Excel → DataCleaner → StateInference → ShiftBuilder → Calculator → ExcelGenerator → Output Excel
```

### Module responsibilities (`src/`)

- **data_cleaner.py** — Loads Excel, standardizes columns (ID→CODIGO, Nombre→NOMBRE, Fecha/Hora→FECHA_HORA, Estado→ESTADO), converts types, removes duplicate records within 15 minutes keeping the LAST record of each group.
- **state_inference.py** — Fills missing Entrada/Salida states using three methods in order: time-range heuristics, context from adjacent records, and employee historical patterns. Falls back to `INDEFINIDO`.
- **shift_builder.py** — Pairs entry/exit records into shifts per employee per day. Handles nocturnal shifts (entry ≥20:00, exit next morning before 10:00) by assigning to the entry date. Post-processes incomplete PM entries as `nocturno_prospectivo` by pairing them with AM records from the next day. Produces complete and incomplete shift records.
- **calculator.py** — Counts AM/PM clock-ins, generates observation codes (OK, TURNO_NOCTURNO, SALIDA_NR, TURNO_LARGO, TRABAJO_DOMINICAL, etc.), and optionally merges employee master data (DOCUMENTO field) from `data/maestro/`. Also calls `rellenar_dias_faltantes()` to insert `SIN_REGISTROS` rows for days between an employee's first and last record that have no attendance. Nocturnal shifts crossing midnight are split into two rows.
- **excel_generator.py** — Writes the 14-column report with color-coded rows (green=OK, blue=nocturnal, purple=salida_estandar_nocturna, yellow=minor, orange=alert, gray=sin_registros), frozen headers, and a summary sheet. Also generates a separate `CASOS_REVISION_*.xlsx` for records needing manual review.
- **logger.py** — Dual-output logging (file + console) with statistics tracking across all phases.

### Django Web App (`web/`)

Browser-based interface for file upload and processing. Deployed to Railway.

#### Apps Structure

- **apps/users/** — Authentication with role-based access (Logística, Supervisión, Admin, etc.). Users with area "supervision" are redirected to `/supervision/`.
- **apps/logistica/** — File upload UI, processing API, and PostgreSQL models. Uses `processor.py` to wrap the core pipeline. Maestro data is loaded from DB (not Excel) in the web context.
- **apps/tecnicos/** — Nómina management module with Google Sheets integration. Accessible via `/supervision/` URL.
- **huellero_web/settings.py** — Django config with Railway deployment support, PostgreSQL in production, SQLite in development.

#### PostgreSQL Models (`apps/logistica/models.py`)

| Model | DB Table | Purpose |
|-------|----------|---------|
| `Cargo` | `maestro_cargo` | Job positions with `horas_dia`/`horas_semana` limits |
| `Horario` | `maestro_horario` | Time ranges with `hora_inicio`/`hora_fin` |
| `CargoHorario` | `maestro_cargo_horario` | Many-to-many: Cargo ↔ Horario (unique_together) |
| `Empleado` | `maestro_empleado` | Employees with `codigo`, `documento`, FK to `Cargo`, `excluido` flag |
| `RegistroAsistencia` | `registro_asistencia` | Processed attendance rows; unique_together `(codigo, fecha, hora_ingreso)` |
| `Concepto` | `maestro_concepto` | Dropdown values for manual `OBSERVACIONES_1` field |

`Empleado.excluido=True` removes the employee entirely from huellero analysis.

`processor.py` loads data from these models via `_cargar_maestro_desde_db()`, `_cargar_horarios_por_codigo()`, and `_cargar_codigos_excluidos()` — the web context never reads Excel maestro files.

#### Key Endpoints

**Logística (`/logistica/`):**
- `/logistica/` — Main dashboard (requires login)
- `/logistica/api/procesar/` — POST: process uploaded huellero Excel; returns `{datos, conceptos, stats, db_stats, archivo, archivo_casos}`
- `/logistica/api/registros/` — GET: list all saved attendance records from DB (same format as procesar response, `desde_db: true`)
- `/logistica/api/registros/obs1/` — POST `{registro_id, obs1}`: save manual observation to `RegistroAsistencia.observaciones_1`
- `/logistica/api/descargar/<filename>/` — Download generated reports

**Supervisión (`/supervision/`):**
- `/supervision/` — Dashboard with module links
- `/supervision/liquidacion-nomina/` — View liquidacion_nomina Google Sheet
- `/supervision/nomina-cali/` — View nomina_cali Google Sheet with hour calculations
- `/supervision/facturacion/` — View facturacion Google Sheet

### App Tecnicos (`web/apps/tecnicos/`)

Manages payroll data through Google Sheets integration.

#### Services

- **constantes.py** — `SEDES` dict (CALI/YUMBO config with env var names) and helpers `obtener_id_hoja(sede_key)` / `obtener_nombre_sede(sede_key)`. All services and views import the sheet ID from here.
- **google_sheets.py** — Connection service for Google Sheets API using gspread. Requires `credentials/nomina.json` service account file.
- **facturacion_service.py** — Generates daily ration records per sede. Creates records in `facturacion` sheet.
- **nomina_cali_service.py** — Generates daily records for manipuladoras with schedules from `HORARIOS` sheet. Supports multiple shifts per sede with automatic rotation. Instantiated with `NominaCaliService(sede='CALI'|'YUMBO')`.
- **liquidacion_nomina_service.py** — Crosses `nomina_cali` + `facturacion` to generate payroll liquidation aggregated by sede. Instantiated with `LiquidacionNominaService(sede='CALI'|'YUMBO')`.
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

#### Views (split across multiple files)

Views are split into focused modules; all import shared helpers from `views.py`:
- **views.py** — Shared utilities only: `_parsear_hora`, `_safe_float`, `_parsear_fecha`, `_parsear_horas_formato`, `_calcular_horas_desde_rango`, `_obtener_datos_filtrados`, `_obtener_novedades_hoja`, and `MESES` constant.
- **views_facturacion.py** — `facturacion()` view.
- **views_liquidacion.py** — `liquidacion_nomina()` view.
- **views_nomina.py** — `nomina_cali()` view.

`_obtener_datos_filtrados()` is the common filtering helper:
- Filters by supervisor, sede, mes (month)
- Reads from Google Sheets dynamically
- Processes rows with custom transformers
- **Header normalization:** Column names are normalized (uppercase, no spaces/underscores) for matching. Custom row processors must normalize column names when accessing `headers_dict`.

**Liquidación Nómina Metrics:**
- Días Nómina: Count of records with `TOTAL HORAS > 0`
- Días Raciones: Count of records with `TOTAL RACIONES > 0`
- Inconsistencias: Records with hours but no rations OR rations but no hours

**Nómina Cali Features (`/supervision/nomina-cali/`):**

Accepts a `?ubicacion=CALI|YUMBO` query parameter (default: CALI) to switch between Google Sheets workbooks via `obtener_id_hoja()`.

The view displays a 3-column layout for auditing and cross-referencing:

| Column | Source | Purpose |
|--------|--------|---------|
| Left: "Nómina al día" | `nomina_cali` (NOVEDAD=SI) | Grouped novedades already processed in payroll |
| Center | Calendar | Visual day selection with color-coded status |
| Right: "Novedades Cali" | `novedades_cali` | Raw novedades from AppSheet webhook |

**Novedad Grouping (Left Column):**
Records from `nomina_cali` with `NOVEDAD=SI` are grouped by `(cedula, tipo_tiempo, observaciones)`. A 4-day incapacity shows as 1 card with date range instead of 4 separate cards.

**Collaborator Detail Panel:**
Clicking any collaborator name opens a bottom panel with:
- Monthly timeline (31 day boxes): green=worked, yellow=novedad, gray=no record
- Summary stats: días trabajados, total horas, días novedad
- Data comes from `asistencia_data` JSON passed to template via `json_script`

**Hour Calculation:**
Hours are calculated dynamically from `HORA_INICIAL` and `HORA_FINAL`, NOT from `TOTAL_HORAS` column:
- Backend: `_calcular_horas_desde_rango()` in views.py
- Frontend: `calcularDiferenciaHoras()` in nomina_cali.js
- Supports formats: `HH:MM`, `HH:MM:SS`, `5:30:00 a. m.`, `1:30:00 p. m.`
- Handles nocturnal shifts (when end time < start time, adds 24h)

**Types Without Hours (Left Column Only):**
These `TIPO TIEMPO LABORADO` values display 0 hours regardless of actual time:
- `DIAS NO CLASE`
- `NO ASISTENCIA`
- `PERMISO NO REMUNERADO`

This rule does NOT apply to the right column (novedades_cali).

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

**Hour Parsing Functions (`views.py`):**
- `_parsear_horas_formato()`: Converts "HH:MM" to decimal (e.g., "5:30" → 5.5)
- `_parsear_hora()`: Parses time strings to datetime objects
- `_parsear_hora_a_minutos()`: Parses hours to minutes, supports AM/PM formats like "5:30:00 a. m."
- `_calcular_horas_desde_rango()`: Calculates hour difference, handles nocturnal shifts

### Templates and Static Files

- Templates: `web/templates/{users,logistica,tecnicos}/` — Keep CSS/JS separate, use `{% static %}` tags
- Static CSS: `web/static/css/` (styles.css for logística, supervision.css for supervisión)
- Static JS: `web/static/js/app.js`, `web/static/js/nomina_cali.js`
- Key CSS patterns in supervision.css: `.stat-card--{info,success,danger,warning}`, `.sup-chip`, `.row-alert`, `.novedad-card`, `.timeline-dia`

**nomina_cali.js Functions:**
- `calcularHorasTarjetas()`: Calculates hours dynamically for cards with `.js-calc-horas` class
- `parsearHoraAMinutos()`: Parses hour strings including AM/PM formats
- `mostrarDetalle()`: Opens collaborator detail panel with timeline
- `hacerNombresClickeables()`: Makes collaborator names clickable

### Configuration (`config.py`)

All thresholds, time ranges, feature flags, directory paths, and format strings are centralized here. Key settings:
- `UMBRAL_DUPLICADOS` (900s / 15 min) — duplicate detection window, keeps LAST record
- `TOLERANCIA_HORARIO_MIN` (90 min) — max deviation from cargo schedule before falling back to global ranges
- `RANGO_INFERENCIA_ENTRADA` / `RANGO_INFERENCIA_SALIDA` — fallback hour ranges (03–11 / 14–21)
- `HORA_INICIO_TURNO_NOCTURNO` (20.0 / 20:00) — nocturnal shift detection threshold
- `HORAS_MINIMAS_TURNO` / `HORAS_MAXIMAS_TURNO` (4/16) — shift duration validation bounds
- `HORAS_LIMITE_JORNADA` (9.8) — maximum hours per workday, triggers `EXCEDE_JORNADA` observation
- Feature flags: `PERMITIR_INFERENCIA`, `ELIMINAR_DUPLICADOS_AUTO`, `GENERAR_HOJA_RESUMEN`, `GENERAR_CASOS_ESPECIALES`
- `VIGILANTE_CASTIGO_CODIGOS` — hardcoded employee codes `[4, 129, 130, 135]` for whom AM+PM marks on the same day are liquidated as a diurnal shift (punishment for wrong marking). Controlled by `VIGILANTE_CASTIGO_HABILITADO`.

### Environment Variables (`web/.env`)

```env
# Google Sheets
GOOGLE_CREDENTIALS_FILE=credentials/nomina.json   # local dev (file path)
GOOGLE_CREDENTIALS_JSON=<full-json-contents>       # production/Railway (env var takes precedence)
GOOGLE_SHEET_ID=<spreadsheet-id>                  # Cali sheet
GOOGLE_SHEET_ID_YUMBO=<spreadsheet-id>            # Yumbo sheet (optional)

# Django
DEBUG=True
SECRET_KEY=<secret-key>
ALLOWED_HOSTS=<comma-separated-domains>

# Email Gmail (notifications)
EMAIL_HOST_USER=<gmail-address>
EMAIL_HOST_PASSWORD=<app-password-16-chars>       # Google App Password, NOT regular Gmail password
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

