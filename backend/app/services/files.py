import subprocess
import uuid
from pathlib import Path
from flask import abort, current_app


def user_dir(user_id, category, identifier=None):
    root = Path(current_app.config['STORAGE']) / 'users' / user_id / category
    if identifier:
        root /= identifier
    root.mkdir(parents=True,exist_ok=True)
    return root


def validate_sample(upload, directory):
    import imageio_ffmpeg
    import soundfile as sf
    extension = Path(upload.filename or '').suffix.lower()
    if extension not in {'.wav','.mp3','.m4a','.ogg','.flac','.webm'}:
        abort(400, 'Upload WAV, MP3, M4A, OGG, FLAC or WebM audio.')
    raw = directory / (uuid.uuid4().hex+extension)
    destination = directory / 'reference.wav'
    try:
        upload.save(raw)
        if raw.stat().st_size > 20*1024*1024:
            abort(413, 'Voice samples must be under 20 MB.')
        demuxer={'.wav':'wav','.mp3':'mp3','.m4a':'mov','.ogg':'ogg','.flac':'flac','.webm':'matroska'}[extension]
        result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error',
                                 '-y','-protocol_whitelist','file,pipe','-f',demuxer,'-i',str(raw),'-t','121','-vn',
                                 '-ac','1','-ar','24000',str(destination)],capture_output=True,timeout=45)
        if result.returncode:
            abort(400, 'This file could not be decoded as audio.')
        info = sf.info(destination)
        if not 3 <= info.duration <= 120:
            abort(400, 'Use a voice sample between 3 seconds and 2 minutes.')
        import numpy as np
        samples,_=sf.read(destination,dtype='float32')
        if float(np.sqrt(np.mean(samples*samples)))<0.0001:
            abort(400,'The recording is silent or too quiet. Upload a clear recording of one speaker.')
        return info.duration
    finally:
        raw.unlink(missing_ok=True)
