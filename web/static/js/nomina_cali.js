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
            const selector = `.novedad-card[data-nombre="${nombre.replace(/"/g, '"')}"]`;
            
            document.querySelectorAll(selector).forEach(match => {
                match.classList.add('highlight');
            });
        });
        
        card.addEventListener('mouseleave', function() {
            const nombre = this.dataset.nombre;
            if (!nombre) return;
            
            const selector = `.novedad-card[data-nombre="${nombre.replace(/"/g, '"')}"]`;
            
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

function mostrarDetalle(cedulaTarget) {
    const dataTarget = asistenciaData[cedulaTarget];
    if (!dataTarget) return;

    const sedeTarget = dataTarget.sede;
    let equipo = [];

    // 1. Filtrar equipo por Sede
    // Si tiene sede, buscar todos los de esa sede. Si no, solo mostrar al individuo.
    if (sedeTarget) {
        equipo = Object.values(asistenciaData).filter(emp => emp.sede === sedeTarget);
    } else {
        equipo = [dataTarget];
    }

    // 2. Ordenar: El seleccionado primero, luego alfabéticamente
    equipo.sort((a, b) => {
        // Si 'a' es el objeto target, ponerlo primero (-1)
        if (a === dataTarget) return -1;
        if (b === dataTarget) return 1;
        // Orden alfabético por nombre
        return (a.nombre || '').localeCompare(b.nombre || '');
    });

    // 3. Actualizar Cabecera del Panel
    const tituloSede = sedeTarget ? `Sede: ${sedeTarget}` : 'Sin Sede Asignada';
    const countText = `${equipo.length} Colaborador${equipo.length !== 1 ? 'es' : ''}`;
    
    // Elementos del DOM (asegurarse de que existan en el HTML actualizado)
    const elTitulo = document.getElementById('detalleSedeTitle');
    const elCount = document.getElementById('detalleCount');
    
    if (elTitulo) elTitulo.textContent = tituloSede;
    if (elCount) elCount.textContent = countText;

    // 4. Generar la Lista de Filas
    const container = document.getElementById('detalleTeamList');
    if (!container) return;
    
    container.innerHTML = '';

    equipo.forEach(miembro => {
        const isSelected = (miembro === dataTarget);
        const row = document.createElement('div');
        row.className = `team-member-row ${isSelected ? 'team-member-row--selected' : ''}`;
        
        // Generar HTML de la línea de tiempo y calcular horas reales dinámicamente
        // Llamamos a generarHTMLTimeline que retorna un objeto { html, totalHoras, diasTrabajados }
        const timelineData = generarHTMLTimeline(miembro.registros);
        const timelineHTML = timelineData.html;
        
        // Usar los totales calculados dinámicamente
        const totalHorasCalculadas = timelineData.totalHoras.toFixed(1);
        const diasTrabCalculados = timelineData.diasTrabajados;

        // Datos de resumen
        const diasNov = miembro.resumen.dias_novedad;
        const cedulaStr = miembro.cedula ? `CC: ${miembro.cedula}` : '';

        row.innerHTML = `
            <div class="member-info">
                <div>
                    <span class="member-name">${miembro.nombre}</span>
                    <span class="member-cedula">${cedulaStr}</span>
                </div>
                <div class="member-stats">
                    <span class="stat-tag">Trab: <strong>${diasTrabCalculados}d</strong></span>
                    <span class="stat-tag">Horas: <strong>${totalHorasCalculadas}h</strong></span>
                    ${diasNov > 0 ? `<span class="stat-tag" style="color:#856404; background:#fff3cd;">Nov: <strong>${diasNov}d</strong></span>` : ''}
                </div>
            </div>
            <div class="detalle-timeline">
                ${timelineHTML}
            </div>
        `;
        
        container.appendChild(row);
    });

    // 5. Mostrar Panel y Scroll
    const panel = document.getElementById('detalleManipuladora');
    panel.style.display = 'block';
    // Scroll suave hacia el panel
    panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Genera el HTML de la barra de tiempo (1-31 días) para un colaborador
 * Fusiona registros si hay duplicados en el mismo día (nómina + novedad)
 * Retorna objeto { html, totalHoras, diasTrabajados }
 */
function generarHTMLTimeline(registros) {
    // 1. Fusionar registros por día
    const diasMap = {}; // { 1: {horas: 5.5, novedad: 'SI', tipos: []} }

    if (registros) {
        registros.forEach(r => {
            const diaNum = parseInt(r.dia);
            if (isNaN(diaNum)) return;

            if (!diasMap[diaNum]) {
                diasMap[diaNum] = {
                    fecha: r.fecha,
                    horas: 0,
                    tieneNovedad: false,
                    tipos: new Set()
                };
            }

            const diaObj = diasMap[diaNum];

            // Calcular horas dinámicas para este registro
            let horasCalc = 0;
            if (r.hora_ini && r.hora_fin) {
                const diff = calcularDiferenciaHoras(r.hora_ini, r.hora_fin);
                if (diff !== null) horasCalc = diff;
            } else {
                // Fallback a las horas estáticas si no hay horas inicio/fin
                horasCalc = parseFloat(r.horas) || 0;
            }

            // Aplicar regla TIPOS_SIN_HORAS
            const tipoUpper = (r.tipo || '').toUpperCase();
            if (TIPOS_SIN_HORAS.some(t => tipoUpper.includes(t))) {
                horasCalc = 0;
            }

            // Actualizar horas del día fusionado
            // Prioridad: Si ya tenía horas, nos quedamos con el máximo (asumiendo que uno es el turno y otro tal vez 0)
            // O sumamos? Usualmente es un solo turno real. Max es más seguro para evitar duplicar si viene de dos fuentes
            diaObj.horas = Math.max(diaObj.horas, horasCalc);

            // Actualizar estado de novedad
            if (r.novedad === 'SI') {
                diaObj.tieneNovedad = true;
            }

            // Agregar tipo
            if (r.tipo) {
                diaObj.tipos.add(r.tipo);
            }
        });
    }
    
    let html = '';
    let totalHorasPeriodo = 0;
    let totalDiasTrabajados = 0;
    
    // 2. Generar casillas del 1 al 31
    for (let i = 1; i <= 31; i++) {
        const diaDatos = diasMap[i];
        let casillaClase = 'timeline-dia__casilla';
        let contenido = '-';
        let titulo = `Día ${i}: Sin registro`;

        if (diaDatos) {
            const horasVal = diaDatos.horas;
            const tieneNovedad = diaDatos.tieneNovedad;
            const tiposStr = Array.from(diaDatos.tipos).join(', ');
            
            // Sumar al total del periodo si hay horas trabajadas
            if (horasVal > 0) {
                totalHorasPeriodo += horasVal;
                totalDiasTrabajados++; // Contar día trabajado
            }
            
            // Formatear horas para mostrar (sin .0 si es entero)
            let horasTxt = horasVal % 1 === 0 ? horasVal.toFixed(0) : horasVal.toFixed(1);

            if (horasVal > 0 && tieneNovedad) {
                // CASO MIXTO: Trabajó horas pero también tiene novedad
                casillaClase += ' timeline-dia__casilla--mixto';
                // Mostrar horas y alerta pequeña
                contenido = `${horasTxt}<span style="font-size:0.9em; vertical-align: top;">⚠️</span>`;
                titulo = `${diaDatos.fecha}\nHoras: ${horasTxt}\nNovedad: ${tiposStr}`;
            } else if (tieneNovedad) {
                // Solo novedad (Horas = 0)
                casillaClase += ' timeline-dia__casilla--novedad';
                contenido = '⚠️';
                titulo = `${diaDatos.fecha}\nNovedad: ${tiposStr}`;
            } else if (horasVal > 0) {
                // Turno normal
                casillaClase += ' timeline-dia__casilla--trabajado';
                contenido = horasTxt; 
                titulo = `${diaDatos.fecha}\nHoras: ${horasTxt}\nTurno Normal`;
            } else {
                // Registro sin horas (ej: descanso o error)
                contenido = '0';
                titulo = `${diaDatos.fecha}\nRegistro sin horas calculadas`;
            }
        }

        html += `
            <div class="timeline-dia">
                <div class="${casillaClase}" title="${titulo}">${contenido}</div>
                <span class="timeline-dia__fecha">${i}</span>
            </div>
        `;
    }
    
    return {
        html: html,
        totalHoras: totalHorasPeriodo,
        diasTrabajados: totalDiasTrabajados
    };
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
