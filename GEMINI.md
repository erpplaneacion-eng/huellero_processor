# Huellero Processor

## Project Overview
**Huellero Processor** is a comprehensive system designed to process biometric time tracking logs ("huellero") for **Corporación Hacia un Valle Solidario (CHVS)**. It automates the cleaning of duplicate entries, infers missing entry/exit states, constructs shifts, and calculates work hours to generate professional Excel reports.

The project operates as a hybrid application:
1.  **CLI Utility:** For local, direct file processing.
2.  **Web Application:** A Django-based interface for user-friendly interaction and deployment.

## Architecture

The system is built around a shared core logic library (`src/`) utilized by both the CLI and Web interfaces.

### Core Logic (`src/`)
Located in the project root, this directory contains the business logic modules:
-   **`DataCleaner`**: Removes duplicate biometric scans.
-   **`StateInference`**: Infers whether a scan is an "Entry" or "Exit" based on context.
-   **`ShiftBuilder`**: Groups scans into logical work shifts.
-   **`Calculator`**: Computes hours worked (regular, night shifts) and identifies anomalies.
-   **`ExcelGenerator`**: Produces the final Excel reports and "Special Cases" logs.
-   **`logger`**: Centralized logging utility.

### Interfaces
-   **CLI (`main.py`)**: Entry point for local execution. Direct invocation of `src` modules.
-   **Web (`web/`)**: A Django project serving a UI.
    -   **`apps.logistica`**: Handles file uploads and calls `src` logic via `HuelleroProcessor`.
    -   **`apps.users`**: Manages authentication.

## Directory Structure

```text
huellero_processor/
├── main.py               # CLI Entry point
├── config.py             # Global configuration (thresholds, shifts)
├── src/                  # Shared Core Logic
├── web/                  # Django Web Application
│   ├── manage.py         # Django CLI
│   ├── huellero_web/     # Project settings
│   └── apps/             # Django Apps (logistica, users)
├── data/                 # Data storage (Git-ignored content)
│   ├── input/            # Raw .xls files
│   ├── output/           # Processed .xlsx reports
│   └── maestro/          # Employee master list (empleados.xlsx)
├── logs/                 # Processing logs
└── railway.json          # Deployment configuration
```

## Setup & Installation

### Prerequisites
-   Python 3.8+
-   `pip`

### Installation
1.  **Clone the repository.**
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    The project has dependencies for the core logic and the web app.
    ```bash
    pip install -r requirements.txt       # Core dependencies
    pip install -r web/requirements.txt   # Web dependencies
    ```
    *(Note: `web/requirements.txt` likely includes the root `requirements.txt` content or specific web packages).*

## Usage

### 1. CLI Mode (Local)
Run the processor directly from the terminal.

*   **Basic Usage:**
    Place raw files in `data/input/` and run:
    ```bash
    python main.py
    ```
*   **With Master File:**
    Ensure `data/maestro/empleados.xlsx` exists and run:
    ```bash
    python main.py --con-maestro
    ```
*   **Interactive Mode:**
    ```bash
    python main.py --interactivo
    ```

### 2. Web Mode (Django)
Run the web server for a UI-based experience.

*   **Development Server:**
    ```bash
    cd web
    python manage.py runserver
    ```
    Access at: `http://127.0.0.1:8000/`

*   **User Management:**
    Create an admin user to access the backend:
    ```bash
    cd web
    python manage.py createsuperuser
    ```

## Configuration

*   **Processing Rules:** Modified in `config.py` (root). Adjust time thresholds, shift boundaries, and Excel formatting here.
*   **Web Settings:** Modified in `web/huellero_web/settings.py`. Handles database connections, security, and static files.
    *   **Environment Variables:** Use a `.env` file in `web/` for secrets (see `web/.env.example`).

## Deployment

The application is configured for **Railway** deployment.

*   **Configuration:** `railway.json` and `Procfile`.
*   **Build System:** Nixpacks (defined in `railway.json`).
*   **Start Command:**
    ```bash
    cd web && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn huellero_web.wsgi --bind 0.0.0.0:$PORT
    ```
*   **Environment:** Expects `DJANGO_ENV=production` for production security settings.

## Development Workflow
*   **Logic Changes:** modifying `src/` affects BOTH the CLI and Web app immediately.
*   **Web Changes:** UI/UX changes are made in `web/templates` and `web/static`.
*   **Testing:**
    *   Run CLI manually with sample data in `data/input`.
    *   Run Web app locally and upload sample data.
