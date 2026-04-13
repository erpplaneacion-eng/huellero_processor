/**
 * Frontend Logistica: carga de Excel y descarga de resultado.
 */

document.addEventListener('DOMContentLoaded', function () {
    if (typeof AREA_CONFIG === 'undefined') return;

    const fileInput              = document.getElementById('fileInput');
    const fileInput2             = document.getElementById('fileInput2');
    const btnSeleccionarArchivo  = document.getElementById('btnSeleccionarArchivo');
    const btnSeleccionarArchivo2 = document.getElementById('btnSeleccionarArchivo2');
    const btnProcesarArchivo     = document.getElementById('btnProcesarArchivo');
    const modal                  = document.getElementById('cargaModal');
    const archivoSeleccionado    = document.getElementById('archivoSeleccionado');
    const archivoSeleccionado2   = document.getElementById('archivoSeleccionado2');
    const estadoEl               = document.getElementById('cargaEstado');
    const fechaInicioEl          = document.getElementById('fechaInicio');
    const fechaFinEl             = document.getElementById('fechaFin');
    const uploadSection          = document.getElementById('uploadSection');
    const resultSection          = document.getElementById('resultSection');

    let selectedFile   = null;
    let selectedFile2  = null;
    let estadoInterval = null;

    // ── Helpers de estado ────────────────────────────────────────────────────

    function setEstado(message, kind) {
        if (!estadoEl) return;
        estadoEl.className = 'modal__estado' + (kind ? ` modal__estado--${kind}` : '');
        estadoEl.textContent = message || '';
    }

    function iniciarProcesando() {
        let dots = 0;
        if (estadoInterval) clearInterval(estadoInterval);
        setEstado('Procesando archivo, por favor espera', 'info');
        estadoInterval = setInterval(() => {
            dots = (dots + 1) % 4;
            setEstado(`Procesando archivo, por favor espera${'.'.repeat(dots)}`, 'info');
        }, 500);
    }

    function detenerProcesando() {
        if (estadoInterval) { clearInterval(estadoInterval); estadoInterval = null; }
    }

    // ── Modal ────────────────────────────────────────────────────────────────

    function abrirModal() {
        if (!modal) return;
        modal.classList.add('modal--open');
        modal.setAttribute('aria-hidden', 'false');
    }

    function cerrarModal() {
        if (!modal) return;
        modal.classList.remove('modal--open');
        modal.setAttribute('aria-hidden', 'true');
        detenerProcesando();
        selectedFile  = null;
        selectedFile2 = null;
        if (fileInput)  fileInput.value  = '';
        if (fileInput2) fileInput2.value = '';
        if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
        if (archivoSeleccionado)  archivoSeleccionado.textContent  = '';
        if (archivoSeleccionado2) archivoSeleccionado2.textContent = '';
        if (fechaInicioEl) fechaInicioEl.value = '';
        if (fechaFinEl) fechaFinEl.value = '';
        if (fechaInicioEl) fechaInicioEl.max = '';
        if (fechaFinEl) {
            fechaFinEl.min = '';
            fechaFinEl.max = '';
        }
        setEstado('');
    }

    // ── Resultado ────────────────────────────────────────────────────────────

    function mostrarResultado(result) {
        if (!resultSection) return;

        const stats        = result.stats || {};
        const urlBase      = AREA_CONFIG.apiDescargar;
        const urlPrincipal = result.archivo       ? urlBase + result.archivo + '/'       : null;
        const urlCasos     = result.archivo_casos ? urlBase + result.archivo_casos + '/' : null;
        const duplicados   = Number(stats.duplicados_eliminados || 0);

        const alertaHtml = duplicados > 0
            ? `<div class="result-card__alert">⚠ Se eliminaron ${duplicados} marcaciones duplicadas en el archivo.</div>`
            : '';

        resultSection.innerHTML = `
            <div class="result-card">
                <div class="result-card__icon">✅</div>
                <h2 class="result-card__title">Archivo procesado correctamente</h2>
                ${alertaHtml}
                <div class="result-card__stats">
                    <div class="stat-item">
                        <span class="stat-item__value">${Number(stats.empleados_unicos || 0)}</span>
                        <span class="stat-item__label">Empleados</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-item__value">${Number(stats.total_registros || 0)}</span>
                        <span class="stat-item__label">Registros</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-item__value">${Number(stats.duplicados_eliminados || 0)}</span>
                        <span class="stat-item__label">Duplicados eliminados</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-item__value">${Number(stats.estados_inferidos || 0)}</span>
                        <span class="stat-item__label">Estados inferidos</span>
                    </div>
                </div>
                <div class="result-card__actions">
                    ${urlPrincipal ? `<a href="${urlPrincipal}" class="btn btn--success" download>⬇ Descargar reporte Excel</a>` : ''}
                    ${urlCasos    ? `<a href="${urlCasos}"     class="btn btn--outline"  download>📋 Casos de revisión</a>`     : ''}
                    <button class="btn btn--ghost" onclick="abrirModalCarga()">🔄 Procesar otro archivo</button>
                </div>
            </div>
        `;

        if (uploadSection) uploadSection.style.display = 'none';
        resultSection.style.display = 'block';
    }

    // ── Procesamiento ────────────────────────────────────────────────────────

    async function procesarArchivo() {
        if (!selectedFile) {
            setEstado('Selecciona un archivo primero.', 'error');
            return;
        }

        const fechaInicio = fechaInicioEl?.value || '';
        const fechaFin = fechaFinEl?.value || '';
        if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
            setEstado('La fecha inicio no puede ser mayor que la fecha final.', 'error');
            return;
        }

        if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
        iniciarProcesando();

        const formData = new FormData();
        formData.append('archivo', selectedFile);
        if (selectedFile2) formData.append('archivo2', selectedFile2);
        formData.append('usar_maestro', 'true');
        if (fechaInicio) formData.append('fecha_inicio', fechaInicio);
        if (fechaFin) formData.append('fecha_fin', fechaFin);

        let timeoutId = null;

        try {
            const controller = new AbortController();
            timeoutId = setTimeout(() => controller.abort(), 300000);

            const response = await fetch(AREA_CONFIG.apiProcesar, {
                method: 'POST',
                body: formData,
                signal: controller.signal,
            });
            clearTimeout(timeoutId);

            let result;
            try {
                result = await response.json();
            } catch {
                throw new Error('El servidor respondió con un formato inesperado.');
            }

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Error durante el procesamiento.');
            }

            cerrarModal();
            mostrarResultado(result);

        } catch (error) {
            if (error?.name === 'AbortError') {
                setEstado('Tiempo de espera agotado (5 min). Intenta con un archivo más pequeño.', 'error');
            } else {
                setEstado(error.message || 'Error de conexión con el servidor.', 'error');
            }
        } finally {
            if (timeoutId) clearTimeout(timeoutId);
            detenerProcesando();
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
        }
    }

    // ── Eventos ──────────────────────────────────────────────────────────────

    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files?.[0] ?? null;
            if (!file) return;

            const lower = file.name.toLowerCase();
            if (!lower.endsWith('.xls') && !lower.endsWith('.xlsx')) {
                selectedFile = null;
                if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
                if (archivoSeleccionado) archivoSeleccionado.textContent = '';
                setEstado('Formato inválido. Usa .xls o .xlsx.', 'error');
                return;
            }

            selectedFile = file;
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
            if (archivoSeleccionado) archivoSeleccionado.textContent = `📄 ${file.name}`;
            setEstado('');
        });
    }

    if (fileInput2) {
        fileInput2.addEventListener('change', function (e) {
            const file = e.target.files?.[0] ?? null;
            if (!file) return;

            const lower = file.name.toLowerCase();
            if (!lower.endsWith('.xls') && !lower.endsWith('.xlsx')) {
                selectedFile2 = null;
                if (archivoSeleccionado2) archivoSeleccionado2.textContent = '';
                setEstado('Archivo 2: formato inválido. Usa .xls o .xlsx.', 'error');
                return;
            }

            selectedFile2 = file;
            if (archivoSeleccionado2) archivoSeleccionado2.textContent = `📄 ${file.name}`;
            setEstado('');
        });
    }

    if (btnSeleccionarArchivo) {
        btnSeleccionarArchivo.addEventListener('click', () => {
            if (fileInput) { fileInput.value = ''; fileInput.click(); }
        });
    }

    if (btnSeleccionarArchivo2) {
        btnSeleccionarArchivo2.addEventListener('click', () => {
            if (fileInput2) { fileInput2.value = ''; fileInput2.click(); }
        });
    }

    if (btnProcesarArchivo) {
        btnProcesarArchivo.addEventListener('click', procesarArchivo);
    }

    if (fechaInicioEl && fechaFinEl) {
        fechaInicioEl.addEventListener('change', () => {
            fechaFinEl.min = fechaInicioEl.value || '';
        });
        fechaFinEl.addEventListener('change', () => {
            fechaInicioEl.max = fechaFinEl.value || '';
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal?.classList.contains('modal--open')) {
            cerrarModal();
        }
    });

    // Exponer para onclick del HTML
    window.abrirModalCarga  = abrirModal;
    window.cerrarModalCarga = cerrarModal;
});
