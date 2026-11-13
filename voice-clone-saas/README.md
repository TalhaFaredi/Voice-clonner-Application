# Sonora · Voice Clone SaaS

A standalone voice cloning and speech generation platform. Everything needed by the application lives in this directory. It does not import from or call the YouTube application.

**Stack:** dependency-free ES module frontend; Flask/Waitress API; SQLite with versioned SQL migrations; independent persistent GPU worker; Qwen3-TTS; Stripe Checkout + Customer Portal; SMTP password resets.

## Start locally (Windows / PowerShell)

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Chrome or Edge for optional browser tests, and a CUDA GPU for practical generation speed. Model weights download into the standard Hugging Face cache; allow approximately 10 GB for models and several GB for PyTorch. CPU is supported with `TTS_DEVICE=cpu` but significantly slower.

From **this folder**:

```powershell
uv sync --extra worker --extra dev
Copy-Item backend/.env.example backend/.env
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

The API initializes SQLite and applies migrations automatically. No seed account, default password, API secret, or simulated paid subscription is supplied. Register your own account. Free accounts receive 5,000 one-time credits. The worker must be running to process audio; the API remains responsive while models load.

For API-only development use `uv sync --extra dev` and test with the test engine. For pip users, create a Python 3.12 virtual environment and install `backend/requirements-web.txt`; install `backend/requirements.txt` for the worker, selecting the correct PyTorch wheel for your hardware. `uv.lock` provides the reproducible recommended environment; the CUDA 12.8 index is explicitly configured for Torch/Torchaudio.

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

## Design and implementation choices

The Sites skill's local workflow informed the frontend structure and responsive checks. Hosting remains local as required by the specification: a Python/GPU worker and SQLite are not deployed into a static site or a Cloudflare Worker.

Qwen3-TTS is the single integrated speech technology. It was chosen because the existing implementation already uses its multilingual cloning and saved prompts, it avoids a third-party per-request voice API dependency, and its Apache-2.0 release supports this self-hosted architecture. This is an engineering choice, not a claim that it wins every quality/speed benchmark. GPU capacity, voice similarity and consent must be evaluated for your audience. [Official Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS).

This is a production-oriented implementation, not a certification that any installation is production-ready. Public launch requires configured billing/email, HTTPS, backups, monitoring, legal/retention policies, and the deployment checks in the setup guide.
