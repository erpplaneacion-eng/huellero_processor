/**
 * Procesador de Huellero - Frontend
 * Corporación Hacia un Valle Solidario
 */

document.addEventListener('DOMContentLoaded', function() {
    // Verificar si estamos en una página de área (no en home)
    if (typeof AREA_CONFIG === 'undefined') {
        return;
    }

    // Elementos del DOM
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const usarMaestro = document.getElementById('usarMaestro');
    const btnProcesar = document.getElementById('btnProcesar');
    const formSection = document.getElementById('formSection');
    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    const resultSection = document.getElementById('resultSection');

    let selectedFile = null;

    // ========== DRAG & DROP ==========
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // ========== FILE HANDLING ==========
    function handleFileSelect(file) {
        // Validar extensión
        const validExtensions = ['.xls', '.xlsx'];
        const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));

        if (!validExtensions.includes(fileExtension)) {
            alert('Por favor seleccione un archivo Excel (.xls o .xlsx)');
            return;
        }

        selectedFile = file;

        // Actualizar UI
        uploadZone.classList.add('has-file');
        uploadZone.innerHTML = `
            <div class="upload-zone__icon">✅</div>
            <div class="upload-zone__filename">
                📄 ${file.name}
            </div>
            <div class="upload-zone__hint">Clic para cambiar archivo</div>
        `;

        // Habilitar botón
        btnProcesar.disabled = false;
    }

    // ========== PROCESSING ==========
    btnProcesar.addEventListener('click', procesarArchivo);

    async function procesarArchivo() {
        if (!selectedFile) {
            alert('Por favor seleccione un archivo');
            return;
        }

        // Mostrar progreso
        formSection.style.display = 'none';
        progressSection.classList.add('active');
        resultSection.classList.remove('active');

        // Simular progreso inicial
        updateProgress(10, 'Cargando archivo...');

        // Preparar FormData
        const formData = new FormData();
        formData.append('archivo', selectedFile);
        formData.append('usar_maestro', usarMaestro.checked);

        try {
            updateProgress(30, 'Procesando datos...');

            const response = await fetch(AREA_CONFIG.apiProcesar, {
                method: 'POST',
                body: formData
            });

            updateProgress(70, 'Generando reporte...');

            const result = await response.json();

            updateProgress(100, 'Completado');

            // Esperar un momento para mostrar el 100%
            await new Promise(resolve => setTimeout(resolve, 500));

            if (result.success) {
                mostrarResultadoExito(result);
            } else {
                mostrarResultadoError(result.error);
            }

        } catch (error) {
            console.error('Error:', error);
            mostrarResultadoError('Error de conexión con el servidor');
        }
    }

    function updateProgress(percent, status) {
        progressFill.style.width = percent + '%';
        progressStatus.innerHTML = `<span class="progress-status__icon">⏳</span> ${status}`;
    }

    // ========== RESULTS ==========
    function mostrarResultadoExito(result) {
        progressSection.classList.remove('active');
        resultSection.classList.add('active');

        const urlDescarga = AREA_CONFIG.apiDescargar + result.archivo + '/';
        const urlCasos = result.archivo_casos ? AREA_CONFIG.apiDescargar + result.archivo_casos + '/' : null;

        resultSection.innerHTML = `
            <div class="card result--success">
                <div class="result__icon">✅</div>
                <div class="result__title">Procesamiento Completado</div>
                <div class="result__message">El archivo de ${AREA_CONFIG.nombre} ha sido procesado exitosamente</div>

                <div class="result__stats">
                    <div class="result__stat">
                        <span class="result__stat-label">Empleados procesados</span>
                        <span class="result__stat-value">${result.stats.empleados_unicos || 0}</span>
                    </div>
                    <div class="result__stat">
                        <span class="result__stat-label">Total registros</span>
                        <span class="result__stat-value">${result.stats.total_registros || 0}</span>
                    </div>
                    <div class="result__stat">
                        <span class="result__stat-label">Turnos completos</span>
                        <span class="result__stat-value">${result.stats.turnos_completos || 0}</span>
                    </div>
                    <div class="result__stat">
                        <span class="result__stat-label">Turnos incompletos</span>
                        <span class="result__stat-value">${result.stats.turnos_incompletos || 0}</span>
                    </div>
                    <div class="result__stat">
                        <span class="result__stat-label">Estados inferidos</span>
                        <span class="result__stat-value">${result.stats.estados_inferidos || 0}</span>
                    </div>
                </div>

                <div class="result__actions">
                    <a href="${urlDescarga}" class="btn btn--success" download>
                        📥 Descargar Reporte
                    </a>
                    ${urlCasos ? `
                        <a href="${urlCasos}" class="btn btn--primary" download>
                            📋 Descargar Casos de Revisión
                        </a>
                    ` : ''}
                    <button class="btn btn--primary" onclick="location.reload()">
                        🔄 Procesar Otro Archivo
                    </button>
                </div>
            </div>
        `;
    }

    function mostrarResultadoError(error) {
        progressSection.classList.remove('active');
        resultSection.classList.add('active');

        resultSection.innerHTML = `
            <div class="card result--error">
                <div class="result__icon">❌</div>
                <div class="result__title">Error en el Procesamiento</div>
                <div class="result__error">${error}</div>

                <div class="result__actions">
                    <button class="btn btn--primary" onclick="location.reload()">
                        🔄 Intentar de Nuevo
                    </button>
                </div>
            </div>
        `;
    }
});
