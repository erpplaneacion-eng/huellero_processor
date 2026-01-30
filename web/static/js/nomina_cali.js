/**
 * Nómina Cali - Calendario y Filtros
 * Corporación Hacia un Valle Solidario
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar días seleccionados desde el DOM
    const diasInputs = document.querySelectorAll('#diasSeleccionadosContainer input[name="dias"]');
    window.diasSeleccionados = new Set();
    diasInputs.forEach(input => {
        window.diasSeleccionados.add(input.value);
    });
});

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
