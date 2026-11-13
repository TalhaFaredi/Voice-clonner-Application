# API

JSON API rooted at `/api`. Cookie `voice_session` is HttpOnly. Login/registration and `GET /auth/me` return a CSRF token; pass it as `X-CSRF-Token` on every authenticated mutation. Do not persist credentials in localStorage. All user-owned resources are scoped to the current session's owner.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | API health |
| POST | `/auth/register` | `name`, `email`, `password` (12–128 characters) |
| POST | `/auth/login` | `email`, `password` |
| GET | `/auth/me` | Current profile, balance, CSRF token |
| POST | `/auth/logout` | Revoke current session |
| POST | `/auth/forgot-password` | `email`; send reset email |
| POST | `/auth/reset-password` | `token`, `password`; revoke all sessions |
| PATCH | `/account` | Update `name` |
| POST | `/account/password` | `current_password`, `password` |
| GET | `/dashboard` | Usage counts, balance, low-credit state, recent jobs |
| GET | `/studio/options` | Preset voices, languages, worker state and credit costs |
| GET | `/voices` | Private voice library |
| POST | `/voices` | Multipart `name`, `audio`, `ref_text?`, `clone_mode?` (`text_conditioned` or `speaker_embedding`), `consent=true`; header `Idempotency-Key`. Transcript-based mode requires the exact words spoken in the recording. |
| POST | `/voices/{id}/preview` | Generate an included sample for a previously saved voice; no additional credits, at most three attempts, and active requests are deduplicated |
| POST | `/voices/{id}/rebuild` | Correct `ref_text` and `clone_mode` on a saved voice; requires `Idempotency-Key`. Up to three no-charge corrections; preserves the voice ID, recording, original transcript and previous prompt |
| PATCH | `/voices/{id}` | Rename with `name` |
| DELETE | `/voices/{id}` | Delete sample/prompt; reject while jobs are active |
| POST | `/generations` | `text` (max 5,000 chars), `voice_id` or `speaker`, `language?`, `instruct?`; `Idempotency-Key` required |
| GET | `/jobs?page=0` | Private history, pages of 30 |
| GET | `/jobs/{id}` | Status: queued, processing, completed or failed |
| DELETE | `/jobs/{id}` | Delete completed/failed history and audio |
| GET | `/audio/voice/{id}` | Private normalized voice reference |
| GET | `/audio/preview/{id}` | Private synthesized clone sample; not the uploaded reference |
| GET | `/audio/generation/{id}` | Private generated WAV; `?download=1` for attachment |
| GET | `/plans` | Public pricing/costs and configuration availability |
| GET | `/billing` | Subscription, credit ledger and paid invoices |
| POST | `/billing/checkout` | `plan` (starter/creator), `interval` (month/year) |
| POST | `/billing/portal` | Stripe portal URL for plan changes/cancellation |
| POST | `/billing/webhook` | Raw Stripe body and `Stripe-Signature`; no browser CSRF |

Errors use `{ "error": "Human-readable message" }` with HTTP 400/401/402/403/404/409/413/429/503 as appropriate. Credit reservations and queue inserts commit atomically. Retry an uncertain request with the same idempotency key and same input; a changed payload with that key returns 409. A genuinely new generation uses a new key. Keys are 16–100 characters of letters, digits, underscore or hyphen.

Clone and generation endpoints return HTTP 202 with the durable job record. Poll the job to completion; no inference runs in the request thread. Work survives API restarts. A worker that dies after claiming a job is detected after three minutes and its reservation refunded by a running/restarted worker. Heartbeats run independently during inference/model loading. Stale work fails safely rather than silently charging a duplicate retry.

Jobs also expose `phase` and `progress` milestones for the animated UI. A new clone now includes synthesis of a short private sample before completion. The 1,000-credit cloning cost is unchanged. If sample synthesis fails after a valid prompt is saved, the voice remains ready and `preview_error` explains how to try it in the studio. Voice records include `reference_duration`, `clone_mode`, `preview_url`, `preview_text`, `preview_duration` and `latest_job`; all remain owner-scoped. Original uploads and generated clone samples use separate audio routes and labels.
