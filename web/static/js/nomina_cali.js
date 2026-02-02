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

    // 4. Calcular horas dinámicamente en las tarjetas
    calcularHorasTarjetas();
    
    // 5. Inicializar efectos de hover cruzado
    initHoverEffects();
});

/**
 * Inicializa el resaltado cruzado entre columnas al pasar el mouse
 */
function initHoverEffects() {
    const cards = document.querySelectorAll('.novedad-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const nombre = this.dataset.nombre;
            if (!nombre) return;
            
            // Normalizar nombre para búsqueda (opcional, pero data-nombre ya viene del backend)
            // Buscar todas las tarjetas con el mismo nombre exacto en el atributo data-nombre
            // Usamos comillas dobles escapadas en el selector por si el nombre tiene comillas simples
            const selector = `.novedad-card[data-nombre="${nombre.replace(/"/g, '\\"')}"]`;
            
            document.querySelectorAll(selector).forEach(match => {
                match.classList.add('highlight');
            });
        });
        
        card.addEventListener('mouseleave', function() {
            const nombre = this.dataset.nombre;
            if (!nombre) return;
            
            const selector = `.novedad-card[data-nombre="${nombre.replace(/"/g, '\\"')}"]`;
            
            document.querySelectorAll(selector).forEach(match => {
                match.classList.remove('highlight');
            });
        });
    });
}

/**
 * Tipos de tiempo que deben mostrar 0 horas (solo aplica a columna izquierda)
 */
const TIPOS_SIN_HORAS = ['DIAS NO CLASE', 'NO ASISTENCIA', 'PERMISO NO REMUNERADO'];

/**
 * Parsea una hora en varios formatos posibles y retorna minutos desde medianoche
 * Formatos soportados: HH:MM, HH:MM:SS, "5:30:00 a. m.", "1:30:00 p. m.", etc.
 */
function parsearHoraAMinutos(horaStr) {
    if (!horaStr || horaStr === '-') return null;

    horaStr = horaStr.toString().trim().toLowerCase();

    // Detectar AM/PM con varios formatos: "p.m.", "p. m.", "pm", "p.m", etc.
    let esPM = false;
    let esAM = false;

    // Regex para detectar PM en formatos: pm, p.m, p.m., p. m., p. m
    if (/p\.?\s?m\.?/i.test(horaStr)) {
        esPM = true;
        horaStr = horaStr.replace(/p\.?\s?m\.?/gi, '').trim();
    }
    // Regex para detectar AM en formatos: am, a.m, a.m., a. m., a. m
    else if (/a\.?\s?m\.?/i.test(horaStr)) {
        esAM = true;
        horaStr = horaStr.replace(/a\.?\s?m\.?/gi, '').trim();
    }

    // Separar por :
    const partes = horaStr.split(':');
    if (partes.length < 2) return null;

    let horas = parseInt(partes[0], 10);
    let minutos = parseInt(partes[1], 10);

    if (isNaN(horas) || isNaN(minutos)) return null;

    // Convertir 12h a 24h si es necesario
    if (esPM && horas < 12) {
        horas += 12;
    } else if (esAM && horas === 12) {
        horas = 0;
    }

    return horas * 60 + minutos;
}

/**
 * Calcula la diferencia de horas entre hora inicial y final
 * Retorna el valor en horas decimales (ej: 5.5)
 */
function calcularDiferenciaHoras(horaIni, horaFin) {
    const minIni = parsearHoraAMinutos(horaIni);
    const minFin = parsearHoraAMinutos(horaFin);

    if (minIni === null || minFin === null) return null;

    let diff = minFin - minIni;

    // Manejar turnos nocturnos (salida al día siguiente)
    if (diff < 0) {
        diff += 24 * 60; // Agregar 24 horas
    }

    return diff / 60; // Convertir a horas
}

/**
 * Calcula y muestra las horas en todas las tarjetas con clase .js-calc-horas
 */
function calcularHorasTarjetas() {
    const elementos = document.querySelectorAll('.js-calc-horas');

    elementos.forEach(el => {
        const horaIni = el.dataset.horaIni || '';
        const horaFin = el.dataset.horaFin || '';
        const tipo = (el.dataset.tipo || '').toUpperCase();
        const skipTipo = el.dataset.skipTipo === 'true';

        // Si el tipo es uno que no debe mostrar horas (solo si no tiene skip)
        if (!skipTipo && TIPOS_SIN_HORAS.some(t => tipo.includes(t))) {
            el.textContent = '⏱️ 0.0h';
            el.classList.add('novedad-card__horas--zero');
            return;
        }

        // Calcular horas
        const horas = calcularDiferenciaHoras(horaIni, horaFin);

        if (horas !== null && horas > 0) {
            el.textContent = `⏱️ ${horas.toFixed(1)}h`;
            el.classList.remove('novedad-card__horas--zero');
        } else {
            el.textContent = '⏱️ 0.0h';
            // Solo marcar como zero si no es skip (columna derecha no se marca en rojo por 0)
            if (!skipTipo) {
                el.classList.add('novedad-card__horas--zero');
            }
        }
    });
}

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
            const tieneHoras = registro.horas > 0;
            const tieneNovedad = registro.novedad === 'SI';

            if (tieneHoras && tieneNovedad) {
                // CASO MIXTO: Trabajó horas pero también tiene novedad (ej: accidente ese día)
                casillaClase += ' timeline-dia__casilla--mixto';
                contenido = registro.horas + '⚠️';
                titulo = `${registro.fecha}\nHoras: ${registro.horas}\nNovedad: ${registro.tipo}`;
            } else if (tieneNovedad) {
                // Solo novedad, sin horas (ej: incapacidad completa)
                casillaClase += ' timeline-dia__casilla--novedad';
                contenido = '⚠️';
                titulo = `${registro.fecha}\nNovedad: ${registro.tipo}`;
            } else if (tieneHoras) {
                // Turno normal con horas
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
