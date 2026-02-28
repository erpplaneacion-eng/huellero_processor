# Organizacion del Proyecto

## Vista general
Este repositorio contiene dos componentes en una misma raiz:

1. Procesador CLI de huellero (main.py, config.py, src/)
2. Aplicacion web Django (web/)

## Estructura actual recomendada

- main.py: punto de entrada CLI
- config.py: configuracion central del procesador
- src/: logica del pipeline de procesamiento
- data/input/: archivos de entrada de huellero
- data/output/: reportes generados
- data/maestro/: maestro de empleados
- data/maestro/fuentes/: excels de referencia historicos (antes archivos_excel/)
- logs/: logs de ejecucion del procesador
- web/: proyecto Django completo (apps, templates, static, manage.py)
- docs/: documentacion interna del proyecto

## Convenciones practicas

- Todo archivo fuente/insumo debe entrar por data/.
- Evitar carpetas sueltas en raiz para datos operativos.
- logs/, data/input/, data/output/, data/maestro/ se consideran datos de entorno (no versionar contenido).
- Mantener web/ como bloque autocontenido de la app Django.

## Proximo paso sugerido

Si quieres una limpieza mas profunda, el siguiente paso es separar en monorepo explicito:

- apps/processor/ para CLI
- apps/web/ para Django
- wrappers de compatibilidad para no romper comandos existentes.
