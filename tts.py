"""Qwen3-TTS: preset voices (CustomVoice model) and voice cloning (Base model).

Models load once in a background thread; generation is serialized on the GPU with a lock.
"""
import shutil
import subprocess
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

import imageio_ffmpeg
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel, VoiceClonePromptItem

import db
from config import CLONE_MODEL, DEVICE, OUTPUTS_DIR, PRESET_MODEL, TMP_DIR, VOICES_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

_models: dict[str, Qwen3TTSModel] = {}
_state = {"ready": False, "error": None}
_gpu_lock = threading.Lock()
_prompt_cache: dict[str, list[VoiceClonePromptItem]] = {}


# ---------- loading ----------

def _load():
    try:
        for key, name in (("preset", PRESET_MODEL), ("clone", CLONE_MODEL)):
            _models[key] = Qwen3TTSModel.from_pretrained(name, device_map=DEVICE, dtype=torch.bfloat16)
        _state["ready"] = True
    except Exception as e:
        _state["error"] = f"{type(e).__name__}: {e}"


def start_loading():
    threading.Thread(target=_load, daemon=True).start()


def status():
    if not _state["ready"]:
        return {"ready": False, "error": _state["error"]}
    preset = _models["preset"].model
    return {
        "ready": True,
        "error": None,
        "languages": ["auto"] + [l for l in (preset.get_supported_languages() or []) if l.lower() != "auto"],
        "speakers": sorted(preset.get_supported_speakers() or []),
    }


def _require_ready():
    if not _state["ready"]:
        raise RuntimeError(_state["error"] or "Models are still loading, try again in a moment.")


# ---------- helpers ----------

def to_wav(src: Path, dst: Path):
    """Convert any uploaded audio (mp3, m4a, ogg, wav...) to 24 kHz mono WAV."""
    subprocess.run(
        [FFMPEG, "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "24000", str(dst)],
        check=True,
    )


def _save_output(wavs, sr) -> str:
    name = f"{uuid.uuid4().hex}.wav"
    sf.write(OUTPUTS_DIR / name, wavs[0], sr)
    return name


def _ref_args(ref_text: str | None):
    ref_text = (ref_text or "").strip() or None
    # No transcript -> speaker-embedding-only mode (works, lower similarity).
    return ref_text, ref_text is None


# ---------- generation ----------

def generate_preset(text: str, language: str, speaker: str, instruct: str | None) -> str:
    _require_ready()
    with _gpu_lock:
        wavs, sr = _models["preset"].generate_custom_voice(
            text=text, language=language, speaker=speaker, instruct=(instruct or "").strip() or None,
        )
    return _save_output(wavs, sr)


def generate_clone(ref_wav: Path, ref_text: str | None, text: str, language: str) -> str:
    _require_ready()
    ref_text, xvec = _ref_args(ref_text)
    with _gpu_lock:
        wavs, sr = _models["clone"].generate_voice_clone(
            text=text, language=language, ref_audio=str(ref_wav), ref_text=ref_text, x_vector_only_mode=xvec,
        )
    return _save_output(wavs, sr)


def generate_saved(voice_id: str, text: str, language: str) -> str:
    _require_ready()
    items = _load_prompt(voice_id)
    with _gpu_lock:
        wavs, sr = _models["clone"].generate_voice_clone(text=text, language=language, voice_clone_prompt=items)
    return _save_output(wavs, sr)


# ---------- saved voices ----------

def save_voice(name: str, ref_wav: Path, ref_text: str | None) -> dict:
    _require_ready()
    ref_text, xvec = _ref_args(ref_text)
    voice_id = uuid.uuid4().hex[:12]
    folder = VOICES_DIR / voice_id
    folder.mkdir()
    shutil.copy(ref_wav, folder / "ref.wav")
    with _gpu_lock:
        items = _models["clone"].create_voice_clone_prompt(
            ref_audio=str(folder / "ref.wav"), ref_text=ref_text, x_vector_only_mode=xvec,
        )
    torch.save({"items": [asdict(it) for it in items]}, folder / "prompt.pt")
    db.add_voice(voice_id, name, ref_text, xvec)
    return db.get_voice(voice_id)


def delete_voice(voice_id: str):
    db.delete_voice(voice_id)
    _prompt_cache.pop(voice_id, None)
    shutil.rmtree(VOICES_DIR / voice_id, ignore_errors=True)


def _load_prompt(voice_id: str) -> list[VoiceClonePromptItem]:
    if voice_id not in _prompt_cache:
        path = VOICES_DIR / voice_id / "prompt.pt"
        if not path.exists():
            raise FileNotFoundError("Voice not found.")
        payload = torch.load(path, map_location="cpu", weights_only=True)
        _prompt_cache[voice_id] = [VoiceClonePromptItem(**d) for d in payload["items"]]
    return _prompt_cache[voice_id]


def temp_path(suffix: str) -> Path:
    return TMP_DIR / f"{uuid.uuid4().hex}{suffix}"
