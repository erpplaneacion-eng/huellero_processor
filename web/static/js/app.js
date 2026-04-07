/**
 * Frontend Logistica: carga de Excel y descarga de resultado.
 */

document.addEventListener('DOMContentLoaded', function () {
    if (typeof AREA_CONFIG === 'undefined') return;

    const fileInput            = document.getElementById('fileInput');
    const btnSeleccionarArchivo = document.getElementById('btnSeleccionarArchivo');
    const btnProcesarArchivo   = document.getElementById('btnProcesarArchivo');
    const cargaModal           = document.getElementById('cargaModal');
    const archivoSeleccionado  = document.getElementById('archivoSeleccionado');
    const cargaEstado          = document.getElementById('cargaEstado');
    const cargaResumen         = document.getElementById('cargaResumen');
    const resultSection        = document.getElementById('resultSection');

    let selectedFile   = null;
    let estadoInterval = null;

    // ── Estado del modal ─────────────────────────────────────────────────────

    function setEstadoCarga(message, kind) {
        if (!cargaEstado) return;
        cargaEstado.className = 'carga-modal__estado' + (kind ? ` carga-modal__estado--${kind}` : '');
        cargaEstado.textContent = message || '';
    }

    function setArchivoSeleccionado(file) {
        if (!archivoSeleccionado) return;
        archivoSeleccionado.textContent = file ? `Archivo: ${file.name}` : '';
    }

    function iniciarEstadoProcesando() {
        let dots = 0;
        if (estadoInterval) clearInterval(estadoInterval);
        setEstadoCarga('Procesando archivo, por favor espera', 'info');
        estadoInterval = setInterval(() => {
            dots = (dots + 1) % 4;
            setEstadoCarga(`Procesando archivo, por favor espera${'.'.repeat(dots)}`, 'info');
        }, 500);
    }

    function detenerEstadoProcesando() {
        if (estadoInterval) { clearInterval(estadoInterval); estadoInterval = null; }
    }

    function abrirModalCarga() {
        if (!cargaModal) return;
        cargaModal.classList.add('carga-modal--open');
        cargaModal.setAttribute('aria-hidden', 'false');
    }

    function cerrarModalCarga() {
        if (!cargaModal) return;
        cargaModal.classList.remove('carga-modal--open');
        cargaModal.setAttribute('aria-hidden', 'true');
        detenerEstadoProcesando();
        selectedFile = null;
        if (fileInput) fileInput.value = '';
        if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
        setArchivoSeleccionado(null);
        setEstadoCarga('', '');
        if (cargaResumen) cargaResumen.innerHTML = '';
    }

    // ── Resultado post-procesamiento ─────────────────────────────────────────

    function mostrarResultado(result) {
        if (!resultSection) return;

        const stats         = result.stats || {};
        const urlBase       = AREA_CONFIG.apiDescargar;
        const urlPrincipal  = result.archivo       ? urlBase + result.archivo + '/'       : null;
        const urlCasos      = result.archivo_casos ? urlBase + result.archivo_casos + '/' : null;
        const duplicados    = Number(stats.duplicados_eliminados || 0);

        const alertaDuplicados = duplicados > 0
            ? `<div class="result-alert">⚠ Se detectaron y eliminaron ${duplicados} marcaciones duplicadas.</div>`
            : '';

        resultSection.innerHTML = `
            <div class="result-card">
                <div class="result-card__icon">✅</div>
                <h2 class="result-card__title">Archivo procesado exitosamente</h2>
                ${alertaDuplicados}
                <ul class="result-card__stats">
                    <li><strong>${Number(stats.empleados_unicos || 0)}</strong> empleados</li>
                    <li><strong>${Number(stats.total_registros || 0)}</strong> registros</li>
                    <li><strong>${Number(stats.duplicados_eliminados || 0)}</strong> duplicados eliminados</li>
                    <li><strong>${Number(stats.estados_inferidos || 0)}</strong> estados inferidos</li>
                </ul>
                <div class="result-card__actions">
                    ${urlPrincipal ? `<a href="${urlPrincipal}" class="btn btn--success" download>⬇ Descargar reporte Excel</a>` : ''}
                    ${urlCasos    ? `<a href="${urlCasos}"     class="btn btn--primary" download>📋 Descargar casos de revisión</a>` : ''}
                    <button class="btn btn--secondary" onclick="abrirModalCarga()">🔄 Procesar otro archivo</button>
                </div>
            </div>
        `;
        resultSection.style.display = 'block';
    }

    // ── Procesamiento ────────────────────────────────────────────────────────

    async function procesarArchivo() {
        if (!selectedFile) {
            setEstadoCarga('Selecciona un archivo primero.', 'error');
            return;
        }

        if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
        iniciarEstadoProcesando();

        const formData = new FormData();
        formData.append('archivo', selectedFile);
        formData.append('usar_maestro', 'true');
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
            } catch (_e) {
                throw new Error('El servidor respondió con un formato no esperado.');
            }

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Error durante el procesamiento.');
            }

            // Cerrar modal y mostrar resultado
            cerrarModalCarga();
            mostrarResultado(result);

        } catch (error) {
            if (error && error.name === 'AbortError') {
                setEstadoCarga('El procesamiento tardó demasiado (timeout 5 min). Intenta con un archivo más pequeño.', 'error');
            } else {
                setEstadoCarga(error.message || 'Error de conexión con el servidor.', 'error');
            }
        } finally {
            if (timeoutId) clearTimeout(timeoutId);
            detenerEstadoProcesando();
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
        }
    }

    // ── Eventos ──────────────────────────────────────────────────────────────

    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files && e.target.files.length > 0 ? e.target.files[0] : null;
            if (!file) return;

            const lower = file.name.toLowerCase();
            if (!lower.endsWith('.xls') && !lower.endsWith('.xlsx')) {
                selectedFile = null;
                if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
                setArchivoSeleccionado(null);
                setEstadoCarga('Formato inválido. Usa .xls o .xlsx.', 'error');
                return;
            }

            selectedFile = file;
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
            setArchivoSeleccionado(file);
            setEstadoCarga('', '');
        });
    }

    if (btnSeleccionarArchivo) {
        btnSeleccionarArchivo.addEventListener('click', function () {
            if (fileInput) { fileInput.value = ''; fileInput.click(); }
        });
    }

    if (btnProcesarArchivo) {
        btnProcesarArchivo.addEventListener('click', procesarArchivo);
    }

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && cargaModal && cargaModal.classList.contains('carga-modal--open')) {
            cerrarModalCarga();
        }
    });

    window.abrirModalCarga  = abrirModalCarga;
    window.cerrarModalCarga = cerrarModalCarga;
});
