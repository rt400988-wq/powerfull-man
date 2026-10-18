"""Safe-by-default agency lead pipeline.

All outreach and calls are disabled unless explicitly configured and consent is recorded.
"""
from __future__ import annotations

import csv
import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import phonenumbers
import psycopg
from psycopg.types.json import Json
from dns.resolver import resolve
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Agency Orchestrator", version="0.1.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agency:agency@localhost:5432/agency")
OPERATING_REGION = os.getenv("OPERATING_REGION", "UNSET")
OUTREACH_MODE = os.getenv("OUTREACH_MODE", "inbox_only")
COOLDOWN_HOURS = int(os.getenv("OUTREACH_COOLDOWN_HOURS", "168"))
MAX_RETRIES = int(os.getenv("MAX_OUTREACH_RETRIES", "3"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads_raw (
  id UUID PRIMARY KEY, first_name TEXT, last_name TEXT, company TEXT, role TEXT,
  email TEXT, phone TEXT, source TEXT NOT NULL, raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS leads_enriched (
  lead_id UUID PRIMARY KEY REFERENCES leads_raw(id) ON DELETE CASCADE,
  email_valid BOOLEAN, email_mx_valid BOOLEAN, phone_e164 TEXT,
  consent_status TEXT NOT NULL DEFAULT 'unknown', do_not_contact BOOLEAN NOT NULL DEFAULT false,
  last_contacted_at TIMESTAMPTZ, outreach_retries INTEGER NOT NULL DEFAULT 0,
  enrichment_json JSONB NOT NULL DEFAULT '{}'::jsonb, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS outreach_events (
  id UUID PRIMARY KEY, lead_id UUID NOT NULL REFERENCES leads_raw(id), channel TEXT NOT NULL,
  status TEXT NOT NULL, detail TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS leads_enriched_contact_idx ON leads_enriched(do_not_contact, consent_status);
"""

class Lead(BaseModel):
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    role: str = ""
    email: str = ""
    phone: str = ""
    source: str = Field(min_length=1)
    consent_status: str = "unknown"
    do_not_contact: bool = False

class CycleResult(BaseModel):
    ingested: int
    enriched: int
    outreach_eligible: int
    outreach_queued: int
    blocked: int
    mode: str


def db():
    return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row)


def init_db() -> None:
    with db() as conn:
        conn.execute(SCHEMA)


def normalize_phone(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = phonenumbers.parse(value, None if value.startswith("+") else os.getenv("DEFAULT_PHONE_REGION", "US"))
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None


def email_mx(email: str) -> tuple[bool, bool]:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""):
        return False, False
    domain = email.rsplit("@", 1)[1]
    try:
        resolve(domain, "MX", lifetime=3)
        return True, True
    except Exception:
        return True, False


def enrich(lead_id: str, email: str, phone: str, consent: str, dnc: bool) -> None:
    email_valid, mx_valid = email_mx(email)
    phone_e164 = normalize_phone(phone)
    with db() as conn:
        conn.execute("""INSERT INTO leads_enriched
          (lead_id,email_valid,email_mx_valid,phone_e164,consent_status,do_not_contact,enrichment_json)
          VALUES (%s,%s,%s,%s,%s,%s,%s)
          ON CONFLICT (lead_id) DO UPDATE SET email_valid=EXCLUDED.email_valid,
          email_mx_valid=EXCLUDED.email_mx_valid,phone_e164=EXCLUDED.phone_e164,
          consent_status=EXCLUDED.consent_status,do_not_contact=EXCLUDED.do_not_contact,
          updated_at=now()""", (lead_id,email_valid,mx_valid,phone_e164,consent,dnc,Json({})))


def ingest_lead(lead: Lead) -> str:
    lead_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute("""INSERT INTO leads_raw
          (id,first_name,last_name,company,role,email,phone,source,raw_json)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (lead_id,lead.first_name,lead.last_name,lead.company,lead.role,lead.email,lead.phone,lead.source,Json(lead.model_dump())))
    enrich(lead_id, lead.email, lead.phone, lead.consent_status, lead.do_not_contact)
    return lead_id


def run_cycle() -> CycleResult:
    init_db()
    with db() as conn:
        rows = conn.execute("""SELECT r.id,r.email,e.consent_status,e.do_not_contact,e.last_contacted_at,e.outreach_retries
          FROM leads_raw r JOIN leads_enriched e ON e.lead_id=r.id""").fetchall()
    eligible, blocked = [], 0
    now = datetime.now(timezone.utc)
    for row in rows:
        if row["do_not_contact"] or row["consent_status"].lower() not in {"opted_in", "consented", "test_consent"}:
            blocked += 1; continue
        if row["outreach_retries"] >= MAX_RETRIES:
            blocked += 1; continue
        if row["last_contacted_at"] and (now - row["last_contacted_at"]).total_seconds() < COOLDOWN_HOURS * 3600:
            blocked += 1; continue
        eligible.append(row)
    queued = 0
    with db() as conn:
        for row in eligible:
            # Inbox-only is the default. Real channels require explicit production configuration.
            status = "queued_inbox_only" if OUTREACH_MODE == "inbox_only" else "queued_for_human_review"
            conn.execute("INSERT INTO outreach_events (id,lead_id,channel,status,detail) VALUES (%s,%s,%s,%s,%s)",
                         (str(uuid.uuid4()), row["id"], "email", status, "Consent and cooldown checks passed"))
            queued += 1
    return CycleResult(ingested=0, enriched=len(rows), outreach_eligible=len(eligible), outreach_queued=queued, blocked=blocked, mode=OUTREACH_MODE)


@app.on_event("startup")
def startup() -> None:
    try:
        init_db()
    except Exception:
        # Health endpoint reports dependency state; container can start while DB is booting.
        pass

@app.get("/health")
def health() -> dict[str, Any]:
    try:
        with db() as conn: conn.execute("SELECT 1")
        db_status = "ok"
    except Exception as exc:
        db_status = f"unavailable: {type(exc).__name__}"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status, "region": OPERATING_REGION, "outreach_mode": OUTREACH_MODE}

@app.post("/leads")
def create_lead(lead: Lead) -> dict[str, str]:
    return {"id": ingest_lead(lead)}

@app.post("/leads/csv")
async def upload_csv(file: UploadFile = File(...)) -> dict[str, int]:
    content = (await file.read()).decode("utf-8-sig")
    count = 0
    for row in csv.DictReader(io.StringIO(content)):
        ingest_lead(Lead(**row))
        count += 1
    return {"ingested": count}

@app.post("/cycle", response_model=CycleResult)
def cycle() -> CycleResult:
    return run_cycle()

@app.post("/rasa/webhook")
def rasa_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept a Rasa event without sending outreach automatically."""
    intent = payload.get("intent", {}).get("name") or payload.get("event")
    if intent == "opt_out":
        return {"status": "opted_out", "action": "mark_do_not_contact_and_route_to_human"}
    if intent == "human":
        return {"status": "human_requested", "action": "create_crm_task"}
    return {"status": "accepted", "action": "continue_qualification"}

@app.get("/metrics")
def metrics() -> str:
    try:
        with db() as conn:
            total = conn.execute("SELECT count(*) AS n FROM leads_raw").fetchone()["n"]
            blocked = conn.execute("SELECT count(*) AS n FROM leads_enriched WHERE do_not_contact OR consent_status NOT IN ('opted_in','consented','test_consent')").fetchone()["n"]
    except Exception:
        total, blocked = 0, 0
    return f"agency_leads_total {total}\nagency_leads_blocked {blocked}\n"

@app.get("/leads")
def list_leads() -> list[dict[str, Any]]:
    with db() as conn:
        return conn.execute("""SELECT r.id,r.first_name,r.last_name,r.company,r.role,r.email,r.phone,r.source,
          e.consent_status,e.do_not_contact,e.phone_e164,e.email_mx_valid,e.outreach_retries
          FROM leads_raw r JOIN leads_enriched e ON e.lead_id=r.id ORDER BY r.created_at DESC LIMIT 500""").fetchall()

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><title>Agency Dashboard</title>
    <style>body{font-family:system-ui;margin:2rem;color:#202124}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:.5rem;text-align:left}th{background:#f4f6f8}</style></head>
    <body><h1>Agency lead dashboard</h1><p>Consent-gated operations. Outreach mode: <b>""" + OUTREACH_MODE + """</b></p>
    <div id='app'>Loading leads…</div><script>fetch('/leads').then(r=>r.json()).then(rows=>{let h='<table><tr><th>Company</th><th>Contact</th><th>Email</th><th>Consent</th><th>Source</th><th>Call</th></tr>';for(const x of rows){h+=`<tr><td>${x.company||''}</td><td>${x.first_name||''} ${x.last_name||''}</td><td>${x.email||''}</td><td>${x.consent_status}</td><td>${x.source}</td><td><button disabled title='Connect SIP.js softphone after SIP configuration'>Call</button></td></tr>`}document.querySelector('#app').innerHTML=h+'</table>'})</script></body></html>"""
