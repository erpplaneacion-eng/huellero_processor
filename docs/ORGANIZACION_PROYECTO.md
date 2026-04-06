# Organizacion del Proyecto

## Vista general

Este repositorio contiene una aplicacion Django en `web/` que integra el procesamiento de huellero para el area de Logistica.

Arquitectura actual:

1. Capa web (autenticacion, vistas, dashboard, APIs).
2. Pipeline de negocio embebido en `web/apps/logistica/pipeline/`.
3. Persistencia en BD de maestro y registros procesados.

## Estructura recomendada

- `web/`: proyecto Django autocontenido.
- `web/apps/users/`: login, logout y redireccion por area.
- `web/apps/logistica/`: modelos, vistas y orquestador (`processor.py`).
- `web/apps/logistica/pipeline/`: limpieza, inferencia, turnos, calculo y generacion de Excel.
- `data/input/`: archivos de entrada del huellero.
- `data/output/`: reportes generados.
- `data/maestro/`: archivo maestro (`empleados.xlsx`).
- `logs/`: logs de ejecucion del pipeline.
- `docs/`: documentacion interna.

## Convenciones practicas

- Todo insumo operacional entra por `data/`.
- Evitar credenciales o secretos en archivos versionados.
- Versionar codigo y configuracion; no versionar contenido operativo de `data/` ni `logs/`.
- Mantener `web/` como bloque principal de ejecucion y despliegue.

## Comandos base

Desde la raiz del repo:

```bash
python web/manage.py migrate
python web/manage.py check
python web/manage.py runserver
```

Carga de maestro:

```bash
python web/manage.py cargar_maestro
```

## Nota historica

Referencias antiguas a `main.py`, `config.py` y `src/` en la raiz corresponden a una estructura anterior y ya no aplican en el estado actual del proyecto.
