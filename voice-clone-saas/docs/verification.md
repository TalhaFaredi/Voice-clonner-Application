# Verification

## Business logic

From `backend/`: `../.venv/Scripts/python.exe -m unittest discover -s tests -v`.

The suite covers registration/login/logout, password hashing/sessions, CSRF, profile updates, reset expiry/single use and session revocation, decoded audio validation, consent, cloning/generation lifecycle, private playback/downloads, cross-user access rejection, idempotent reservations, concurrent insufficient credit handling, failure refunds, stale-worker recovery, Stripe checkout/portal calls and deduplicated invoice allocations. Inference, SMTP and remote Stripe calls are mocked; local FFmpeg decoding is real.

## Browser

Install the dev extra and have Chrome/Edge installed. Run `python scripts/browser_check.py` with the frontend and API running. The script creates its own test account using the actual API, navigates the actual frontend, validates desktop and mobile layouts, and saves screenshots under ignored `backend/storage/qa/`. It does not pay for subscriptions or claim a simulated waveform is generated speech.

## Real inference

Install the worker extra and run `python -m app.worker` from `backend/`. Check `/api/studio/options` for a fresh ready heartbeat. Register your own account, generate a short preset sample, play/download it, then upload a 3–120 second consenting reference sample and generate a short script using the saved clone. This verifies model loading, CUDA compatibility and actual audio; automated mocked tests do not establish voice similarity.

An opt-in local integration script `scripts/inference_check.py` performs a real preset → clone → speech roundtrip using a synthetic preset reference. Its reference is explicitly synthetic, not a claim of human speaker similarity. Run with the worker and API ready. Expect GPU work and model downloads, but no paid voice API calls. Check downloaded WAV files and inspect voice quality manually.

## External services and public launch

Stripe test-mode events and real SMTP delivery require separately configured credentials. Verify their full lifecycle using the setup guide. Do not describe mocked API tests as successful real payments or delivered emails. Before public launch complete HTTPS, production cookies, trusted-proxy rate limiting, process supervision, backup/restore, load testing, retention/privacy/consent requirements and error monitoring.

## Results from this implementation session

- 13 backend tests passed, including real Stripe SDK signature verification, annual invoice grants, concurrency, ownership, refunds, reset security and decoded upload validation.
- Actual Chrome checks passed against the running API: registration/session, all dashboard pages, logout/access gate, mobile layout and private generated-audio metadata loading.
- Two real GPU roundtrips completed: Qwen preset speech, a reusable clone built from that explicitly synthetic reference, and speech generated from the saved clone. The final run also exercised chunked synthesis. Credit balances matched their exact reservations.
- Example WAVs live in ignored `backend/storage/qa/`; the two intentionally public synthetic demonstrations are copied to `frontend/public/audio/`. No human reference sample is published by these tests.
- Backend/frontend are independent processes on ports 8010/5173. Port 8000 was already occupied and was left untouched. The original YouTube app was also left untouched.
- Real card checkout, live Stripe renewals, actual SMTP delivery, multi-host deployment and production load have not been verified. No live payment keys or SMTP credentials were supplied to this new project.

`scripts/inference_check.py --browser-only` can re-check already generated QA audio. This local administrative test creates a temporary session for the latest synthetic Inference QA account through backend helpers; it is not an HTTP endpoint and is not available to site visitors. It persists no password or session token file.
