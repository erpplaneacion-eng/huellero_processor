# 🚀 GUÍA DE INSTALACIÓN RÁPIDA

## Paso 1: Requisitos Previos

✅ Python 3.8 o superior instalado
✅ pip (gestor de paquetes)

**Verificar instalación:**
```bash
python --version
pip --version
```

## Paso 2: Abrir Proyecto en VS Code

1. Abre Visual Studio Code
2. Menú: `Archivo` → `Abrir Carpeta`
3. Selecciona la carpeta `huellero_processor`

## Paso 3: Instalar Dependencias

Abre la terminal en VS Code (`Ctrl + ñ` o `View` → `Terminal`)

```bash
pip install -r requirements.txt
```

## Paso 4: Preparar Archivos

### Archivo de Huellero
Copia tu archivo `.xls` del huellero en:
```
data/input/
```

### Archivo Maestro (Opcional pero Recomendado)

Crea archivo `data/maestro/empleados.xlsx` con columnas:
- CODIGO
- NOMBRE
- DOCUMENTO
- CARGO (opcional)

Ver ejemplo en: `data/maestro/empleados_ejemplo.csv`

## Paso 5: Ejecutar

### Opción A: Modo Simple
```bash
python main.py
```

### Opción B: Modo Interactivo
```bash
python main.py --interactivo
```

### Opción C: Archivo Específico
```bash
python main.py --archivo ruta/al/archivo.xls
```

## Paso 6: Resultados

Los archivos procesados estarán en:
```
data/output/REPORTE_ASISTENCIA_YYYYMMDD_HHMMSS.xlsx
```

Los logs estarán en:
```
logs/procesamiento_YYYYMMDD_HHMMSS.log
```

## ⚠️ Solución de Problemas

### Error: "No module named 'pandas'"
```bash
pip install pandas openpyxl xlrd
```

### Error: "No se encontraron archivos"
- Verifica que el archivo esté en `data/input/`
- Verifica que tenga extensión `.xls` o `.xlsx`

### Los documentos salen vacíos
- Crea archivo maestro en `data/maestro/empleados.xlsx`
- O usa: `python main.py --sin-maestro`

## 📞 Soporte

Para problemas o dudas, consultar:
- README.md - Documentación completa
- logs/ - Archivos de log con detalles

---
**Última actualización:** Enero 2026
