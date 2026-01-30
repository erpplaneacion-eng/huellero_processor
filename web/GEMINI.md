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
    - **`users/`**: User authentication and management (login/logout).
- **`templates/`**: HTML templates (Django Template Language).
- **`static/`**: Static assets (CSS, JS, images).
- **`manage.py`**: Django command-line utility.

### Core Processing Logic (External)
The core processing logic resides in a `src/` directory located in the **parent directory** of this web project. The Django application imports these modules dynamically in `settings.py` and `apps/logistica/processor.py`.

**Key Modules in `../src/` (Inferred):**
- `DataCleaner`: Cleans raw input data.
- `StateInference`: Infers employee states (Entry/Exit).
- `ShiftBuilder`: Constructs shifts from states.
- `Calculator`: Calculates hours and metrics.
- `ExcelGenerator`: Generates the final Excel reports.
- `logger`: Custom logging utility.

## Configuration (`huellero_web/settings.py`)

The project is configured to run in both local development and production (Railway) environments.

- **Environment Variables**: Managed via `os.environ`. See `.env.example` for required keys.
- **Database**:
    - **Development**: SQLite (`db.sqlite3`).
    - **Production**: PostgreSQL (via `DATABASE_URL`).
- **Static Files**: Served via `WhiteNoise`.
- **Allowed Hosts**: Configured to accept localhost and Railway domains.

## Integrations

### Google Sheets
The `tecnicos` app integrates with Google Sheets to read and write report data.
- **Service**: `apps.tecnicos.google_sheets.GoogleSheetsService`
- **Authentication**: Uses Service Account credentials (via file in dev, JSON env var in prod).

### AppSheet Webhooks
The system exposes webhooks to receive real-time updates from AppSheet applications.
- **Endpoint**: `/supervision/api/webhook/novedad-nomina/`
- **Function**: Receives updates when a "Novedad" is marked as "SI" in AppSheet.
- **Security**: Protected by a shared secret token (`WEBHOOK_SECRET_TOKEN`).
- **Action**: Automatically creates/updates the `novedades_cali` sheet in the connected Google Spreadsheet.

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

### 3. Run Development Server
Start the local server:
```bash
python manage.py runserver
```
Access the app at `http://127.0.0.1:8000/`.

### 4. User Management
Create a superuser to access the admin panel (`/admin`):
```bash
python manage.py createsuperuser
```

## Key Workflows
1.  **Login**: Users authenticate via `apps.users`.
2.  **Upload (Logística)**: Users upload a raw "huellero" file.
3.  **Process**:
    - The file is saved to `data/input` (in parent dir).
    - `HuelleroProcessor` (in `apps/logistica/processor.py`) orchestrates the cleaning, inference, and calculation steps using the `src` modules.
4.  **Download**: The processed Excel file is generated in `data/output` and served to the user.
5.  **Supervision/Tecnicos**:
    - View reports from Google Sheets (Facturación, Nómina Cali).
    - Receive webhooks from AppSheet for instant "Novedad" reporting.

## Deployment (Railway)
The project is optimized for Railway.app.
- `CSRF_TRUSTED_ORIGINS` and `ALLOWED_HOSTS` are automatically configured if `DJANGO_ENV=production`.