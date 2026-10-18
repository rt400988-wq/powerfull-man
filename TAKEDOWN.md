# Lead removal and takedown procedure

When a contact requests removal, stop all active outreach immediately, set `do_not_contact=true`, set `consent_status=opted_out`, and record the request source and timestamp. Remove the lead from provider campaign queues and delete recordings or transcripts when the applicable retention policy requires it.

For the local stack, update the record in PostgreSQL and verify `GET /leads` no longer shows it as eligible. For a legal request, preserve only the minimum audit record needed to demonstrate compliance and escalate to the owner contact in `.env`.
