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

There is no test suite. Testing is done manually by processing files.

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
- **nomina_cali_service.py** — Generates daily records for manipuladoras with schedules from `HORARIOS` sheet.
- **liquidacion_nomina_service.py** — Crosses `nomina_cali` + `facturacion` to generate payroll liquidation aggregated by sede.
- **email_service.py** — Sends email notifications via Gmail with liquidation reports.

#### Google Sheets Structure

The system reads/writes to a Google Sheets workbook with these sheets:

| Sheet | Purpose |
|-------|---------|
| `Sedes` | Master list of sedes with ration quotas |
| `Manipuladoras` | Employee list with Estado (activo/inactivo), sede, supervisor |
| `HORARIOS` | Work schedules per sede (some sedes have multiple shifts) |
| `sedes_supevisor` | Supervisor-sede assignments with email |
| `facturacion` | Daily ration records per sede (generated at 8 AM) |
| `nomina_cali` | Daily manipuladora records with hours (generated at 8 AM) |
| `liquidacion_nomina` | Aggregated payroll by sede (generated at 10 PM) |

#### Daily Workflow

1. **8:00 AM** — `facturacion_diaria` and `nomina_cali_diaria` create default records
2. **During day** — Supervisors edit via AppSheet, mark NOVEDAD=SI for changes
3. **10:00 PM** — `liquidacion_nomina_diaria` crosses data, generates liquidation, sends email

#### Views (`views.py`)

Uses `_obtener_datos_filtrados()` helper function for common filtering logic:
- Filters by supervisor, sede, mes (month)
- Reads from Google Sheets dynamically
- Processes rows with custom transformers

### Templates Structure (`web/templates/`)

```
templates/
├── base.html                    # Base template with container and footer
├── users/
│   └── login.html              # Login form
├── logistica/
│   └── index.html              # File upload interface
└── tecnicos/
    ├── index.html              # Supervisión dashboard
    ├── liquidacion_nomina.html # Liquidación view with stats
    ├── nomina_cali.html        # Nómina Cali view
    └── facturacion.html        # Facturación view
```

### Static Files (`web/static/`)

```
static/
├── css/
│   ├── styles.css       # Global styles (logística, login)
│   └── supervision.css  # Supervisión module styles
└── js/
    └── app.js           # Logística file upload logic
```

**Important:** Keep CSS/JS separate from HTML templates. Use `{% static 'css/...' %}` in templates.

### Configuration (`config.py`)

All thresholds, time ranges, feature flags, directory paths, and format strings are centralized here. Key settings:
- `UMBRAL_DUPLICADOS` (900s / 15 min) — duplicate detection window, keeps LAST record
- `RANGO_INFERENCIA_ENTRADA` / `RANGO_INFERENCIA_SALIDA` — hour ranges for time-based state inference
- `HORA_INICIO_TURNO_NOCTURNO` (15.5 / 15:30) — nocturnal shift detection threshold
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
- Some sedes in HORARIOS have multiple shifts (AM/PM). Currently `nomina_cali_service` takes only the first schedule found per sede.
