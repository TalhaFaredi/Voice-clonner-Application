# Voice Cloner Application

> Legacy application guide. For the new standalone Sonora SaaS, see [voice-clone-saas](../voice-clone-saas/README.md).

A local Flask web app for creating short-form video assets:

- **Voice generation** with [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
  - **Preset voices**: 9 built-in speakers with optional style instructions ("Very happy", "Speak slowly and calmly").
  - **Voice cloning**: clone any voice from a short clip (MP3, WAV, M4A, OGG…).
  - **Saved voices**: store cloned voices in SQLite and reuse them without re-uploading.
- **YouTube extractor**: paste a link and get the transcript plus frames from the video.

Everything runs on your own machine. No API keys are needed.

## Screenshots

| Preset voices | Clone a voice |
|---|---|
| ![Preset voices](screenshots/preset-voices.png) | ![Clone a voice](screenshots/clone-voice.png) |

| Saved voices | YouTube extractor |
|---|---|
| ![Saved voices](screenshots/saved-voices.png) | ![YouTube extractor](screenshots/youtube.png) |

## Requirements

- **NVIDIA GPU** with CUDA. Both voice models together need roughly 10 GB of free VRAM.
- **Python 3.12** (uv installs it for you).
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** package manager.
- About **10 GB of free disk** for the model downloads.

ffmpeg is bundled through the `imageio-ffmpeg` package, so you don't need to install it separately.

## Install and run

```bash
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync          # creates .venv and installs everything, including CUDA PyTorch
uv run app.py
```

Open **http://127.0.0.1:5000**.

On start, the voice models load in the background. The voice buttons stay disabled until the models are ready. The YouTube extractor works right away.

## How the models are downloaded and cached

The app uses two models from Hugging Face:

| Used for | Model | Setting |
|---|---|---|
| Preset voices | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `PRESET_MODEL` |
| Voice cloning | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | `CLONE_MODEL` |

- **First start:** nothing to do by hand. On the first `uv run app.py`, both models download automatically. They are several GB each, so the first start takes a few minutes, depending on your connection.
- **Cache location:** the standard Hugging Face cache.
  - Windows: `C:\Users\<you>\.cache\huggingface\hub\`
  - Linux / macOS: `~/.cache/huggingface/hub/`
- **Later starts:** the models load from the cache with no download. Startup takes about a minute while they load onto the GPU.
- **Moving the cache:** set `HF_HOME` before starting, for example `HF_HOME=D:\hf-cache`.
- **Downloading ahead of time** (optional):
  ```bash
  uv run python -c "from huggingface_hub import snapshot_download as d; d('Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice'); d('Qwen/Qwen3-TTS-12Hz-1.7B-Base')"
  ```
- **Running offline:** after the first download, set `HF_HUB_OFFLINE=1` to stop any network checks.
- **Smaller model:** for a GPU with less memory, use the 0.6B cloning model: `CLONE_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-Base`. It uses less VRAM and gives lower quality.

## Configuration

Set these as environment variables before `uv run app.py`:

| Variable | Default | Purpose |
|---|---|---|
| `PRESET_MODEL` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | Model for preset voices |
| `CLONE_MODEL` | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | Model for cloning and saved voices |
| `TTS_DEVICE` | `cuda:0` | GPU to use |
| `HF_HOME` | Hugging Face default | Where models are cached |

## Using the app

**Preset voices**: type text, pick a speaker and language, and optionally add a style instruction.

**Clone a voice**
1. Upload a clean clip of 3 seconds or more, with one speaker and little background noise.
2. Type exactly what the clip says. This is recommended: leaving it empty clones from the voice only, which sounds less similar.
3. Type the new text, then click **Clone & generate**.
4. To keep the voice, give it a name in **Save this voice as**.

**Saved voices**: click **Use** on a voice, type text, and click **Generate**. Each voice has a preview player and a delete button.

**Note on emotion:** style instructions only work with preset voices. The cloning model (`Base`) doesn't support them. To get a cloned voice in a certain mood, record the reference clip in that mood and save one voice per mood.

## Where data is stored

Everything is in `data/`, which is git-ignored:

```
data/
├── app.db             SQLite: saved voice records
├── voices/<id>/
│   ├── ref.wav        reference clip (converted to 24 kHz mono)
│   └── prompt.pt      precomputed voice prompt (fast reuse)
├── outputs/           generated audio (.wav)
├── jobs/              YouTube frames (last 5 runs kept)
└── tmp/               temporary uploads
```

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Flask routes |
| `tts.py` | Qwen3-TTS loading, preset generation, cloning, saved voices |
| `db.py` | SQLite access |
| `youtube.py` | YouTube transcript and frame extraction |
| `config.py` | Paths, model names, device |
| `index.html` | Web page (vanilla HTML/JS) |
| `pyproject.toml` / `uv.lock` | Dependencies |
| `specs/v1.md` | v1 spec (YouTube extractor) |

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/tts/status` | – | `ready`, `languages`, `speakers` |
| POST | `/api/tts/preset` | JSON: `text`, `speaker`, `language`, `instruct?` | `audio_url` |
| POST | `/api/tts/clone` | form: `audio`, `text`, `ref_text?`, `language`, `save_name?` | `audio_url`, `voice?` |
| GET | `/api/voices` | – | list of saved voices |
| POST | `/api/voices` | form: `name`, `audio`, `ref_text?` | saved voice |
| POST | `/api/voices/<id>/generate` | JSON: `text`, `language` | `audio_url` |
| DELETE | `/api/voices/<id>` | – | `ok` |
| POST | `/api/extract` | JSON: `url`, `interval?` | transcript and frames |

## Troubleshooting

- **"An Application Control policy has blocked this file" (Windows):** Smart App Control is blocking the Python or PyTorch files. Turn it off in *Windows Security → App & browser control → Smart App Control*. On many Windows versions it can't be turned back on without resetting Windows.
- **Voice buttons stay disabled:** the models are still downloading or loading. Watch the console. The page shows an error if loading fails.
- **CUDA out of memory:** close other GPU apps, or switch to the 0.6B cloning model (see above).
- **Slow generation on Windows:** FlashAttention isn't available on Windows, so the app uses PyTorch's default attention. It works, a little slower.
