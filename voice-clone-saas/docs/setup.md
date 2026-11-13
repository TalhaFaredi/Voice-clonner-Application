# Setup and deployment

## Processes and directories

- `frontend/`: static HTML, CSS, native JavaScript modules. Run independently with `python serve.py`; no Node build step or external CDN is required.
- `backend/`: API under `app/routes`, configuration, middleware, database helpers and inference services. `run.py` uses Waitress bound to loopback port 8010. The worker runs separately as `python -m app.worker`.
- `database/migrations/`: numbered SQL migration scripts. Each migration is recorded in SQLite's `migrations` table. Create a new script for schema changes; never edit an already-applied migration.
- `backend/storage/users/{user_id}/voices/{voice_id}/`: normalized reference WAV and trusted saved voice prompt.
- `backend/storage/users/{user_id}/generated/{job_id}.wav`: generated audio. No path outside this project's storage tree is used for user files.

## Billing

1. Create a Stripe account and enable test mode first. Create Starter ($12/month, $120/year) and Creator ($29/month, $290/year) recurring USD prices matching the advertised values. Configure all four `STRIPE_*_PRICE` IDs and `STRIPE_SECRET_KEY`.
2. Enable the Stripe Customer Portal with subscription switching and cancellation. Configure allowed prices and proration behavior. Upgrades are managed there; prorations don't receive another full credit grant.
3. Forward Stripe events to `/api/billing/webhook`; configure the signing secret. Subscribe to `invoice.paid`, `invoice.payment_failed`, `customer.subscription.created`, `customer.subscription.updated`, and `customer.subscription.deleted`. The implementation supports legacy invoice `subscription` and modern `parent.subscription_details.subscription` structures; invoice price data is read from legacy `price` or `pricing.price_details.price`.
4. Exercise test Checkout, initial payment, renewal, annual allocation, failed payment, upgrade, cancellation, duplicate webhook and out-of-order delivery before live mode. The service reconciles subscription state from Stripe when processing events. Invoice credits are based on the actual paid invoice's configured price, even after a later plan change.
5. Free: 5,000 one-time credits. Starter: 50,000/month or 600,000/year upfront. Creator: 200,000/month or 2,400,000/year upfront. Unused credits carry forward, including after cancellation. Model failures refund the original reservation once. These business rules are intentional and should match your terms.

Never send browser-supplied amounts to Stripe. Never grant credits based on return-page parameters. Keep API keys and signing secrets on the backend only. [Stripe subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks).

## Email

Set SMTP host, port (STARTTLS), user/password, and a verified `SMTP_FROM`. Password reset tokens are hashed in SQLite, expire after 30 minutes, are single-use and revoke existing sessions. Missing SMTP returns a clear service-unavailable message. The API never returns a password-reset token to the browser. Configure SPF, DKIM and DMARC for the sending domain. Test delivery before launch.

## Production

Use a Linux host with a suitable GPU, persistent local disk and one Qwen worker per GPU. Run the API and worker as dedicated unprivileged services supervised by systemd or your container orchestrator. Install the worker's Torch build for your CUDA stack. SQLite/WAL is appropriate for an initial single-host deployment; use a server database/object storage before horizontal scaling.

Set `APP_ENV=production`, `PUBLIC_URL=https://your-domain.example`, and `ALLOWED_ORIGINS=https://your-domain.example`. Change `frontend/public/config.js` to `window.SONORA_API = '/api';`. Serve frontend static files with Nginx; proxy `/api/` to loopback port 8010. Forward neither arbitrary client IP headers nor cookies to third parties. Rate limiting currently uses the direct peer address: configure trusted proxy handling with exact proxy counts before per-client limiting behind a proxy. Configure TLS and matching security headers/CSP. The development frontend server is not the production web server.

Do not expose `backend/storage`, the database, `.env`, model prompts or Python source through the web server. Private downloads must pass through the authenticated API. Keep cookie traffic on HTTPS; production cookies are Secure, HttpOnly and SameSite=Lax. Use same-origin frontend/API hosting in production.

Suggested Nginx locations:

```nginx
root /srv/voice-clone-saas/frontend;
index index.html;
client_max_body_size 21m;
location /api/ { proxy_pass http://127.0.0.1:8010; }
location /src/ { try_files $uri =404; }
location /public/ { try_files $uri =404; }
location = / { try_files /index.html =404; }
location / { return 404; }
```

Add HTTPS, headers and timeouts appropriate to your host. Do not enable a broad static directory listing. Use OS permissions to restrict storage to the application service user. Maintain encrypted backups of the SQLite database and private audio together; test restoration. Use SQLite's backup API or stop writes during backups, rather than copying only the main database while WAL writes are active. Monitor disk space, worker heartbeats, queue depth, webhook failures and error logs. Do not log scripts, passwords, tokens or audio uploads. Log retention and access should be restricted.

Deleting a voice removes its reference and prompt while preserving separately generated history. Deleting a completed history item removes its audio. Billing/usage records remain for accounting. Define and implement your business's account-erasure, retention, consent, privacy and refund policies before public launch. No automated hard account erasure is exposed while subscriptions/accounting may remain active.

## Independence check

Copy this entire directory to another location, run `uv sync --extra worker`, and start the three processes from that copy. All application imports are relative to `backend/app`. There are no symlinks, parent-project imports, reused parent `.env` files or hardcoded parent workspace paths. The standard Python environment, dependency cache and Hugging Face model cache are external infrastructure, not dependencies on the YouTube app.
