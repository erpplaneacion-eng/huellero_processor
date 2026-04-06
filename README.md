# Sistema Procesador de Huellero

Aplicacion web Django para procesar archivos de asistencia (huellero), generar reportes en Excel y administrar observaciones de novedades.

## Estado Actual (Abril 2026)

Este repositorio ya no usa `main.py` ni `src/` en la raiz.
La arquitectura actual es:

1. Aplicacion web Django en `web/`.
2. Pipeline de procesamiento en `web/apps/logistica/pipeline/`.

## Caracteristicas

- Limpieza automatica de marcaciones duplicadas.
- Inferencia de estados faltantes (Entrada/Salida).
- Deteccion de turnos nocturnos y reglas especiales.
- Calculo de horas trabajadas y validaciones de jornada.
- Generacion de Excel de resultados y casos especiales.
- Persistencia de resultados en base de datos (`RegistroAsistencia`).
- Dashboard web para consulta, filtros, descarga y observacion manual.

## Estructura del Proyecto

```text
huellero_processor/
|-- data/
|   |-- input/                  # Archivos de huellero cargados
|   |-- output/                 # Excels generados
|   `-- maestro/                # Excel maestro (empleados.xlsx)
|-- docs/
|   `-- ORGANIZACION_PROYECTO.md
|-- logs/                       # Logs del procesamiento
|-- web/
|   |-- manage.py               # Entrada de comandos Django
|   |-- huellero_web/           # Settings, urls, wsgi
|   |-- apps/
|   |   |-- users/              # Login y redireccion por area
|   |   `-- logistica/
|   |       |-- views.py        # Endpoints y vistas del area
|   |       |-- models.py       # Maestro y registros de asistencia
|   |       |-- processor.py    # Orquestador del pipeline
|   |       `-- pipeline/       # data_cleaner, inference, turnos, calculo, excel
|   |-- templates/
|   `-- static/
|-- requirements.txt
|-- Procfile
`-- railway.json
```

## Instalacion

Requisitos:

- Python 3.10+ recomendado.
- `pip`.

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion Local

Desde la raiz del repo:

```bash
python web/manage.py migrate
python web/manage.py collectstatic --noinput
python web/manage.py runserver
```

Abrir:

- `http://127.0.0.1:8000/users/login/`

## Flujo de Uso

1. Iniciar sesion.
2. Entrar al area de Logistica (`/logistica/`).
3. Cargar archivo `.xls` o `.xlsx` desde el modal del dashboard.
4. El sistema procesa, guarda en BD y devuelve estadisticas.
5. Desde el dashboard se puede:
- Filtrar por mes, empleado o documento.
- Descargar Excel de registros por rango de fechas.
- Descargar PDF de novedades.
- Guardar `OBSERVACIONES_1` por registro.

## Carga de Maestro de Empleados

Comando de gestion:

```bash
python web/manage.py cargar_maestro
```

Opciones:

```bash
python web/manage.py cargar_maestro --ruta data/maestro/empleados.xlsx
python web/manage.py cargar_maestro --limpiar
```

Hojas esperadas en el archivo maestro:

- `horas_cargos`
- `horarios`
- `cargos_horarios`
- `empleados_ejemplo`
- `conceptos`

## Configuracion Clave

- Django: `web/huellero_web/settings.py`
- Pipeline: `web/apps/logistica/pipeline/config.py`

Variables de entorno relevantes:

- `DJANGO_ENV`
- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `CSRF_TRUSTED_ORIGINS`

## Despliegue (Railway)

Configurado en `railway.json` para:

1. Ejecutar migraciones.
2. Ejecutar `collectstatic`.
3. Levantar `gunicorn`.

## Notas de Seguridad

- No incluir credenciales en archivos versionados.
- Usar variables de entorno para secretos y accesos.

## Licencia

Uso interno - Corporacion Hacia un Valle Solidario.
