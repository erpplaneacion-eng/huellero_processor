/**
 * Frontend Logistica: dashboard por defecto + carga de Excel en modal.
 */

document.addEventListener('DOMContentLoaded', function () {
    if (typeof AREA_CONFIG === 'undefined') return;

    const fileInput = document.getElementById('fileInput');
    const btnSeleccionarArchivo = document.getElementById('btnSeleccionarArchivo');
    const btnProcesarArchivo = document.getElementById('btnProcesarArchivo');
    const cargaModal = document.getElementById('cargaModal');
    const archivoSeleccionado = document.getElementById('archivoSeleccionado');
    const cargaEstado = document.getElementById('cargaEstado');
    const cargaResumen = document.getElementById('cargaResumen');
    const dashboardSection = document.getElementById('dashboardSection');

    let selectedFile = null;
    let estadoInterval = null;

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
        if (estadoInterval) {
            clearInterval(estadoInterval);
            estadoInterval = null;
        }
    }

    function clearResumenCarga() {
        if (!cargaResumen) return;
        cargaResumen.innerHTML = '';
        cargaResumen.classList.remove('is-visible');
    }

    function safeText(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function mostrarResumenCarga(result) {
        if (!cargaResumen) return;

        const stats = result.stats || {};
        const dbStats = result.db_stats || {};
        const duplicados = Number(stats.duplicados_eliminados || 0);
        const alertaDuplicados = duplicados > 0
            ? `<div class="carga-modal__alerta">⚠ Se detectaron y eliminaron ${duplicados} duplicados en este archivo.</div>`
            : '';

        cargaResumen.innerHTML = `
            ${alertaDuplicados}
            <ul>
                <li><strong>Empleados:</strong> ${Number(stats.empleados_unicos || 0)}</li>
                <li><strong>Registros:</strong> ${Number(stats.total_registros || 0)}</li>
                <li><strong>Duplicados eliminados:</strong> ${duplicados}</li>
                <li><strong>Estados inferidos:</strong> ${Number(stats.estados_inferidos || 0)}</li>
                <li><strong>BD nuevos:</strong> ${Number(dbStats.creados || 0)} | <strong>existentes:</strong> ${Number(dbStats.existentes || 0)} | <strong>errores:</strong> ${Number(dbStats.errores || 0)}</li>
            </ul>
        `;
        cargaResumen.classList.add('is-visible');
    }

    function validarExtension(fileName) {
        const lower = (fileName || '').toLowerCase();
        return lower.endsWith('.xls') || lower.endsWith('.xlsx');
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
        clearResumenCarga();
    }

    async function cargarDashboardDesdeBD() {
        if (!dashboardSection) return;
        dashboardSection.innerHTML = `
            <div class="card">
                <h2 class="card__title"><span class="card__title-icon">⏳</span>Cargando dashboard...</h2>
                <p class="result__message">Consultando registros procesados.</p>
            </div>
        `;

        try {
            const response = await fetch(AREA_CONFIG.apiListarRegistros, { method: 'GET' });
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'No fue posible cargar registros.');
            }

            renderizarDashboard(result, AREA_CONFIG);
        } catch (error) {
            dashboardSection.innerHTML = `
                <div class="card result--error">
                    <div class="result__icon">❌</div>
                    <div class="result__title">No se pudo cargar el dashboard</div>
                    <div class="result__error">${error.message}</div>
                    <div class="result__actions">
                        <button class="btn btn--primary" onclick="recargarDashboard()">Reintentar</button>
                    </div>
                </div>
            `;
        }
    }

    async function procesarArchivo() {
        if (!selectedFile) {
            setEstadoCarga('Selecciona un archivo primero.', 'error');
            return;
        }

        if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
        iniciarEstadoProcesando();
        clearResumenCarga();

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

            let result = null;
            try {
                result = await response.json();
            } catch (_e) {
                throw new Error('El servidor respondió con un formato no esperado.');
            }

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Error durante el procesamiento.');
            }

            renderizarDashboard(result, AREA_CONFIG);
            mostrarResumenCarga(result);

            // Cuenta regresiva y cierre automático para que el usuario
            // pueda leer el resumen y luego ver los botones en el dashboard
            let seg = 5;
            const tick = setInterval(() => {
                seg--;
                setEstadoCarga(`✔ Procesado. Cerrando en ${seg}s…`, 'success');
                if (seg <= 0) {
                    clearInterval(tick);
                    cerrarModalCarga();
                }
            }, 1000);
            setEstadoCarga(`✔ Procesado. Cerrando en ${seg}s…`, 'success');
        } catch (error) {
            if (error && error.name === 'AbortError') {
                setEstadoCarga('El procesamiento tardó demasiado (timeout de 5 minutos). Intenta con un archivo más pequeño o revisa logs.', 'error');
            } else {
                setEstadoCarga(error.message || 'Error de conexion con el servidor.', 'error');
            }
        } finally {
            if (timeoutId) clearTimeout(timeoutId);
            detenerEstadoProcesando();
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
        }
    }

    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files && e.target.files.length > 0 ? e.target.files[0] : null;
            if (!file) return;

            if (!validarExtension(file.name)) {
                selectedFile = null;
                if (btnProcesarArchivo) btnProcesarArchivo.disabled = true;
                setArchivoSeleccionado(null);
                setEstadoCarga('Formato invalido. Usa .xls o .xlsx.', 'error');
                clearResumenCarga();
                return;
            }

            selectedFile = file;
            if (btnProcesarArchivo) btnProcesarArchivo.disabled = false;
            setArchivoSeleccionado(file);
            setEstadoCarga('', '');
            clearResumenCarga();
        });
    }

    if (btnSeleccionarArchivo) {
        btnSeleccionarArchivo.addEventListener('click', function () {
            if (fileInput) {
                fileInput.value = '';
                fileInput.click();
            }
        });
    }

    if (btnProcesarArchivo) {
        btnProcesarArchivo.addEventListener('click', procesarArchivo);
    }

    window.abrirModalCarga = abrirModalCarga;
    window.cerrarModalCarga = cerrarModalCarga;
    window.cargarOtroArchivo = abrirModalCarga;
    window.recargarDashboard = cargarDashboardDesdeBD;

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && cargaModal && cargaModal.classList.contains('carga-modal--open')) {
            cerrarModalCarga();
        }
    });

    cargarDashboardDesdeBD();
});
