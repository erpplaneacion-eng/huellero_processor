# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Huellero Processor is a Python data pipeline that transforms raw biometric fingerprint reader (huellero) attendance Excel files into clean, formatted attendance reports. Built for Corporación Hacia un Valle Solidario (CHVS). All user-facing text is in Spanish.

## Commands

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

There is no test suite. Testing is done manually by processing files.

## Architecture

The system is a 5-phase sequential pipeline defined in `main.py`:

```
Input Excel → DataCleaner → StateInference → ShiftBuilder → Calculator → ExcelGenerator → Output Excel
```

### Module responsibilities (`src/`)

- **data_cleaner.py** — Loads Excel, standardizes columns (ID→CODIGO, Nombre→NOMBRE, Fecha/Hora→FECHA_HORA, Estado→ESTADO), converts types, removes duplicate records within a configurable time threshold (default 120s).
- **state_inference.py** — Fills missing Entrada/Salida states using three methods in order: time-range heuristics, context from adjacent records, and employee historical patterns. Falls back to `INDEFINIDO`.
- **shift_builder.py** — Pairs entry/exit records into shifts per employee per day. Handles nocturnal shifts (entry ≥15:00, exit next morning before 10:00) by assigning to the entry date. Produces complete and incomplete shift records.
- **calculator.py** — Counts AM/PM clock-ins, generates observation codes (OK, TURNO_NOCTURNO, SALIDA_NR, TURNO_LARGO, TRABAJO_DOMINICAL, etc.), and optionally merges employee master data (DOCUMENTO field) from `data/maestro/`.
- **excel_generator.py** — Writes the 11-column report with color-coded rows (green=OK, blue=nocturnal, yellow=minor, orange=alert), frozen headers, and a summary sheet. Also generates a separate `CASOS_REVISION_*.xlsx` for records needing manual review.
- **logger.py** — Dual-output logging (file + console) with statistics tracking across all phases.

### Configuration (`config.py`)

All thresholds, time ranges, feature flags, directory paths, and format strings are centralized here. Key settings:
- `UMBRAL_DUPLICADOS` (120s) — duplicate detection window
- `RANGO_INFERENCIA_ENTRADA` / `RANGO_INFERENCIA_SALIDA` — hour ranges for time-based state inference
- `HORA_INICIO_TURNO_NOCTURNO` (15) — nocturnal shift detection threshold
- `HORAS_MINIMAS_TURNO` / `HORAS_MAXIMAS_TURNO` (4/16) — shift duration validation bounds
- Feature flags: `PERMITIR_INFERENCIA`, `ELIMINAR_DUPLICADOS_AUTO`, `GENERAR_HOJA_RESUMEN`, `GENERAR_CASOS_ESPECIALES`

### Data directories

- `data/input/` — Place source `.xls`/`.xlsx` files here
- `data/output/` — Generated reports land here
- `data/maestro/` — Optional employee master file (CODIGO, NOMBRE, DOCUMENTO, CARGO)
- `logs/` — Processing logs (`procesamiento_YYYYMMDD_HHMMSS.log`)

## Key Implementation Details

- Input Excel header detection is flexible: scans rows to find the one containing "ID".
- Datetime format is `DD/MM/YYYY HH:MM` (Colombian convention).
- Observations are pipe-separated (`|`) when multiple apply to one shift.
- Nocturnal exit records (00:00–10:00) are paired with the previous day's entry and attributed to the entry date.
- The shift dict structure includes `es_nocturno`, `completo`, `entrada_inferida`, `salida_inferida` boolean flags.
- Dependencies: pandas, openpyxl, xlrd, XlsxWriter, python-dateutil. Python 3.8+.
