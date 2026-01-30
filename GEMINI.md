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
-   **`Calculator`**: Computes hours worked. **Feature**: Automatically splits night shifts crossing midnight into two records to respect calendar days in final reports.
-   **`ExcelGenerator`**: Produces the final Excel reports and "Special Cases" logs.
-   **`logger`**: Centralized logging utility.

### Interfaces
-   **CLI (`main.py`)**: Entry point for local execution. Direct invocation of `src` modules.
-   **Web (`web/`)**: A Django project serving a UI.
    -   **`apps.logistica`**: Handles file uploads and calls `src` logic via `HuelleroProcessor`.
    -   **`apps.tecnicos`**: Handles automated reports (Nómina Cali, Facturación) and AppSheet integrations.
        -   Includes `webhooks.py` for external notifications.
        -   Includes `cron.py` for scheduled automation.
    -   **`apps.users`**: Manages authentication.

## Directory Structure

```text
huellero_processor/
├── main.py               # CLI Entry point
├── config.py             # Global configuration (thresholds, shifts)
├── init_sheets_headers.py # Utility to initialize Google Sheets headers
├── src/                  # Shared Core Logic
├── web/                  # Django Web Application
│   ├── manage.py         # Django CLI
│   ├── huellero_web/     # Project settings
│   └── apps/             # Django Apps (logistica, tecnicos, users)
├── data/                 # Data storage (Git-ignored content)
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
    ```bash
    pip install -r requirements.txt       # Core dependencies
    pip install -r web/requirements.txt   # Web dependencies
    ```

### Google Sheets Sync
Before running the web app automation, initialize the headers in your Google Spreadsheet:
```bash
python init_sheets_headers.py
```

## Usage

### 1. Web Mode (Django)
Run the web server for a UI-based experience and automation.
```bash
cd web
python manage.py runserver
```
Access at: `http://127.0.0.1:8000/`

### 2. AppSheet Integration
The web app is ready to receive webhooks from AppSheet at:
`/supervision/api/webhook/novedad-nomina/`

Ensure `WEBHOOK_SECRET_TOKEN` is configured in your `.env` file.

## Configuration
*   **Core Logic:** Modified in `config.py` (root).
*   **Web Settings:** Modified in `web/huellero_web/settings.py`.
*   **Daily Tasks:** Automated via Cron endpoints in the `tecnicos` app.

## Development Workflow
*   **Logic Changes:** modifying `src/` affects BOTH the CLI and Web app.
*   **Refactoring:** The `tecnicos` app is modularized into `views.py` (UI), `webhooks.py` (API), and `cron.py` (Automation).
*   **Data Integrity:** All automated records must include a unique `ID` column.