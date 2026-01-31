/**
 * Nómina Cali - Calendario, Filtros y Detalle de Colaborador
 * Corporación Hacia un Valle Solidario
 */

let asistenciaData = {};

document.addEventListener('DOMContentLoaded', function() {
    // 1. Cargar datos de asistencia desde el JSON incrustado
    const scriptData = document.getElementById('asistencia-data');
    if (scriptData) {
        try {
            asistenciaData = JSON.parse(scriptData.textContent);
        } catch (e) {
            console.error("Error parseando datos de asistencia:", e);
        }
    }

    // 2. Inicializar días seleccionados
    const diasInputs = document.querySelectorAll('#diasSeleccionadosContainer input[name="dias"]');
    window.diasSeleccionados = new Set();
    diasInputs.forEach(input => {
        window.diasSeleccionados.add(input.value);
    });

    // 3. Hacer clickeables los nombres en las tarjetas
    hacerNombresClickeables();
});

function hacerNombresClickeables() {
    const nombres = document.querySelectorAll('.novedad-card__nombre');
    nombres.forEach(el => {
        el.style.cursor = 'pointer';
        el.style.textDecoration = 'underline';
        el.style.textDecorationStyle = 'dotted';
        
        el.addEventListener('click', function() {
            // Buscar cédula por nombre en el dataset (método aproximado o exacto)
            const nombreBusq = this.textContent.trim();
            buscarYMostrarColaborador(nombreBusq);
        });
    });
}

function buscarYMostrarColaborador(nombre) {
    // Buscar en el objeto asistenciaData
    let cedulaEncontrada = null;
    
    // Búsqueda exacta primero
    for (const [cedula, data] of Object.entries(asistenciaData)) {
        if (data.nombre === nombre) {
            cedulaEncontrada = cedula;
            break;
        }
    }

    // Si no encuentra, búsqueda parcial
    if (!cedulaEncontrada) {
        for (const [cedula, data] of Object.entries(asistenciaData)) {
            if (data.nombre.includes(nombre) || nombre.includes(data.nombre)) {
                cedulaEncontrada = cedula;
                break;
            }
        }
    }

    if (cedulaEncontrada) {
        mostrarDetalle(cedulaEncontrada);
    } else {
        alert("No se encontraron detalles detallados para este colaborador en el mes actual.");
    }
}

function mostrarDetalle(cedula) {
    const data = asistenciaData[cedula];
    if (!data) return;

    // Llenar cabecera
    document.getElementById('detalleNombre').textContent = data.nombre;
    document.getElementById('detalleSede').textContent = data.sede;
    document.getElementById('detalleCedula').textContent = 'CC: ' + cedula;

    // Llenar stats
    document.getElementById('statDiasTrab').textContent = data.resumen.dias_trabajados;
    document.getElementById('statHoras').textContent = data.resumen.total_horas.toFixed(2);
    document.getElementById('statNovedades').textContent = data.resumen.dias_novedad;

    // Llenar timeline
    const timelineContainer = document.querySelector('.detalle-timeline');
    timelineContainer.innerHTML = '';

    // Ordenar registros por día
    const registrosOrdenados = data.registros.sort((a, b) => parseInt(a.dia) - parseInt(b.dia));

    // Crear mapa de días para llenado rápido
    const diasMap = {};
    registrosOrdenados.forEach(r => diasMap[parseInt(r.dia)] = r);

    // Generar 31 días (o los del mes actual)
    for (let i = 1; i <= 31; i++) {
        const registro = diasMap[i];
        const diaDiv = document.createElement('div');
        diaDiv.className = 'timeline-dia';

        let casillaClase = 'timeline-dia__casilla';
        let contenido = '-';
        let titulo = `Día ${i}: Sin registro`;

        if (registro) {
            if (registro.novedad === 'SI') {
                casillaClase += ' timeline-dia__casilla--novedad';
                contenido = '⚠️';
                titulo = `${registro.fecha}\nNovedad: ${registro.tipo}`;
            } else if (registro.horas > 0) {
                casillaClase += ' timeline-dia__casilla--trabajado';
                contenido = registro.horas;
                titulo = `${registro.fecha}\nHoras: ${registro.horas}\nTurno Normal`;
            } else {
                contenido = '0';
                titulo = `${registro.fecha}\nRegistro sin horas`;
            }
        }

        diaDiv.innerHTML = `
            <div class="${casillaClase}" title="${titulo}">${contenido}</div>
            <span class="timeline-dia__fecha">${i}</span>
        `;
        timelineContainer.appendChild(diaDiv);
    }

    // Mostrar panel con animación
    const panel = document.getElementById('detalleManipuladora');
    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function cerrarDetalle() {
    document.getElementById('detalleManipuladora').style.display = 'none';
}

/**
 * Toggle selección de un día en el calendario
 * @param {number} dia - Número del día a seleccionar/deseleccionar
 */
function toggleDia(dia) {
    const diaStr = dia.toString();
    const diaElement = document.querySelector(`[data-dia="${dia}"]`);

    if (!diaElement) return;

    if (window.diasSeleccionados.has(diaStr)) {
        window.diasSeleccionados.delete(diaStr);
        diaElement.classList.remove('calendario-dia--seleccionado');
    } else {
        window.diasSeleccionados.add(diaStr);
        diaElement.classList.add('calendario-dia--seleccionado');
    }

    actualizarFormulario();
}

/**
 * Actualiza los inputs ocultos del formulario y lo envía
 */
function actualizarFormulario() {
    const container = document.getElementById('diasSeleccionadosContainer');
    if (!container) return;

    // Limpiar inputs existentes
    container.innerHTML = '';

    // Crear nuevos inputs para cada día seleccionado
    window.diasSeleccionados.forEach(dia => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'dias';
        input.value = dia;
        container.appendChild(input);
    });

    // Enviar formulario
    const form = document.getElementById('filtrosForm');
    if (form) {
        form.submit();
    }
}

/**
 * Limpia la selección de días y muestra todos los registros
 */
function verTodos() {
    window.diasSeleccionados.clear();

    // Limpiar selección visual
    document.querySelectorAll('.calendario-dia--seleccionado').forEach(el => {
        el.classList.remove('calendario-dia--seleccionado');
    });

    actualizarFormulario();
}
