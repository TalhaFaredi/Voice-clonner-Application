# Sonora · Voice Clone SaaS

A standalone voice cloning and speech generation platform. Everything needed by the application lives in this directory. It does not import from or call the YouTube application.

**Documentation:** English · [Other languages](docs/i18n/README.md)

**Project status:** voice cloning and speech generation work locally on NVIDIA CUDA. Accounts, private audio, credits, job processing and billing integration are implemented. Live Stripe payments and SMTP delivery still need configuration and end-to-end verification before a public launch.

**Stack:** dependency-free ES module frontend; Flask/Waitress API; SQLite with versioned SQL migrations; independent persistent GPU worker; Qwen3-TTS; Stripe Checkout + Customer Portal; SMTP password resets.

## Start locally (Windows / PowerShell)

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Chrome or Edge for optional browser tests, and a CUDA GPU for practical generation speed. Model weights download into the standard Hugging Face cache; allow approximately 10 GB for models and several GB for PyTorch. CPU is supported with `TTS_DEVICE=cpu` but significantly slower.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application/voice-clone-saas
```

From **this folder**:

```powershell
uv sync --extra worker --extra dev
# First setup only; do not overwrite an existing backend/.env.
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Open three terminals:

```powershell
# API — terminal 1
cd backend
../.venv/Scripts/python.exe run.py
```

```powershell
# Qwen audio worker — terminal 2
cd backend
../.venv/Scripts/python.exe -m app.worker
```

```powershell
# Frontend — terminal 3
cd frontend
../.venv/Scripts/python.exe serve.py
```

Open **http://localhost:5173**. Use the same hostname for frontend and API (both localhost, or both 127.0.0.1) so cookie authentication works. The original app can keep running on port 5000.

| Service | Address / command |
|---|---|
| Frontend | `http://localhost:5173` |
| API health | `http://localhost:8010/api/health` |
| Audio-worker status | `http://localhost:8010/api/studio/options` → `worker.status` |
| Windows launch helper | `./scripts/start.ps1 api`, `./scripts/start.ps1 worker`, `./scripts/start.ps1 frontend` in separate terminals |

The API initializes SQLite and applies migrations automatically. No seed account, default password, API secret, or simulated paid subscription is supplied. Register your own account. Free accounts receive 5,000 one-time credits. The worker must be running to process audio; the API remains responsive while models load.

For API-only development use `uv sync --extra dev` and test with the test engine. For pip users, create a Python 3.12 virtual environment and install `backend/requirements-web.txt`; install `backend/requirements.txt` for the worker, selecting the correct PyTorch wheel for your hardware. `uv.lock` provides the reproducible recommended environment; the CUDA 12.8 index is explicitly configured for Torch/Torchaudio.

## NVIDIA GPU acceleration

The default `TTS_DEVICE=cuda:0` loads both Qwen3-TTS models onto the first NVIDIA CUDA GPU. The API and frontend do not perform model inference; the separate worker performs cloning and speech synthesis. Low GPU utilization while idle is expected.

This installation was verified on an **NVIDIA RTX A6000 with 48 GB VRAM** using the project's CUDA-enabled PyTorch environment. This is the tested hardware, not a minimum hardware requirement or a performance guarantee for other GPUs. Leave GPU-memory headroom for audio generation as well as model weights.

Check your own environment from the `voice-clone-saas` directory:

```powershell
nvidia-smi
./.venv/Scripts/python.exe -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU available')"
```

If CUDA is unavailable, check the NVIDIA driver and installed PyTorch build before starting the worker. For CPU operation, set `TTS_DEVICE=cpu` in `backend/.env` and restart the worker; synthesis will be slower. After any model or device configuration change, restart the worker and wait for a fresh `worker.status: ready` response. Do not start duplicate workers on the same GPU unless you have explicitly provisioned capacity.

## Supported speech languages

The current application exposes the following Qwen3-TTS output languages for presets and saved voice clones:

| Language | Native name | API value |
|---|---|---|
| Chinese | 中文 | `chinese` |
| English | English | `english` |
| Japanese | 日本語 | `japanese` |
| Korean | 한국어 | `korean` |
| German | Deutsch | `german` |
| French | Français | `french` |
| Russian | Русский | `russian` |
| Portuguese | Português | `portuguese` |
| Spanish | Español | `spanish` |
| Italian | Italiano | `italian` |

Choose **Detect automatically** (`auto`) to let the model infer the language from your script. Language selection controls speech generation; it does not translate your script. Write the script in the language you want to hear. Cross-language voice similarity and pronunciation should be evaluated with your own samples. Translated README files describe the same application; they do not add model-language support or translate the interface.

## Features

- Landing/pricing, registration/login/reset, speech studio, private voice library, cloning, audio playback and WAV downloads, generation history, billing/usage, and account settings.
- Argon2 passwords, opaque revocable cookie sessions, CSRF protection, origin allowlist, database-backed rate limits, validated uploads, private ownership-checked audio routes, and no public storage mount.
- WAV/MP3/M4A/OGG/FLAC/WebM samples, 3–120 seconds, 20 MB limit. Voice creation requires consent. Cloned prompts are server-created and loaded with Torch's `weights_only=True`.
- Persistent asynchronous jobs, idempotency keys, atomic credit reservations, one-time refunds on failures, worker heartbeats and stale-job recovery. One credit per script character; 1,000 credits per voice clone. No negative balances.
- Stripe-hosted payments, customer portal upgrades/cancellations, signature-verified webhooks, deduplicated invoice allocations and payment history. Credit grants happen only from verified paid recurring invoices, never from a browser success redirect.

## Configuration, testing and deployment

See [setup and deployment](docs/setup.md), [API reference](docs/api.md), and [verification notes](docs/verification.md). `backend/.env.example` lists all configuration names. Real credentials belong only in `backend/.env` or your deployment secret manager.

```powershell
cd backend
../.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Automated business-logic tests use a fake inference engine and mocked Stripe/SMTP; they do not claim to verify model quality, real card payments or email delivery. Real GPU verification is a separate opt-in command documented in `docs/verification.md`.

Verified during implementation: **13 backend tests**, desktop/mobile browser flows, real GPU preset → saved clone → generated speech, correct credit deductions, and private audio loading in Chrome. The two landing-page audio demonstrations are intentionally public synthetic samples, not uploaded human voices.

## Before a public launch

- Configure Stripe test credentials, all four recurring price IDs, Customer Portal and a verified webhook endpoint. Test payments, renewals, annual credits, failed payments, changes and cancellations.
- Configure SMTP and verify password-reset delivery.
- Deploy behind HTTPS with production cookies, trusted-proxy rate limiting, supervised services, backups and monitoring.
- Review the consent, privacy, retention and accounting policies in the [deployment guide](docs/setup.md).

The voice engine does not need an OpenRouter, NVIDIA API, HeyGen or ElevenLabs API key. It uses the local NVIDIA GPU through PyTorch/CUDA. Stripe and SMTP credentials are separate and must stay in `backend/.env` or a backend secret manager.

## Design and implementation choices

The frontend is buildless and runs independently from the API. GPU inference runs in a separate worker so model loading and synthesis do not block dashboard requests. The application is designed for a self-hosted Python/GPU environment with persistent SQLite storage; serving the frontend alone does not deploy the backend or worker.

Qwen3-TTS is the single integrated speech technology. It was chosen because the existing implementation already uses its multilingual cloning and saved prompts, it avoids a third-party per-request voice API dependency, and its Apache-2.0 release supports this self-hosted architecture. This is an engineering choice, not a claim that it wins every quality/speed benchmark. GPU capacity, voice similarity and consent must be evaluated for your audience. [Official Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS).

This is a production-oriented implementation, not a certification that any installation is production-ready. Public launch requires configured billing/email, HTTPS, backups, monitoring, legal/retention policies, and the deployment checks in the setup guide.
