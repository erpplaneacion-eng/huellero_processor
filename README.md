# 🕐 Sistema Procesador de Huellero

Sistema automático para limpiar y procesar archivos de control de asistencia (huellero biométrico).

## 📋 Características

- ✅ Limpieza automática de marcaciones duplicadas
- ✅ Inferencia inteligente de estados faltantes (Entrada/Salida)
- ✅ Detección y manejo de turnos nocturnos
- ✅ Cálculo automático de horas laboradas
- ✅ Generación de reportes en Excel con formato profesional
- ✅ Sistema de observaciones automáticas
- ✅ Log detallado del procesamiento

## 🗂️ Estructura del Proyecto

```
huellero_processor/
├── main.py                      # Archivo principal - ejecutar aquí
├── config.py                    # Configuraciones del sistema
├── requirements.txt             # Dependencias Python
├── README.md                    # Este archivo
│
├── src/
│   ├── __init__.py
│   ├── data_cleaner.py         # Limpieza de datos
│   ├── state_inference.py      # Inferencia de estados
│   ├── shift_builder.py        # Construcción de turnos
│   ├── calculator.py           # Cálculos de horas
│   ├── excel_generator.py      # Generación de Excel
│   └── logger.py               # Sistema de logging
│
├── data/
│   ├── input/                  # Colocar archivos de entrada aquí
│   │   └── HUELLERO_*.xls
│   ├── output/                 # Archivos procesados
│   └── maestro/                # Archivo maestro de empleados (opcional)
│       └── empleados.xlsx
│
└── logs/                       # Logs de procesamiento
```

## 🚀 Instalación

### 1. Requisitos Previos
- Python 3.8 o superior
- pip (gestor de paquetes Python)

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

## 📖 Uso

### Opción 1: Uso Básico (Sin Archivo Maestro)

1. Coloca el archivo de huellero en `data/input/`
2. Ejecuta:

```bash
python main.py
```

### Opción 2: Con Archivo Maestro de Empleados

1. Crea archivo `data/maestro/empleados.xlsx` con columnas:
   - CODIGO
   - NOMBRE
   - DOCUMENTO
   - CARGO (opcional)

2. Coloca el archivo de huellero en `data/input/`

3. Ejecuta:

```bash
python main.py --con-maestro
```

### Opción 3: Modo Interactivo

```bash
python main.py --interactivo
```

## 📊 Archivo de Salida

El sistema genera un archivo Excel con las siguientes columnas:

| Columna | Descripción |
|---------|-------------|
| CODIGO COLABORADOR | ID del empleado |
| NOMBRE COMPLETO DEL COLABORADOR | Nombre completo |
| DOCUMENTO DEL COLABORADOR | Cédula/documento |
| FECHA | Fecha del turno (DD/MM/YYYY) |
| DIA | Día de la semana |
| # MARCACIONES AM | Marcaciones entre 06:00-11:59 |
| # MARCACIONES PM | Marcaciones entre 12:00-23:59 |
| HORA DE INGRESO | Hora de entrada |
| HORA DE SALIDA | Hora de salida |
| TOTAL HORAS LABORADAS | Horas trabajadas |
| OBSERVACION | Notas y alertas |

## ⚙️ Configuración

Edita `config.py` para ajustar:

- Umbrales de tiempo para duplicados
- Horarios de turnos AM/PM
- Validaciones de horas mínimas/máximas
- Formato de fechas
- Colores del Excel

## 🔍 Tipos de Observaciones

| Código | Significado |
|--------|-------------|
| `OK` | Turno completo sin problemas |
| `TURNO_NOCTURNO` | Entrada tarde, salida madrugada |
| `SALIDA_NR` | Salida no registrada |
| `ENTRADA_NR` | Entrada no registrada |
| `ESTADO_INFERIDO` | Estado deducido por contexto |
| `DUPLICADOS_ELIM` | Marcaciones duplicadas eliminadas |
| `ALERTA: Turno largo` | Más de 14 horas |
| `ALERTA: Turno corto` | Menos de 6 horas |
| `REQUIERE_REVISION` | Necesita revisión manual |

## 📝 Logs

El sistema genera logs detallados en `logs/`:
- `procesamiento_YYYYMMDD_HHMMSS.log` - Log general
- `casos_especiales_YYYYMMDD.xlsx` - Casos para revisión manual

## contraseñas usuarios logistica
marcecast
marce123
## administrador
admin                                                                                                     
Chvs2024* 

## 🛠️ Soporte

Para reportar problemas o sugerencias, contactar al administrador del sistema.

## 📄 Licencia

Uso interno - Corporación Hacia un Valle Solidario

---
**Versión:** 1.0.0  
**Última actualización:** Enero 2026
