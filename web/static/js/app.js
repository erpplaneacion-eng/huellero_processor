/**
 * Procesador de Huellero - Frontend
 * Corporación Hacia un Valle Solidario
 */

document.addEventListener('DOMContentLoaded', function () {
    // Verificar si estamos en una página de área (no en home)
    if (typeof AREA_CONFIG === 'undefined') {
        return;
    }

    // Elementos del DOM
    const fileInput = document.getElementById('fileInput');
    const inicioSection = document.getElementById('inicioSection');
    const btnSeleccionarArchivo = document.getElementById('btnSeleccionarArchivo');
    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    const resultSection = document.getElementById('resultSection');

    let selectedFile = null;
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }
    if (btnSeleccionarArchivo) {
        btnSeleccionarArchivo.addEventListener('click', abrirSelectorArchivo);
    }

    function handleFileSelect(file) {
        // Validar extensión
        const validExtensions = ['.xls', '.xlsx'];
        const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));

        if (!validExtensions.includes(fileExtension)) {
            alert('Por favor seleccione un archivo Excel (.xls o .xlsx)');
            return;
        }

        selectedFile = file;
        procesarArchivo();
    }

    async function procesarArchivo() {
        if (!selectedFile) {
            abrirSelectorArchivo();
            return;
        }

        // Mostrar progreso
        if (inicioSection) inicioSection.style.display = 'none';
        if (progressSection) progressSection.classList.add('active');
        if (resultSection) resultSection.classList.remove('active');

        // Simular progreso inicial
        updateProgress(10, 'Cargando archivo...');

        // Preparar FormData
        const formData = new FormData();
        formData.append('archivo', selectedFile);
        formData.append('usar_maestro', 'true');

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
        if (progressFill) progressFill.style.width = percent + '%';
        if (progressStatus) {
            progressStatus.innerHTML = `<span class="progress-status__icon">⏳</span> ${status}`;
        }
    }

    function mostrarResultadoExito(result) {
        if (progressSection) progressSection.classList.remove('active');
        if (inicioSection) inicioSection.style.display = 'none';
        renderizarDashboard(result, AREA_CONFIG);
    }

    function mostrarResultadoError(error) {
        if (progressSection) progressSection.classList.remove('active');
        if (!resultSection) return;
        resultSection.classList.add('active');
        if (inicioSection) inicioSection.style.display = 'block';

        resultSection.innerHTML = `
            <div class="card result--error">
                <div class="result__icon">❌</div>
                <div class="result__title">Error en el Procesamiento</div>
                <div class="result__error">${error}</div>
                <div class="result__actions">
                    <button class="btn btn--primary" onclick="cargarOtroArchivo()">
                        📤 Seleccionar Otro Archivo
                    </button>
                </div>
            </div>
        `;
    }

    function abrirSelectorArchivo() {
        if (!fileInput) return;
        fileInput.value = '';
        fileInput.click();
    }

    // Exponer acción para botón "Cargar otro" del dashboard
    window.cargarOtroArchivo = function () {
        if (inicioSection) inicioSection.style.display = 'block';
        abrirSelectorArchivo();
    };
});
