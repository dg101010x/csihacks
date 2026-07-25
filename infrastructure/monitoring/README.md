# Monitoring (Section 20)

- **Liveness/readiness**: `GET /health` on apps/api — used by docker-compose's healthcheck and any orchestrator (Kubernetes, ECS, etc.) probe config.
- **Structured logs**: set `LOG_FORMAT=json` (apps/api/app/logging_config.py) for JSON-formatted log lines suitable for any aggregator (CloudWatch, Datadog, Loki, ...). Plain text by default for local dev readability.
- **Request correlation**: every response carries an `X-Request-Id` header (RequestIdMiddleware); the same id is included in error log lines via `extra={"request_id": ...}` and in every audit event's `request_id` field, so a single request can be traced end-to-end across logs and the audit trail.
- **Not yet built**: metrics export (Prometheus/OpenTelemetry), alerting rules, and dashboards. `/health` plus structured logs are the floor, not the ceiling — tracked as a real gap, not something quietly skipped.
