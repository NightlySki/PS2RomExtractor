import os
import tempfile
import logging
from flask import Flask, request, jsonify, send_file, render_template, session, json
from werkzeug.utils import secure_filename
from flask_babel import Babel, gettext as _
from ps2_rom_unpacker import PS2ROMUnpacker
import gettext as python_gettext

# Configurar logging 
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "dev_key" #Added default for dev
babel = Babel(app)

# Configuración de Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'es'
app.config['LANGUAGES'] = {
    'es': 'Español',
    'en': 'English',
    'de': 'Deutsch',
    'fr': 'Français',
    'ja': '日本語',
    'zh': '中文',
    'pt': 'Português',
    'it': 'Italiano'
}

# Configuración de archivos temporales
TEMP_DIR = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'.bin', '.rom0'}

def get_locale():
    # Try to get language from URL parameter
    lang = request.args.get('lang')
    if lang and lang in app.config['LANGUAGES']:
        session['lang'] = lang
        return lang

    # Try to get language from session
    if 'lang' in session:
        return session['lang']

    # Try to get language from browser
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys())

# Inyectar get_locale en el contexto de la plantilla
@app.context_processor
def inject_functions():
    return {
        'get_locale': get_locale,
        'languages': app.config['LANGUAGES']
    }

babel.init_app(app, locale_selector=get_locale)

@app.route('/static/translations/<lang>.json')
def get_translations(lang):
    """Endpoint para servir traducciones al frontend"""
    if lang not in app.config['LANGUAGES']:
        return jsonify({}), 404

    try:
        translations_dir = os.path.join('translations', lang, 'LC_MESSAGES')
        mo_file = os.path.join(translations_dir, 'messages.mo')

        if not os.path.exists(mo_file):
            logger.warning(f"No se encontró el archivo de traducciones para {lang}")
            return jsonify({}), 404

        # Cargar traducciones usando gettext nativo de Python con fallback=False
        translator = python_gettext.translation('messages', 'translations', languages=[lang], fallback=False)

        # Diccionario con todas las cadenas que necesitamos traducir
        strings_to_translate = {
            'Desempaquetador de ROM de PS2': 'Desempaquetador de ROM de PS2',
            'Selecciona tu archivo ROM de PS2 (.bin o .rom0)': 'Selecciona tu archivo ROM de PS2 (.bin o .rom0)',
            'Arrastra tu archivo o haz clic para cargarlo': 'Arrastra tu archivo o haz clic para cargarlo',
            'Se procesará automáticamente el volcado de la BIOS': 'Se procesará automáticamente el volcado de la BIOS',
            'Mostrar Opciones': 'Mostrar Opciones',
            'Extraer TODOS los Módulos': 'Extraer TODOS los Módulos',
            'No se envió ningún archivo': 'No se envió ningún archivo',
            'Nombre de archivo vacío': 'Nombre de archivo vacío',
            'El archivo debe tener extensión .bin o .rom0': 'El archivo debe tener extensión .bin o .rom0',
            'Archivo ROM no encontrado': 'Archivo ROM no encontrado',
            'ROM cargada correctamente!': 'ROM cargada correctamente!',
            'Por favor carga una ROM primero': 'Por favor carga una ROM primero',
            'Error': 'Error',
            'Offset': 'Offset',
            'Tamaño': 'Tamaño'
        }

        # Traducir cada cadena usando el traductor específico del idioma
        translations = {}
        for key in strings_to_translate:
            try:
                translations[key] = translator.gettext(key)
            except Exception as e:
                logger.error(f"Error translating '{key}': {str(e)}")
                translations[key] = key

        return jsonify(translations)

    except Exception as e:
        logger.error(f"Error serving translations: {str(e)}")
        return jsonify({}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_rom():
    if 'file' not in request.files:
        return jsonify({'error': _('No se envió ningún archivo')}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': _('Nombre de archivo vacío')}), 400

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': _('El archivo debe tener extensión .bin o .rom0')}), 400

    try:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(TEMP_DIR, filename)
        file.save(temp_path)

        logger.debug(f"Archivo guardado en: {temp_path}")

        unpacker = PS2ROMUnpacker(temp_path)
        modules = unpacker.get_modules()

        modules_json = [
            {
                'index': m.index,
                'name': m.name,
                'offset': m.offset,
                'size': m.size,
                'size_padded': m.size_padded
            }
            for m in modules
        ]

        return jsonify({
            'success': True,
            'modules': modules_json,
            'temp_file': filename
        })

    except Exception as e:
        logger.error(f"Error procesando ROM: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/extract/<filename>/<int:module_index>')
def extract_module(filename, module_index):
    try:
        temp_path = os.path.join(TEMP_DIR, secure_filename(filename))
        if not os.path.exists(temp_path):
            return jsonify({'error': _('Archivo ROM no encontrado')}), 404

        unpacker = PS2ROMUnpacker(temp_path)
        module_data = unpacker.extract_module(module_index)
        modules = unpacker.get_modules()
        module_name = modules[module_index].name

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(module_data)
            tmp_path = tmp.name

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f"{module_index}_{module_name}.bin",
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"Error extrayendo módulo: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)