/**
 * Dashboard de Asistencia - Huellero Processor
 * Corporación Hacia un Valle Solidario
 */

/* ===== Estado del módulo ===== */
let _dashEmpleados = [];       // lista completa
let _dashFiltrados = [];       // lista tras búsqueda
let _dashResult = null;        // resultado completo de la API
let _dashAreaConfig = null;    // AREA_CONFIG
const _PDF_CLASES_EXCLUIDAS = new Set(['fila--verde', 'fila--gris', 'fila--naranja', 'fila--azul']);

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
    const urlDescarga = archivo ? _dashAreaConfig.apiDescargar + archivo + '/' : null;
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
    const subtitulo = nombreArchivo
        ? `📄 ${nombreArchivo}`
        : '🗄️ Datos desde base de datos';

    return `
        <div class="dashboard-header">
            <div class="dashboard-header__meta">
                <h2>📊 Dashboard de Asistencia</h2>
                <p>
                    ${subtitulo} &nbsp;|&nbsp;
                    👤 ${stats.empleados_unicos} empleados &nbsp;|&nbsp;
                    📋 ${stats.total_registros} registros
                </p>
            </div>
            <div class="dashboard-header__actions">
                ${urlDescarga ? `<a href="${urlDescarga}" class="btn btn--success" download>📥 Descargar Excel</a>` : ''}
                ${urlCasos ? `<a href="${urlCasos}" class="btn btn--primary" download>📋 Casos de Revisión</a>` : ''}
                <button class="btn btn--pdf" onclick="descargarPDF()">🖨 Informe PDF</button>
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

    // Límite de horas/día: primer valor no vacío entre los registros
    const limiteRaw = emp.registros.map(r => r.limite).find(l => l && l !== '' && l !== 'nan') || '';
    const limiteNum = limiteRaw ? parseFloat(limiteRaw) : null;

    const cargo = emp.cargo ? `<span class="empleado-card__cargo">${emp.cargo}</span>` : '';
    const doc   = emp.documento ? `<span class="empleado-card__cargo" style="color:#aaa">C.C. ${emp.documento}</span>` : '';
    const limiteChip = limiteNum !== null
        ? `<span class="emp-chip emp-chip--limite">⏰ Límite: ${formatearHoras(limiteNum)}/día</span>`
        : '';

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
                    ${limiteChip}
                    ${stats.novedades > 0 ? `<span class="emp-chip emp-chip--novedad">⚠ ${stats.novedades} novedad${stats.novedades > 1 ? 'es' : ''}</span>` : ''}
                </span>
                <span class="empleado-card__chevron">▶</span>
            </div>
            <div class="empleado-card__detalle" id="detalle-${emp.codigo}">
                <div class="empleado-card__detalle-inner">
                    <div class="empleado-card__acciones">
                        <button class="btn btn--pdf btn--pdf-individual" onclick="descargarPDFEmpleado('${emp.codigo}')">
                            🖨 PDF Individual
                        </button>
                    </div>
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
    const conceptos = (_dashResult && _dashResult.conceptos) ? _dashResult.conceptos : [];
    const opcionesHTML = conceptos.map(c =>
        `<option value="${_escaparAttr(c)}">${_truncar(c, 60)}</option>`
    ).join('');

    const filas = registros.map(reg => {
        const clase = determinarClaseFila(reg.observacion);
        const horas = reg.horas !== null && reg.horas !== undefined ? formatearHoras(reg.horas) : '—';
        const obs = reg.observacion || '—';
        const tieneId = reg.id !== null && reg.id !== undefined;
        const obs1Val = reg.obs1 || '';

        const selectHTML = tieneId
            ? `<select class="obs1-select"
                        data-id="${reg.id}"
                        onchange="guardarObs1(this)"
                        title="${_escaparAttr(obs1Val)}">
                    <option value="">— Sin observación —</option>
                    ${conceptos.map(c =>
                        `<option value="${_escaparAttr(c)}"${c === obs1Val ? ' selected' : ''}>${_truncar(c, 60)}</option>`
                    ).join('')}
               </select>`
            : `<span class="obs1-nobd">—</span>`;

        return `
            <tr class="fila ${clase}">
                <td>${reg.fecha}</td>
                <td>${reg.dia}</td>
                <td>${reg.ingreso || '—'}</td>
                <td>${reg.salida || '—'}</td>
                <td>${horas}</td>
                <td title="${obs}">${_truncar(obs, 55)}</td>
                <td class="obs1-celda">${selectHTML}</td>
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
                    <th>Obs. Manual</th>
                </tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>
    `;
}

/* ===== Guardar OBSERVACIONES_1 vía AJAX ===== */
function guardarObs1(selectEl) {
    const registroId = parseInt(selectEl.dataset.id, 10);
    const obs1 = selectEl.value;

    if (!registroId || isNaN(registroId)) {
        console.warn('guardarObs1: data-id inválido', selectEl.dataset.id);
        return;
    }

    // URL desde AREA_CONFIG inyectada en el template, con fallback hardcodeado
    const url = (_dashAreaConfig && _dashAreaConfig.apiGuardarObs1)
        || '/logistica/api/registros/obs1/';

    selectEl.disabled = true;
    selectEl.style.opacity = '0.6';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ registro_id: registroId, obs1: obs1 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            selectEl.style.background = '#C6EFCE';
            setTimeout(() => { selectEl.style.background = ''; }, 1500);
        } else {
            selectEl.style.background = '#FFC7CE';
            console.error('Error al guardar obs1:', data.error);
            setTimeout(() => { selectEl.style.background = ''; }, 2000);
        }
    })
    .catch(err => {
        selectEl.style.background = '#FFC7CE';
        console.error('Error de red al guardar obs1:', err);
        setTimeout(() => { selectEl.style.background = ''; }, 2000);
    })
    .finally(() => {
        selectEl.disabled = false;
        selectEl.style.opacity = '';
    });
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

/* ===== Util: escapar caracteres especiales en atributos HTML ===== */
function _escaparAttr(texto) {
    if (!texto) return '';
    return String(texto)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

/* ===== PDF: descarga informe de novedades ===== */
function descargarPDF() {
    // Recopilar novedades: excluir verde (OK), gris (sin registros), naranja (exceso horas) y azul (turno nocturno)
    const conNovedades = [];
    _dashEmpleados.forEach(emp => {
        const novs = _obtenerNovedadesEmpleado(emp);
        if (novs.length > 0) {
            conNovedades.push({ emp, novs });
        }
    });

    if (conNovedades.length === 0) {
        alert('No hay novedades para reportar (excluyendo exceso de horas y sin registros).');
        return;
    }

    const ventana = window.open('', '_blank');
    ventana.document.write(_generarHTMLPDF(conNovedades, { esIndividual: false }));
    ventana.document.close();
    // Esperar a que cargue antes de imprimir
    ventana.addEventListener('load', () => ventana.print());
}

function descargarPDFEmpleado(codigo) {
    const emp = _dashEmpleados.find(e => String(e.codigo) === String(codigo));
    if (!emp) {
        alert('No se encontró el empleado para generar el PDF.');
        return;
    }

    const novs = _obtenerNovedadesEmpleado(emp);
    if (novs.length === 0) {
        alert(`No hay novedades para reportar de ${emp.nombre}.`);
        return;
    }

    const ventana = window.open('', '_blank');
    ventana.document.write(_generarHTMLPDF([{ emp, novs }], { esIndividual: true }));
    ventana.document.close();
    ventana.addEventListener('load', () => ventana.print());
}

function _obtenerNovedadesEmpleado(emp) {
    return emp.registros.filter(r => {
        const clase = determinarClaseFila(r.observacion);
        return !_PDF_CLASES_EXCLUIDAS.has(clase);
    });
}

function _generarHTMLPDF(conNovedades, opciones = {}) {
    const ahora = new Date();
    const fechaStr = ahora.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const archivo = _dashResult.archivo || '';
    const totalNovs = conNovedades.reduce((s, e) => s + e.novs.length, 0);
    const esIndividual = opciones.esIndividual === true;
    const titulo = esIndividual
        ? `Informe Individual de Novedades — ${conNovedades[0]?.emp?.nombre || ''}`
        : 'Informe de Novedades — Corporación Hacia un Valle Solidario';

    const COLORES = {
        'fila--amarillo': { bg: '#FFEB9C', label: 'Advertencia' },
        'fila--morado':   { bg: '#E1BEE7', label: 'Salida nocturna' },
    };

    const seccionesHTML = conNovedades.map(({ emp, novs }) => {
        const limiteRaw = emp.registros.map(r => r.limite).find(l => l && l !== '' && l !== 'nan') || '';
        const limiteNum = limiteRaw ? parseFloat(limiteRaw) : null;
        const limiteTexto = limiteNum !== null ? `Límite: ${formatearHoras(limiteNum)}/día` : '';

        const filasHTML = novs.map(r => {
            const clase = determinarClaseFila(r.observacion);
            const cfg = COLORES[clase] || { bg: '#fff', label: '' };
            const horas = r.horas !== null && r.horas !== undefined ? formatearHoras(r.horas) : '—';
            return `
                <tr>
                    <td style="background:${cfg.bg}">${r.fecha}</td>
                    <td style="background:${cfg.bg}">${r.dia}</td>
                    <td style="background:${cfg.bg}">${r.ingreso || '—'}</td>
                    <td style="background:${cfg.bg}">${r.salida || '—'}</td>
                    <td style="background:${cfg.bg}">${horas}</td>
                    <td style="background:${cfg.bg};font-size:10px">${cfg.label}</td>
                    <td style="background:${cfg.bg};font-size:10px">${r.observacion}</td>
                </tr>`;
        }).join('');

        return `
            <div class="empleado-bloque">
                <div class="empleado-encabezado">
                    <span class="emp-codigo">${emp.codigo}</span>
                    <span class="emp-nombre">${emp.nombre}</span>
                    ${emp.cargo ? `<span class="emp-cargo">${emp.cargo}</span>` : ''}
                    ${emp.documento ? `<span class="emp-doc">C.C. ${emp.documento}</span>` : ''}
                    ${limiteTexto ? `<span class="emp-limite">${limiteTexto}</span>` : ''}
                    <span class="emp-count">${novs.length} novedad${novs.length > 1 ? 'es' : ''}</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Fecha</th><th>Día</th><th>Ingreso</th>
                            <th>Salida</th><th>Horas</th><th>Tipo</th><th>Observación</th>
                        </tr>
                    </thead>
                    <tbody>${filasHTML}</tbody>
                </table>
            </div>`;
    }).join('');

    const leyendaHTML = Object.values(COLORES).map(c =>
        `<span class="ley-item"><span class="ley-color" style="background:${c.bg}"></span>${c.label}</span>`
    ).join('');

    return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>${esIndividual ? 'Informe Individual de Novedades' : 'Informe de Novedades'} - ${fechaStr}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; font-size: 12px; color: #222; padding: 24px; }
  .portada { margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 12px; }
  .portada h1 { font-size: 18px; }
  .portada p  { font-size: 11px; color: #555; margin-top: 4px; }
  .resumen { display: flex; gap: 24px; margin-bottom: 16px; }
  .resumen-item { background: #f5f5f5; border-radius: 6px; padding: 8px 16px; text-align: center; }
  .resumen-item strong { display: block; font-size: 20px; }
  .resumen-item span   { font-size: 10px; color: #666; }
  .leyenda { display: flex; gap: 16px; margin-bottom: 20px; font-size: 11px; }
  .ley-item { display: flex; align-items: center; gap: 5px; }
  .ley-color { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }
  .empleado-bloque { margin-bottom: 20px; page-break-inside: avoid; }
  .empleado-encabezado { display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      background: #1a1a2e; color: #fff; padding: 8px 12px; border-radius: 6px 6px 0 0; }
  .emp-codigo { background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px; font-size: 11px; }
  .emp-nombre { font-weight: bold; font-size: 13px; }
  .emp-cargo  { font-size: 11px; color: #ccc; }
  .emp-doc    { font-size: 11px; color: #aaa; }
  .emp-limite { font-size: 11px; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 10px; }
  .emp-count  { margin-left: auto; font-size: 11px; background: rgba(255,255,255,0.15); padding: 2px 8px; border-radius: 10px; }
  table { width: 100%; border-collapse: collapse; }
  thead tr { background: #3a4d8f; color: #fff; }
  th { padding: 7px 10px; text-align: left; font-size: 11px; }
  td { padding: 6px 10px; border-bottom: 1px solid rgba(0,0,0,0.06); font-size: 11px; }
  @media print {
    body { padding: 12px; }
    .empleado-bloque { page-break-inside: avoid; }
  }
</style>
</head>
<body>
  <div class="portada">
    <h1>${titulo}</h1>
    <p>Archivo: ${archivo} &nbsp;|&nbsp; Generado: ${fechaStr} &nbsp;|&nbsp;
       Nota: se excluyen registros OK, Sin Registros y Exceso de Horas</p>
  </div>

  <div class="resumen">
    <div class="resumen-item"><strong>${conNovedades.length}</strong><span>Empleados con novedades</span></div>
    <div class="resumen-item"><strong>${totalNovs}</strong><span>Total novedades</span></div>
  </div>

  <div class="leyenda">${leyendaHTML}</div>

  ${seccionesHTML}
</body>
</html>`;
}
