# Sonora · Voice Cloning & Speech Generation

A standalone voice-cloning SaaS powered by **Qwen3-TTS and NVIDIA CUDA**, with private accounts, reusable voices, background speech jobs, audio downloads, credits and subscription billing integration.

The new application is in **[`voice-clone-saas/`](voice-clone-saas/README.md)**. Its frontend, backend, configuration, database migrations, assets and documentation are self-contained. The original local voice-cloning/YouTube app remains in the repository root; its instructions are preserved in the [legacy application guide](docs/legacy-voice-cloner.md).

## Documentation languages

[English](voice-clone-saas/README.md) · [中文](voice-clone-saas/docs/i18n/README.zh-CN.md) · [日本語](voice-clone-saas/docs/i18n/README.ja.md) · [한국어](voice-clone-saas/docs/i18n/README.ko.md) · [Deutsch](voice-clone-saas/docs/i18n/README.de.md) · [Français](voice-clone-saas/docs/i18n/README.fr.md) · [Русский](voice-clone-saas/docs/i18n/README.ru.md) · [Português](voice-clone-saas/docs/i18n/README.pt.md) · [Español](voice-clone-saas/docs/i18n/README.es.md) · [Italiano](voice-clone-saas/docs/i18n/README.it.md)

Translations are getting-started guides. Full operational details are in the [main README](voice-clone-saas/README.md), [deployment guide](voice-clone-saas/docs/setup.md), [API reference](voice-clone-saas/docs/api.md) and [verification notes](voice-clone-saas/docs/verification.md).

## What is implemented

- Registration, login/logout, password reset, profiles and private user-owned voice libraries.
- Validated voice uploads, reusable cloned voices, preset speech, ten speech languages, previews, WAV downloads and generation history.
- A responsive landing page and dashboard, with real synthetic preset/clone audio demonstrations.
- An independent Qwen background worker, persistent SQLite jobs, atomic credit reservations, idempotent requests, failure refunds and usage history.
- Stripe Checkout, subscription management through Customer Portal, signed webhooks and invoice-based credit allocations.
- Argon2 password hashing, revocable cookie sessions, CSRF/origin checks, rate limits and authenticated audio access.

**Status:** local speech synthesis and voice cloning work and have been tested with real GPU inference. Live Stripe billing and SMTP email delivery still require configuration and end-to-end verification. This repository is not a claim that the service is already deployed or production-certified.

## Quick start — Windows / PowerShell

Install Python 3.12 and [uv](https://docs.astral.sh/uv/), and provide a CUDA-capable NVIDIA GPU for practical generation speed. The dependency lock selects CUDA-enabled PyTorch; models download on first startup.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application/voice-clone-saas
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

From `voice-clone-saas/`, open three separate terminals and run one command in each:

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Open **http://localhost:5173** and register an account. The API runs on **http://localhost:8010**. Check `/api/studio/options` for a fresh `worker.status: ready` response before generating audio. Use the same hostname for frontend and API. No default login or administrator password is supplied.

## NVIDIA GPU support

The worker uses `TTS_DEVICE=cuda:0` by default, so Qwen inference runs on the first NVIDIA CUDA GPU. This installation was verified on an **NVIDIA RTX A6000 with 48 GB VRAM**. That is tested hardware, not a minimum requirement or a guarantee of performance on other GPUs. GPU utilization increases during synthesis and can be low while idle.

```powershell
nvidia-smi
./.venv/Scripts/python.exe -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU available')"
```

`TTS_DEVICE=cpu` is also supported but slower. Configure it in `backend/.env` and restart the worker. The local voice engine does not require an OpenRouter, NVIDIA API, HeyGen or ElevenLabs API key.

## Supported speech languages

Chinese · English · Japanese · Korean · German · French · Russian · Portuguese · Spanish · Italian.

Select `auto` to detect the script's language. Language selection controls speech generation; **it does not translate the script**. The current interface is English; the linked translated READMEs do not add interface translations or model-language support. See the [native names and API values](voice-clone-saas/README.md#supported-speech-languages).

## Verification

From `voice-clone-saas/backend/`:

```powershell
../.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Verified during implementation: **13 backend tests**, desktop/mobile browser flows, real preset speech → saved voice clone → generated speech, exact credit deductions, and private audio loading in Chrome. Stripe/SMTP unit tests use mocked external calls; real transactions and email delivery are separate checks. [Detailed verification](voice-clone-saas/docs/verification.md).

## Before public deployment

Configure Stripe keys, recurring price IDs, Customer Portal and webhook signing; configure and test SMTP; deploy behind HTTPS; set up backups, monitoring and supervised processes; and complete the [deployment checklist](voice-clone-saas/docs/setup.md).

Never commit `.env`, databases, private audio, user voice prompts or installed environments. Only the intentionally public synthetic audio demonstrations are included in Git.
