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
- **Service**: `apps.tecnicos.google_sheets.GoogleSheetsService`
- **Mandatory IDs**: All automated records (Nómina Cali, Facturación) now include a unique ID (e.g., `NOM-YYYYMMDD-####`) to ensure data integrity and traceability.
- **Header Management**: Use `init_sheets_headers.py` (root) to synchronize Google Sheets columns with the system's expected structure.

### AppSheet Webhooks
The system exposes webhooks to receive real-time updates from AppSheet applications.
- **Endpoint**: `/supervision/api/webhook/novedad-nomina/`
- **Function**: Receives updates when a "Novedad" is marked as "SI" in AppSheet.
- **Security**: Protected by a shared secret token (`WEBHOOK_SECRET_TOKEN`).
- **Action**: Automatically creates/updates the `novedades_cali` sheet in the connected Google Spreadsheet.

### Novedades Cali Persistence Logic
The daily automation (`nomina_cali_diaria`) includes an intelligent persistence layer for employee novelties:
- **Active Range Detection**: For every employee, the system checks the `novedades_cali` sheet. If the current processing date falls between the novelty's `FECHA` and `FECHA FINAL`, the novelty is considered **Active**.
- **Automated Record Modification**:
    - **Total Hours**: Automatically set to **0** for the duration of the novelty.
    - **Type**: Inherits the `TIPO TIEMPO LABORADO` from the novelty (e.g., *INCAPACIDAD*, *DIAS NO CLASE*).
    - **Status**: Sets `NOVEDAD` to `SI` and carries over the `FECHA FINAL` and `OBSERVACIONES`.
- **Normalization Engine**: Implements robust matching by stripping dots, commas, and spaces from Cédulas/IDs, ensuring synchronization even when data formats vary between the Master sheet and AppSheet inputs.
- **Auto-Reversion**: Once the current date exceeds the `FECHA FINAL`, the system automatically reverts the employee to their standard shift and `P. ALIMENTOS` status.

### Shift Assignment & Rotation Logic
The system implements a dual-layer logic for daily shift assignment:
1.  **Exclusion Rule**: Any employee with `Estado` set to `Incapacitada` in the **Manipuladoras** sheet is automatically excluded from the daily generation process, even if they were previously active.
2.  **Priority 1: Fixed Shift**: The system checks the `TURNOS` column in the **Manipuladoras** sheet. If a specific shift (e.g., "A", "B") is assigned to an employee, that specific schedule is used every day, overriding any rotation.
2.  **Priority 2: Automatic Rotation**: If the `TURNOS` column is empty, the system applies a rotational formula: `(DayOfWeek + EmployeeIndex) % TotalShifts`. This ensures fair distribution of morning/afternoon shifts across the staff in the same location.
3.  **Saturday Rule**: Regardless of the shift, Saturdays are generated with empty hours by default.

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

## Deployment (Railway)
The project is optimized for Railway.app.
- `CSRF_TRUSTED_ORIGINS` and `ALLOWED_HOSTS` are automatically configured if `DJANGO_ENV=production`.
- Ensure `WEBHOOK_SECRET_TOKEN` is set in Railway environment variables for AppSheet integration.
