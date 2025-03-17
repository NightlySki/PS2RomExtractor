// Funciones de traducción
let translationsCache = {};
let currentLang = document.documentElement.lang || 'es';
let translations = {};

async function loadTranslations(lang) {
    try {
        // Si ya tenemos las traducciones en caché, usarlas
        if (translationsCache[lang]) {
            translations = translationsCache[lang];
            updateDynamicTexts();
            return;
        }

        const response = await fetch(`/static/translations/${lang}.json`);
        if (!response.ok) {
            throw new Error(`Error loading translations: ${response.statusText}`);
        }

        const newTranslations = await response.json();
        translationsCache[lang] = newTranslations;
        translations = newTranslations;

        // Precargar traducciones de idiomas comunes en segundo plano
        preloadCommonTranslations();

        // Actualizar la interfaz
        updateDynamicTexts();
    } catch (error) {
        console.error('Error loading translations:', error);
        // Fallback a español si hay error
        if (lang !== 'es' && !translations['Desempaquetador de ROM de PS2']) {
            await loadTranslations('es');
        }
    }
}

function _(key) {
    return translations[key] || key;
}

function updateDynamicTexts() {
    // Actualizar título
    const title = document.querySelector('h1');
    if (title) {
        title.textContent = _('Desempaquetador de ROM de PS2');
        document.title = _('Desempaquetador de ROM de PS2');
    }

    // Actualizar instrucciones
    const instructions = document.querySelectorAll('.card-body li');
    if (instructions.length >= 3) {
        instructions[0].textContent = _('Selecciona tu archivo ROM de PS2 (.bin o .rom0)');
        instructions[1].textContent = _('Arrastra tu archivo aquí o haz clic para cargarlo. El programa extraerá todos los módulos internos.');
        instructions[2].textContent = _('Se procesará automáticamente y podrás extraer los módulos que necesites.');
    }

    // Actualizar área de carga
    if (uploadArea) {
        uploadArea.innerHTML = _('Arrastra tu archivo aquí o haz clic para cargarlo. El programa extraerá todos los módulos internos.');
    }

    // Actualizar botones principales
    if (menuBtn) menuBtn.textContent = _('Mostrar Opciones');
    if (extractAllBtn) extractAllBtn.textContent = _('Extraer TODOS los Módulos');

    // Actualizar lista de módulos
    if (!menu.classList.contains('d-none')) {
        const moduleItems = menu.querySelectorAll('.list-group-item');
        moduleItems.forEach(item => {
            const moduleInfo = item.dataset;
            const small = item.querySelector('small');
            if (small) {
                small.innerHTML = `${_('Offset')}: 0x${moduleInfo.offset.toString(16).padStart(8, '0')} | ${_('Tamaño')}: ${moduleInfo.size} bytes`;
            }
        });
    }
}

// Precargar traducciones comunes en segundo plano
async function preloadCommonTranslations() {
    const commonLanguages = ['en', 'es', 'fr', 'ja', 'zh'];
    for (const lang of commonLanguages) {
        if (!translationsCache[lang] && lang !== currentLang) {
            try {
                const response = await fetch(`/static/translations/${lang}.json`);
                if (response.ok) {
                    translationsCache[lang] = await response.json();
                }
            } catch (error) {
                console.error(`Error preloading ${lang} translations:`, error);
            }
        }
    }
}

// Optimizada para cambio de idioma sin recarga
async function changeLanguage(lang) {
    if (lang === currentLang) return;

    // Deshabilitar selector durante el cambio
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) langSelect.disabled = true;

    try {
        // Actualizar idioma
        currentLang = lang;
        document.documentElement.lang = lang;

        // Cargar traducciones y actualizar interfaz
        await loadTranslations(lang);

        // Actualizar URL sin recargar
        const url = new URL(window.location);
        url.searchParams.set('lang', lang);
        window.history.pushState({}, '', url);

    } finally {
        // Habilitar selector
        if (langSelect) langSelect.disabled = false;
    }
}

// Referencias DOM
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const menuBtn = document.getElementById('menuBtn');
const menu = document.getElementById('menu');
const extractAllBtn = document.getElementById('extractAll');

let currentRomFile = null;

// Eventos de arrastrar y soltar
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('bg-dark');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('bg-dark');
});

uploadArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    uploadArea.classList.remove('bg-dark');
    const file = e.dataTransfer.files[0];
    await handleFile(file);
});

// Eventos de clic
uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    await handleFile(file);
});

async function handleFile(file) {
    if (!file || (!file.name.endsWith('.bin') && !file.name.endsWith('.rom0'))) {
        alert(_('El archivo debe tener extensión .bin o .rom0'));
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || _('Error al procesar el archivo'));
        }

        currentRomFile = data.temp_file;
        generateModuleList(data.modules);
        alert(_('ROM cargada correctamente!'));
    } catch (error) {
        alert(`${_('Error')}: ${error.message}`);
    }
}

// Cargar traducciones al iniciar
document.addEventListener('DOMContentLoaded', async () => {
    currentLang = document.documentElement.lang || 'es';
    await loadTranslations(currentLang);
});

// Mensajes de error conocidos
const errorMessages = {
    'No se envió ningún archivo': true,
    'Nombre de archivo vacío': true,
    'El archivo debe tener extensión .bin o .rom0': true,
    'Archivo ROM no encontrado': true,
    'ROM cargada correctamente!': true,
    'Por favor carga una ROM primero': true,
    'Error': true,
    'Error al extraer módulo': true,
    'Error al procesar el archivo': true
};

function generateModuleList(modules) {
    menu.classList.remove('d-none');
    menu.querySelector('.list-group').innerHTML = modules.map(module => `
        <button class="list-group-item list-group-item-action" 
                data-index="${module.index}"
                data-offset="${module.offset}"
                data-size="${module.size}">
            ${module.index}. ${module.name}<br>
            <small>${_('Offset')}: 0x${module.offset.toString(16).padStart(8, '0')} | 
            ${_('Tamaño')}: ${module.size} bytes</small>
        </button>
    `).join('');

    menu.querySelectorAll('.list-group-item').forEach(item => {
        item.addEventListener('click', () => extractModule(item.dataset.index));
    });
}

async function extractModule(index) {
    if (!currentRomFile) {
        alert(_('Por favor carga una ROM primero'));
        return;
    }

    try {
        const response = await fetch(`/api/extract/${currentRomFile}/${index}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || _('Error al extraer módulo'));
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = response.headers.get('content-disposition').split('filename=')[1];
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (error) {
        alert(`${_('Error')}: ${error.message}`);
    }
}


menuBtn.addEventListener('click', () => {
    menu.classList.toggle('d-none');
});

extractAllBtn.addEventListener('click', async () => {
    if (!currentRomFile) {
        alert(_('Por favor carga una ROM primero'));
        return;
    }

    const zip = new JSZip();
    const modules = Array.from(menu.querySelectorAll('.list-group-item'));

    try {
        for (const module of modules) {
            const index = module.dataset.index;
            const response = await fetch(`/api/extract/${currentRomFile}/${index}`);

            if (!response.ok) {
                throw new Error(_('Error al extraer módulo') + ` ${index}`);
            }

            const blob = await response.blob();
            const filename = response.headers.get('content-disposition').split('filename=')[1];
            zip.file(filename, blob);
        }

        const content = await zip.generateAsync({type: "blob"});
        const url = URL.createObjectURL(content);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ps2_modules.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (error) {
        alert(`${_('Error')}: ${error.message}`);
    }
});