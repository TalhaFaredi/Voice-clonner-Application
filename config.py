import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"        # YouTube frames
VOICES_DIR = DATA_DIR / "voices"    # saved voices: <id>/ref.wav + prompt.pt
OUTPUTS_DIR = DATA_DIR / "outputs"  # generated audio
TMP_DIR = DATA_DIR / "tmp"
DB_PATH = DATA_DIR / "app.db"

for d in (JOBS_DIR, VOICES_DIR, OUTPUTS_DIR, TMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

PRESET_MODEL = os.getenv("PRESET_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
CLONE_MODEL = os.getenv("CLONE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
DEVICE = os.getenv("TTS_DEVICE", "cuda:0")
