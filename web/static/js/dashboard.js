/**
 * Dashboard de Asistencia - Huellero Processor
 * Corporación Hacia un Valle Solidario
 */

/* ===== Estado del módulo ===== */
let _dashEmpleados = [];       // lista completa
let _dashFiltrados = [];       // lista tras búsqueda
let _dashResult = null;        // resultado completo de la API
let _dashAreaConfig = null;    // AREA_CONFIG

/* ===== Punto de entrada ===== */
function renderizarDashboard(result, areaConfig) {
    _dashResult = result;
    _dashAreaConfig = areaConfig;
    _dashEmpleados = result.datos || [];
    _dashFiltrados = _dashEmpleados.slice();

    const section = document.getElementById('dashboardSection');
    section.style.display = 'block';

    // Ocultar sección de resultado anterior
    const resultSection = document.getElementById('resultSection');
    if (resultSection) resultSection.classList.remove('active');

    section.innerHTML = _construirHTML();

    // Eventos
    document.getElementById('dashBuscador').addEventListener('input', function () {
        filtrarEmpleados(this.value.trim());
    });
}

/* ===== Construcción HTML principal ===== */
function _construirHTML() {
    const { stats, archivo, archivo_casos } = _dashResult;
    const urlDescarga = _dashAreaConfig.apiDescargar + archivo + '/';
    const urlCasos = archivo_casos ? _dashAreaConfig.apiDescargar + archivo_casos + '/' : null;

    const resumen = calcularResumenGlobal(_dashEmpleados);

    return `
        ${_renderizarHeader(stats, archivo, urlDescarga, urlCasos)}
        ${_renderizarStatsBar(resumen)}
        <div class="dashboard-search">
            <input id="dashBuscador" type="text" placeholder="🔍 Buscar por nombre o código...">
        </div>
        <div class="dashboard-count" id="dashCount">
            Mostrando ${_dashEmpleados.length} de ${_dashEmpleados.length} empleados
        </div>
        <div id="dashLista">
            ${renderizarEmpleados(_dashEmpleados)}
        </div>
        ${_renderizarLeyenda()}
    `;
}

/* ===== Header ===== */
function _renderizarHeader(stats, nombreArchivo, urlDescarga, urlCasos) {
    return `
        <div class="dashboard-header">
            <div class="dashboard-header__meta">
                <h2>📊 Dashboard de Asistencia</h2>
                <p>
                    📄 ${nombreArchivo} &nbsp;|&nbsp;
                    👤 ${stats.empleados_unicos} empleados &nbsp;|&nbsp;
                    📋 ${stats.total_registros} registros
                </p>
            </div>
            <div class="dashboard-header__actions">
                <a href="${urlDescarga}" class="btn btn--success" download>📥 Descargar Excel</a>
                ${urlCasos ? `<a href="${urlCasos}" class="btn btn--primary" download>📋 Casos de Revisión</a>` : ''}
                <button class="btn btn--primary" onclick="location.reload()">🔄 Cargar otro</button>
            </div>
        </div>
    `;
}

/* ===== Chips de resumen global ===== */
function calcularResumenGlobal(empleados) {
    const conteos = { verde: 0, amarillo: 0, naranja: 0, azul: 0, morado: 0, gris: 0 };
    empleados.forEach(emp => {
        emp.registros.forEach(reg => {
            const clase = determinarClaseFila(reg.observacion);
            const key = clase.replace('fila--', '');
            if (conteos.hasOwnProperty(key)) conteos[key]++;
        });
    });
    return conteos;
}

function _renderizarStatsBar(resumen) {
    const defs = [
        { key: 'verde',    label: 'OK',               color: '#C6EFCE' },
        { key: 'amarillo', label: 'Advertencia',       color: '#FFEB9C' },
        { key: 'naranja',  label: 'Alerta',            color: '#FFC7CE' },
        { key: 'azul',     label: 'Turno nocturno',    color: '#DDEBF7' },
        { key: 'morado',   label: 'Salida nocturna',   color: '#E1BEE7' },
        { key: 'gris',     label: 'Sin registros',     color: '#D9D9D9' },
    ];

    const chips = defs.map(d => {
        const n = resumen[d.key] || 0;
        if (n === 0) return '';
        return `
            <span class="stat-chip stat-chip--${d.key}">
                <span class="stat-chip__dot" style="background:${d.color};border:1px solid rgba(0,0,0,0.15)"></span>
                ${d.label}: <strong>${n}</strong>
            </span>
        `;
    }).join('');

    return `<div class="dashboard-stats-bar">${chips}</div>`;
}

/* ===== Lista de empleados ===== */
function renderizarEmpleados(lista) {
    if (lista.length === 0) {
        return '<div class="dashboard-empty">No se encontraron empleados.</div>';
    }
    return lista.map(emp => renderizarEmpleadoCard(emp)).join('');
}

/* ===== Tarjeta de empleado ===== */
function renderizarEmpleadoCard(emp) {
    const stats = calcularStatsEmpleado(emp.registros);
    const cargo = emp.cargo ? `<span class="empleado-card__cargo">${emp.cargo}</span>` : '';
    const doc   = emp.documento ? `<span class="empleado-card__cargo" style="color:#aaa">Doc: ${emp.documento}</span>` : '';

    return `
        <div class="empleado-card" id="card-${emp.codigo}">
            <div class="empleado-card__header" onclick="toggleEmpleado('${emp.codigo}')">
                <span class="empleado-card__codigo">${emp.codigo}</span>
                <span class="empleado-card__nombre">${emp.nombre}</span>
                ${cargo}
                ${doc}
                <span class="empleado-card__resumen">
                    <span class="emp-chip emp-chip--dias">📅 ${stats.diasTrabajados} días</span>
                    <span class="emp-chip emp-chip--horas">⏱ ${formatearHoras(stats.totalHoras)}</span>
                    ${stats.novedades > 0 ? `<span class="emp-chip emp-chip--novedad">⚠ ${stats.novedades} novedad${stats.novedades > 1 ? 'es' : ''}</span>` : ''}
                </span>
                <span class="empleado-card__chevron">▶</span>
            </div>
            <div class="empleado-card__detalle" id="detalle-${emp.codigo}">
                <div class="empleado-card__detalle-inner">
                    ${renderizarTablaRegistros(emp.registros)}
                </div>
            </div>
        </div>
    `;
}

/* ===== Stats del empleado ===== */
function calcularStatsEmpleado(registros) {
    let diasTrabajados = 0;
    let totalHoras = 0;
    let novedades = 0;

    registros.forEach(reg => {
        const clase = determinarClaseFila(reg.observacion);
        if (clase !== 'fila--gris') diasTrabajados++;
        if (reg.horas !== null && reg.horas !== undefined) totalHoras += reg.horas;
        if (clase !== 'fila--verde' && clase !== 'fila--gris') novedades++;
    });

    return { diasTrabajados, totalHoras, novedades };
}

/* ===== Tabla de registros ===== */
function renderizarTablaRegistros(registros) {
    const filas = registros.map(reg => {
        const clase = determinarClaseFila(reg.observacion);
        const horas = reg.horas !== null && reg.horas !== undefined ? formatearHoras(reg.horas) : '—';
        const obs = reg.observacion || '—';
        return `
            <tr class="fila ${clase}">
                <td>${reg.fecha}</td>
                <td>${reg.dia}</td>
                <td>${reg.ingreso || '—'}</td>
                <td>${reg.salida || '—'}</td>
                <td>${horas}</td>
                <td title="${obs}">${_truncar(obs, 55)}</td>
            </tr>
        `;
    }).join('');

    return `
        <table class="registros-tabla">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Día</th>
                    <th>Ingreso</th>
                    <th>Salida</th>
                    <th>Total Horas</th>
                    <th>Observación</th>
                </tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>
    `;
}

/* ===== Mapeo observacion → clase CSS ===== */
function determinarClaseFila(obs) {
    if (!obs || obs === '' || obs === 'OK' || obs === 'Sin observaciones') return 'fila--verde';
    if (obs.includes('SIN REGISTROS') || obs.includes('SIN_REGISTROS')) return 'fila--gris';
    if (obs.includes('Salida Inferida Estándar') || obs.includes('SALIDA_ESTANDAR_NOCTURNA')) return 'fila--morado';
    if (obs.includes('Turno nocturno') || obs.includes('TURNO_NOCTURNO')) return 'fila--azul';
    if (obs.toUpperCase().includes('ALERTA')) return 'fila--naranja';
    return 'fila--amarillo';
}

/* ===== Toggle abrir/cerrar ===== */
function toggleEmpleado(codigo) {
    const card = document.getElementById('card-' + codigo);
    if (card) {
        card.classList.toggle('empleado-card--abierta');
    }
}

/* ===== Filtrar por búsqueda ===== */
function filtrarEmpleados(query) {
    const q = query.toLowerCase();
    _dashFiltrados = q
        ? _dashEmpleados.filter(e =>
            e.nombre.toLowerCase().includes(q) ||
            e.codigo.includes(q) ||
            (e.documento && e.documento.includes(q))
          )
        : _dashEmpleados.slice();

    document.getElementById('dashLista').innerHTML = renderizarEmpleados(_dashFiltrados);
    document.getElementById('dashCount').textContent =
        `Mostrando ${_dashFiltrados.length} de ${_dashEmpleados.length} empleados`;
}

/* ===== Formatear horas (decimal → "Xh YYmin") ===== */
function formatearHoras(horas) {
    if (horas === null || horas === undefined) return '—';
    const h = Math.floor(horas);
    const m = Math.round((horas - h) * 60);
    if (h === 0 && m === 0) return '0h';
    if (m === 0) return `${h}h`;
    if (h === 0) return `${m}min`;
    return `${h}h ${m}min`;
}

/* ===== Leyenda inferior ===== */
function _renderizarLeyenda() {
    const items = [
        { color: '#C6EFCE', label: 'OK' },
        { color: '#FFEB9C', label: 'Advertencia' },
        { color: '#FFC7CE', label: 'Alerta' },
        { color: '#DDEBF7', label: 'Turno nocturno' },
        { color: '#E1BEE7', label: 'Salida nocturna' },
        { color: '#D9D9D9', label: 'Sin registros' },
    ];
    return `
        <div class="dashboard-leyenda">
            ${items.map(i => `
                <span class="leyenda-item">
                    <span class="leyenda-item__color" style="background:${i.color}"></span>
                    ${i.label}
                </span>
            `).join('')}
        </div>
    `;
}

/* ===== Util: truncar texto ===== */
function _truncar(texto, max) {
    if (!texto) return '';
    return texto.length > max ? texto.slice(0, max) + '…' : texto;
}
