# ⚡ INICIO RÁPIDO - 5 MINUTOS

## 🎯 Lo que hace este sistema

Transforma archivos crudos del huellero en reportes limpios y profesionales de Excel.

**Problemas que resuelve:**
✅ Elimina marcaciones duplicadas automáticamente
✅ Infiere estados faltantes (Entrada/Salida)
✅ Maneja correctamente turnos nocturnos
✅ Calcula horas trabajadas automáticamente
✅ Genera observaciones inteligentes

## 📦 Instalación (Una sola vez)

```bash
# 1. Abrir terminal en VS Code
# 2. Ejecutar:
pip install -r requirements.txt
```

## 🚀 Uso Diario

### Paso 1: Preparar archivo
Copia tu archivo `HUELLERO_*.xls` a la carpeta:
```
data/input/
```

### Paso 2: Ejecutar
```bash
python main.py
```

### Paso 3: Obtener resultado
Tu archivo estará en:
```
data/output/REPORTE_ASISTENCIA_[fecha].xlsx
```

## 📊 Qué contiene el archivo de salida

11 columnas con información completa:
1. Código del colaborador
2. Nombre completo
3. Documento (si tienes archivo maestro)
4. Fecha
5. Día de la semana
6. Número de marcaciones AM
7. Número de marcaciones PM
8. Hora de ingreso
9. Hora de salida
10. Total horas laboradas
11. Observaciones

## 🎨 Colores en el Excel

- 🟢 Verde = Todo correcto
- 🔵 Azul = Turno nocturno
- 🟡 Amarillo = Observaciones menores
- 🟠 Naranja = Requiere atención
- 🔴 Rojo = Alerta crítica

## 📝 Archivo Maestro (Recomendado)

Crea `data/maestro/empleados.xlsx` con:
```
CODIGO | NOMBRE                | DOCUMENTO
3      | HAROLD ANGULO C.     | 123456789
40     | JHON MICOLTA D.      | 987654321
```

Esto llenará la columna DOCUMENTO automáticamente.

## ⚠️ Notas Importantes

1. **Turnos Nocturnos**: Automáticamente detectados y procesados
   - Entrada: 18:00
   - Salida: 05:00 (día siguiente)
   - Se asigna al día de ENTRADA

2. **Marcaciones Duplicadas**: Se eliminan automáticamente
   - Umbral: < 2 minutos
   - Se conserva la primera marcación

3. **Estados Faltantes**: Se infieren por:
   - Hora del día
   - Contexto (marcación anterior/siguiente)
   - Patrón del empleado

## 🆘 Problemas Comunes

**Error: No se encontraron archivos**
→ Verifica que el archivo esté en `data/input/`

**Los documentos salen vacíos**
→ Crea archivo maestro o ignora (opcional)

**Aparecen muchas alertas**
→ Revisa `CASOS_REVISION_*.xlsx` para casos especiales

## 📞 Contacto

Para soporte o mejoras, contactar al área de tecnología.

---
**Versión 1.0 | Enero 2026**
