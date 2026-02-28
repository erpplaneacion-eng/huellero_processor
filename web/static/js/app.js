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

    function setEstadoCarga(message, kind) {
        if (!cargaEstado) return;
        cargaEstado.className = 'carga-modal__estado' + (kind ? ` carga-modal__estado--${kind}` : '');
        cargaEstado.textContent = message || '';
    }

    function setArchivoSeleccionado(file) {
        if (!archivoSeleccionado) return;
        archivoSeleccionado.textContent = file ? `Archivo: ${file.name}` : '';
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
        const nombreArchivo = result.archivo ? safeText(result.archivo) : 'No disponible';
        const nombreCasos = result.archivo_casos ? safeText(result.archivo_casos) : 'No generado';

        cargaResumen.innerHTML = `
            <ul>
                <li><strong>Archivo generado:</strong> ${nombreArchivo}</li>
                <li><strong>Casos revision:</strong> ${nombreCasos}</li>
                <li><strong>Empleados:</strong> ${Number(stats.empleados_unicos || 0)}</li>
                <li><strong>Registros:</strong> ${Number(stats.total_registros || 0)}</li>
                <li><strong>Duplicados eliminados:</strong> ${Number(stats.duplicados_eliminados || 0)}</li>
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
        setEstadoCarga('Procesando archivo, por favor espera...', 'info');
        clearResumenCarga();

        const formData = new FormData();
        formData.append('archivo', selectedFile);
        formData.append('usar_maestro', 'true');

        try {
            const response = await fetch(AREA_CONFIG.apiProcesar, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Error durante el procesamiento.');
            }

            setEstadoCarga('Archivo procesado correctamente.', 'success');
            mostrarResumenCarga(result);
            renderizarDashboard(result, AREA_CONFIG);
        } catch (error) {
            setEstadoCarga(error.message || 'Error de conexion con el servidor.', 'error');
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
