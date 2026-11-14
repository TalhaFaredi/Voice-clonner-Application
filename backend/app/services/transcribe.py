"""Speech-to-text for uploaded voice samples using microsoft/mai-transcribe-2 via OpenRouter."""
import base64
import shutil
import tempfile
from pathlib import Path

import requests
from flask import abort, current_app

from .files import validate_sample

OPENROUTER_URL = 'https://openrouter.ai/api/v1/audio/transcriptions'

# Languages offered for the recording. 'auto' omits the language so the model detects it.
TRANSCRIBE_LANGUAGES = {
    'auto': 'Detect automatically',
    'en': 'English', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'de': 'German',
    'fr': 'French', 'ru': 'Russian', 'pt': 'Portuguese', 'es': 'Spanish', 'it': 'Italian',
    'ur': 'Urdu', 'hi': 'Hindi', 'ar': 'Arabic', 'tr': 'Turkish', 'nl': 'Dutch',
}


def transcribe_upload(upload, language='auto'):
    """Normalise the upload with the same checks as cloning, then transcribe it."""
    key = current_app.config['OPENROUTER_API_KEY']
    if not key:
        abort(503, 'Transcription is not configured. Add OPENROUTER_API_KEY to backend/.env.')
    if language not in TRANSCRIBE_LANGUAGES:
        abort(400, 'Choose a supported recording language or automatic detection.')
    workdir = Path(tempfile.mkdtemp(prefix='mellifon-stt-'))
    try:
        duration = validate_sample(upload, workdir)
        audio_b64 = base64.b64encode((workdir / 'reference.wav').read_bytes()).decode('ascii')
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    payload = {'model': current_app.config['TRANSCRIBE_MODEL'],
               'input_audio': {'data': audio_b64, 'format': 'wav'}}
    if language != 'auto':
        payload['language'] = language
    try:
        response = requests.post(OPENROUTER_URL, json=payload, timeout=180,
                                 headers={'Authorization': f'Bearer {key}'})
    except requests.RequestException:
        abort(502, 'Could not reach the transcription service. Check your internet connection.')
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not response.ok:
        message = (result.get('error') or {}).get('message') if isinstance(result.get('error'), dict) else None
        current_app.logger.warning('Transcription failed (%s): %s', response.status_code, message)
        abort(502, f'Transcription failed: {message or "HTTP " + str(response.status_code)}')
    text = (result.get('text') or '').strip()
    if not text:
        abort(422, 'No speech was recognised in this recording.')
    return {'text': text[:4000], 'language': language, 'detected_language': result.get('language'),
            'duration': duration, 'model': current_app.config['TRANSCRIBE_MODEL']}
