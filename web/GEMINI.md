# Huellero Processor (Web Interface)

## Project Overview
This project is the web interface for **Huellero Processor**, a tool developed for **Corporación Hacia un Valle Solidario (CHVS)**. It processes employee time tracking logs ("huellero") to generate attendance reports, calculate shifts, and produce statistics.

The application is built with **Django** and serves as the frontend and API layer for the core processing logic.

## Architecture

### Directory Structure
- **`huellero_web/`**: Main Django configuration (`settings.py`, `urls.py`, `wsgi.py`).
- **`apps/`**: Django applications.
    - **`logistica/`**: Main business domain. Handles file uploads and invokes the processing logic.
    - **`tecnicos/`**: Handles specialized technical reports and integrations (Google Sheets, Facturación, Nómina).
        - `views.py`: Shared utilities and Index view.
        - `views_liquidacion.py`: Logic for Liquidación Nómina.
        - `views_nomina.py`: Logic for Nómina Cali (Audit tool).
        - `views_facturacion.py`: Logic for Facturación.
        - `webhooks.py`: Handles AppSheet notifications.
        - `cron.py`: Handles scheduled tasks (daily automation).
    - **`users/`**: User authentication and management (login/logout).
- **`templates/`**: HTML templates (Django Template Language).
- **`static/`**: Static assets (CSS, JS, images).
- **`manage.py`**: Django command-line utility.

### Core Processing Logic (External)
The core processing logic resides in a `src/` directory located in the **parent directory** of this web project.

**Key Features:**
- **Split Night Shifts**: The `Calculator` automatically detects shifts crossing midnight and splits them into two records (one until 00:00 and another starting at 00:00) to respect calendar days in reports.
- **DataCleaner**: Cleans raw input data.
- **StateInference**: Infers employee states (Entry/Exit).
- **ShiftBuilder**: Constructs shifts from states.
- `logger`: Custom logging utility.

## Configuration (`huellero_web/settings.py`)

The project is configured to run in both local development and production (Railway) environments.

- **Environment Variables**: Managed via `os.environ`. See `.env.example` for required keys.
- **Database**:
    - **Development**: SQLite (`db.sqlite3`).
    - **Production**: PostgreSQL (via `DATABASE_URL`).

## Integrations

### Google Sheets
The `tecnicos` app integrates with Google Sheets to read and write report data.
- **Multi-Sede Architecture**: Managed via `apps.tecnicos.constantes.py`. 
    - **Cali**: Uses `GOOGLE_SHEET_ID`.
    - **Yumbo**: Uses `GOOGLE_SHEET_ID_YUMBO`.
- **Service**: `apps.tecnicos.google_sheets.GoogleSheetsService`
- **Mandatory IDs**: All automated records (Nómina, Facturación) now include a unique ID (e.g., `NOM-YYYYMMDD-####`) to ensure data integrity and traceability.
- **Header Management**: Use `init_sheets_headers.py` (root) to synchronize Google Sheets columns with the system's expected structure for all configured sedes.

### AppSheet Webhooks
The system exposes webhooks to receive real-time updates from AppSheet applications.
- **Endpoint**: `/supervision/api/webhook/novedad-nomina/`
- **Dynamic Routing**: Supports a `?sede=YUMBO` query parameter to route novedades to the correct Google Spreadsheet.
- **Function**: Receives updates when a "Novedad" is marked as "SI" in AppSheet.
- **Security**: Protected by a shared secret token (`WEBHOOK_SECRET_TOKEN`).
- **Action**: Automatically creates/updates the `novedades_cali` sheet in the connected Google Spreadsheet.

### Novedades Cali Persistence Logic
The daily automation (`nomina_cali_diaria`) includes an intelligent persistence layer for employee novelties:
- **Active Range Detection**: For every employee, the system checks the `novedades_cali` sheet. If the current processing date falls between the novelty's `FECHA` and `FECHA FINAL`, the novelty is considered **Active**.
- **Automated Record Modification**:
    - **Total Hours**: Automatically set to **0** for the duration of the novelty.
    - **Type**: Inherits the `TIPO TIEMPO LABORADO` from the novelty (e.g., *INCAPACIDAD*, *DIAS NO CLASE*, *ACCIDENTE LABORAL*, *PERMISO NO REMUNERADO*).
    - **Status**: Sets `NOVEDAD` to `SI` and carries over the `FECHA FINAL` and `OBSERVACIONES`.
- **Normalization Engine (Data Integrity)**: To prevent matching failures due to formatting, the system implements a robust normalization layer that strips dots, commas, and spaces from Cédulas/IDs. This ensures perfect synchronization between the Master sheet (`Manipuladoras`) and AppSheet novelty reports.
- **Auto-Reversion**: Once the current date exceeds the `FECHA FINAL`, the system automatically reverts the employee to their standard shift and `P. ALIMENTOS` status without human intervention.

### Shift Assignment & Rotation Logic
The system implements a triple-layer logic for daily shift assignment to handle complex staffing scenarios:
1.  **Exclusion Rule (Master Status)**: Any employee with `Estado` set to `Incapacitada` or any status other than `Activo` in the **Manipuladoras** sheet is automatically excluded from the daily generation process.
2.  **Priority 1: Fixed Shift**: The system checks the `TURNOS` column in the **Manipuladoras** sheet. If a specific shift (e.g., "A", "B") is assigned, that schedule is used every day, overriding any rotation. This is used for employees with fixed schedules in multi-shift locations.
3.  **Priority 2: Automatic Rotation**: If the `TURNOS` column is empty, the system applies a rotational formula: `(DayOfWeek + EmployeeIndex) % TotalShifts`. This ensures fair distribution of morning/afternoon shifts across the staff in the same location.
4.  **Saturday Rule**: Saturdays are always generated with empty hours by default, regardless of the assigned shift or rotation.

### Web Interface & Auditor Tool
The **Nómina** module (`/tecnicos/nomina-cali/`) has been transformed into a powerful audit and diagnosis dashboard:
- **Location Selector**: Users can switch between Cali and Yumbo views.
- **Unified Monthly Data Map**: The backend fuses data from `nomina_cali`, `novedades_cali`, and `facturacion`. This creates a complete "Radiography" of the month for every employee.
- **Alphabetical Sorting**: All employee lists are automatically sorted by name for easier navigation.
- **Cross-Column Highlighting**: Hovering over an employee card in one column automatically highlights the corresponding card in the other column, facilitating side-by-side comparison.
- **Sede-Based Team View**: Clicking on an employee name opens a comprehensive team panel.
    - **Contextual View**: Instead of just one person, it displays the full team belonging to that same Sede.
    - **Comparative Timelines**: Multiple horizontal timelines allow coordinators to compare shifts and novelties across the entire local staff simultaneously.
- **One-Click Audit**: Clicking on any name in the novelty lists instantly populates the team timeline, allowing coordinators to verify if reported novelties from AppSheet have been correctly reflected in the payroll records.
- **Dynamic Accuracy Engine**: Total hours and Worked Days are recalculated in real-time by the frontend, ensuring the "Stats Badges" are 100% consistent with the visual timeline blocks.
- **Schedule Cross-Reference**: Novelty cards display the **Official Sede Schedule** (from the HORARIOS sheet) in the top-right corner, allowing immediate contrast with the reported novelty hours at the bottom.

### Web Interface Improvements (Audit & Traceability)
The **Nómina Cali** module (`/tecnicos/nomina-cali/`) has been upgraded to serve as a comprehensive audit tool:
- **Unified Data Map**: The backend now fuses data from three sources (`nomina_cali`, `novedades_cali`, `facturacion`) into a single Master JSON object injected into the frontend. 
- **Normalization Layer**: Strict normalization of Cédulas (stripping dots, commas, and spaces) ensures that records from different sheets are perfectly merged into a single employee profile.
- **Interactive Detail Panel**: A new bottom section allows coordinators to click on any employee name to reveal their full monthly history within their team context.
    - **Visual Timeline**: A compact, 31-day horizontal grid showing Worked Days (Green), Novelties (Yellow), and Mixed status (Blue with ⚠️ icon).
    - **Compact Design**: Optimized vertical space with low-height bars (18px) and zoom-on-hover for maximum information density without scrolling.
- **Goal**: To transform the view from a simple list into a traceability tool, allowing coordinators to instantly verify if an AppSheet report has been correctly processed into the daily payroll records and how it affects the sede's overall staffing.

## Setup & Usage

### 1. Environment Setup
Create a `.env` file in this directory based on `.env.example`:
```bash
cp .env.example .env
```
Ensure `DJANGO_ENV=development` and `DEBUG=True` for local work.

### 2. Database Migration
Initialize or update the database schema:
```bash
python manage.py migrate
```

### 3. Google Sheets Initialization
Run the initialization script to ensure all sheets have the correct headers (including the `ID` column):
```bash
python init_sheets_headers.py
```

### 4. Run Development Server
Start the local server:
```bash
python manage.py runserver
```

## Key Workflows
1.  **Login**: Users authenticate via `apps.users`.
2.  **Upload (Logística)**: Users upload a raw "huellero" file.
3.  **Process**:
    - `HuelleroProcessor` orchestrates the cleaning, inference, and calculation steps.
    - **Note**: Night shifts are automatically split for day-to-day reporting.
4.  **Download**: The processed Excel file is generated in `data/output`.
5.  **Supervision/Tecnicos**:
    - View reports from Google Sheets.
    - Receive webhooks from AppSheet for instant "Novedad" reporting.
    - Automated daily tasks via Cron endpoints.

### Web Interface Improvements (Audit & Traceability)
The **Nómina Cali** module (`/tecnicos/nomina-cali/`) has been upgraded to serve as a comprehensive audit tool:
- **Unified Data Map**: The backend now fuses data from three sources (`nomina_cali`, `novedades_cali`, `facturacion`) into a single Master JSON object injected into the frontend. This ensures complete visibility of an employee's status regardless of the source.
- **Interactive Detail Panel**: A new bottom section allows coordinators to click on any employee name to reveal their full monthly history.
    - **Visual Timeline**: A 31-day horizontal grid showing Worked Days (Green), Novelties (Yellow), and Absences.
    - **Instant Summary**: Real-time calculation of Total Hours and Days Worked based on the processed data.
- **Goal**: To transform the view from a simple list into a traceability tool, allowing coordinators to instantly verify if an AppSheet report has been correctly processed into the daily payroll records.

## Deployment (Railway)
The project is optimized for Railway.app.
- `CSRF_TRUSTED_ORIGINS` and `ALLOWED_HOSTS` are automatically configured if `DJANGO_ENV=production`.
- Ensure `WEBHOOK_SECRET_TOKEN` is set in Railway environment variables for AppSheet integration.
