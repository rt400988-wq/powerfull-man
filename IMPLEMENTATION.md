# Agency Orchestrator implementation

The `agency-orchestrator/` directory now contains a consent-gated local-first lead pipeline. It stores raw and enriched leads in PostgreSQL, normalizes phones, checks email MX records, applies cooldown and retry rules, exposes a dashboard/API, and emits Prometheus-compatible metrics. Docker Compose provides PostgreSQL, Redis, MinIO, Prometheus, and Grafana.

Run `cp .env.example .env`, review all placeholders, then run `./deploy.sh`. Load the included test lead with `SEED_LEADS_CSV=agency-orchestrator/examples/seed_leads.csv ./run_cycle.sh`. Production provider activation remains intentionally disabled until jurisdiction, legal copy, credentials, test inbox, and human-call workflow are supplied.
