# Agency Orchestrator

A local-first, consent-gated lead pipeline around the collected Scrapy/Playwright, email, CRM, PBX, Rasa, SIP.js, Vosk, MinIO, and observability projects.

## Safety defaults

- `OUTREACH_MODE=inbox_only` by default.
- Only leads with `consent_status` of `opted_in`, `consented`, or `test_consent` enter outreach queues.
- `do_not_contact`, opt-out status, cooldown, and three-retry limits block outreach.
- WhatsApp automation is limited to the official Business API; otherwise use a documented human handshake.
- Automated calling is not enabled by this scaffold; calls require human review, SIP configuration, and disclosure text.

## Run locally

```bash
cp .env.example .env
# replace placeholders and keep OUTREACH_MODE=inbox_only for testing
./deploy.sh
curl http://localhost:8000/health
open http://localhost:8000/dashboard
./run_cycle.sh
```

The API accepts `POST /leads`, CSV upload at `POST /leads/csv`, `POST /cycle`, and lists leads at `GET /leads`.

## Components

The current implementation provides the consent gate, raw/enriched lead storage, email MX and phone enrichment, cooldown/retry policy, dashboard, and local infrastructure. Provider adapters for Mautic/SuiteCRM, Postal/SMTP, official WhatsApp, Asterisk/FreeSWITCH, Rasa, SIP.js, Vosk, and MinIO are represented by configuration templates and integration inventory; credentials and jurisdiction-specific legal text are intentionally required before activation.
