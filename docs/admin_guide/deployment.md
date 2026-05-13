# EIBO Deployment Guide

> Complete installation, configuration, and operations reference for system administrators.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Browser  →  Streamlit (port 8501)                  │
│               │                                      │
│           DuckDB (in-process analytics)              │
│           PostgreSQL (persistent data, audit logs)   │
│           Redis (optional session cache)             │
└─────────────────────────────────────────────────────┘
```

All components run inside Docker containers. The default single-node deployment runs everything on one host. For high-concurrency deployments (100+ concurrent users), see the [Scaling](#scaling) section.

---

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 20 GB | 50+ GB (for audit logs + data) |
| Docker | 24.0+ | latest stable |
| Docker Compose | 2.20+ | latest stable |
| OS | Linux/macOS/Windows (WSL2) | Ubuntu 22.04 LTS |

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/eibo.git
cd eibo
```

### 2. Configure Environment Variables

Copy the example environment file and fill in required values:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```bash
# Required — database
POSTGRES_USER=eibo_user
POSTGRES_PASSWORD=<generate a strong password>
POSTGRES_DB=eibo_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Required — application security
SECRET_KEY=<generate a random 64-character string>

# Application mode
DEMO_MODE_ENABLED=true         # set false for production with real data
LOG_LEVEL=INFO                 # DEBUG for troubleshooting
```

Generate a strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the Stack

```bash
docker-compose up -d
```

First startup downloads images and runs database migrations (~2–3 minutes). Check progress:

```bash
docker-compose logs -f
```

### 4. Verify the Deployment

```bash
# Check all containers are healthy
docker-compose ps

# Run the health check
docker-compose exec streamlit python -c "
from health.checker import get_health_summary
import json
print(json.dumps(get_health_summary(), indent=2))
"
```

All components should report `healthy`. Open `http://localhost:8501` in a browser.

### 5. Seed Demo Data (Optional)

```bash
docker-compose exec streamlit python demo_data/seed_demo.py --scenario all --size medium
```

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | Database username | `eibo_user` |
| `POSTGRES_PASSWORD` | Database password (min 8 chars) | `<strong password>` |
| `POSTGRES_DB` | Database name | `eibo_db` |
| `POSTGRES_HOST` | Database host | `postgres` (Docker service name) |
| `SECRET_KEY` | Application secret key (min 16 chars) | `<64-char hex string>` |

### Optional

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_PORT` | Database port | `5432` |
| `DUCKDB_PATH` | Path for DuckDB analytics file | `/data/eibo_analytics.db` |
| `REDIS_HOST` | Redis host (for caching) | *(disabled if unset)* |
| `REDIS_PORT` | Redis port | `6379` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_MODE` | Formatter mode (`production`/`development`) | `production` |
| `DEMO_MODE_ENABLED` | Enable demo data mode | `true` |
| `MAX_EMPLOYEES_SIMULATION` | Max employees for ILP solver | `5000` |
| `SIMULATION_TIMEOUT_SECONDS` | ILP solver timeout | `10` |
| `AUDIT_LOG_RETENTION_DAYS` | Days to keep audit logs | `365` |
| `SIMULATION_HISTORY_RETENTION_DAYS` | Days to keep simulation history | `90` |

### Email Notifications (Optional)

| Variable | Description |
|---|---|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_FROM` | From address for notifications |

### OAuth2/OIDC Authentication (Optional)

| Variable | Description |
|---|---|
| `OAUTH_PROVIDER` | Provider: `google`, `azure`, `okta`, or `local` |
| `OAUTH_CLIENT_ID` | OAuth client ID |
| `OAUTH_CLIENT_SECRET` | OAuth client secret |
| `OAUTH_DISCOVERY_URL` | Provider's OIDC discovery URL |

Set `OAUTH_PROVIDER=local` (default) to use EIBO's built-in username/password authentication.

---

## Production Deployment

For production, use the production compose override:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production override applies:
- `DEMO_MODE_ENABLED=false`
- Structured JSON logging
- Stricter resource limits
- Health check intervals
- Automatic container restart policies

### Secrets Management

**Never store secrets in the repository.** In production:

1. Use Docker Secrets or your orchestrator's secrets manager (Kubernetes Secrets, AWS Secrets Manager, etc.)
2. Mount secrets as files and reference via environment variables
3. Run the secrets validator on startup:

```bash
docker-compose exec streamlit python -c "
from utils.secrets_validator import assert_production_secrets
assert_production_secrets()
print('All secrets validated.')
"
```

### TLS / HTTPS

EIBO itself does not terminate TLS. Place a reverse proxy in front:

```nginx
# Example nginx config
server {
    listen 443 ssl;
    server_name eibo.yourcompany.com;
    ssl_certificate /etc/ssl/certs/eibo.crt;
    ssl_certificate_key /etc/ssl/private/eibo.key;
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## User Management

### Creating the First Admin

```bash
docker-compose exec streamlit python -c "
from auth.rbac import RBACManager, Role
manager = RBACManager()
manager.create_user(
    user_id='admin-001',
    email='admin@yourcompany.com',
    name='System Administrator',
    role=Role.ADMIN,
    department=None,  # Admins are org-wide
)
print('Admin user created.')
"
```

### Role Reference

| Role | Level | Capabilities |
|---|---|---|
| Viewer | 1 | Dashboards only, no simulation |
| Analyst | 2 | Run simulations, create scenarios |
| Manager | 3 | Own department, full features, can override |
| Director | 4 | Multiple departments, strategic planning |
| Executive | 5 | Org-wide, all features except admin |
| Admin | 6 | System config, user management, audit logs |

### Department Scoping

Managers and Analysts are scoped to specific departments. When creating a user, set their `department` to enforce data isolation:

```python
manager.create_user(
    user_id="mgr-001",
    email="sarah@yourcompany.com",
    name="Sarah Chen",
    role=Role.MANAGER,
    department="Engineering",
)
```

A Manager with `department="Engineering"` cannot query, simulate, or export data from other departments.

---

## Data Ingestion

### Supported Formats

- **CSV**: UTF-8, with header row. See `data_pipeline/validators.py` for required columns.
- **Excel**: `.xlsx` format, first sheet used.
- **HRIS Connectors**: Workday, SAP SuccessFactors, BambooHR (configured separately).

### Pipeline Execution

```bash
# Run data pipeline (full refresh)
python data_pipeline/bronze_ingest.py --input data/payroll.csv
python data_pipeline/silver_cleanse.py
python data_pipeline/gold_aggregate.py

# Or via the workflow engine (recommended for production)
python workflows/data_pipeline_flow.py --input data/payroll.csv
```

### Scheduled Refresh

Use Prefect or cron to schedule regular ingestion:

```bash
# Daily at 2am
0 2 * * * cd /opt/eibo && docker-compose exec -T streamlit python workflows/data_pipeline_flow.py
```

---

## Monitoring and Health

### Health Check Endpoint

```bash
# Check all components
python -c "
from health.checker import HealthChecker
report = HealthChecker().run()
print(report.overall_status)
for c in report.components:
    print(f'  {c.name}: {c.status} ({c.latency_ms:.0f}ms)')
"
```

### Logs

Production logs are written as JSON lines to stdout (captured by Docker):

```bash
# Stream all logs
docker-compose logs -f

# Stream Streamlit logs only
docker-compose logs -f streamlit

# Filter for errors
docker-compose logs streamlit | grep '"level":"ERROR"'
```

### Audit Trail

All user actions (logins, simulations, overrides, exports) are recorded:

```bash
# View recent audit entries
docker-compose exec streamlit python -c "
from audit.logger import get_audit_logger
logger = get_audit_logger()
for entry in list(logger.recent_entries())[-20:]:
    print(entry)
"

# Export audit log
docker-compose exec streamlit python audit/trail_viewer.py --export --output audit_export.csv
```

---

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U eibo_user eibo_db > backups/eibo_$(date +%Y%m%d).sql

# Backup DuckDB analytics file
docker cp eibo_streamlit_1:/data/eibo_analytics.db backups/analytics_$(date +%Y%m%d).db
```

### Database Restore

```bash
docker-compose exec -T postgres psql -U eibo_user eibo_db < backups/eibo_20260101.sql
```

### Automated Backups

Add to cron:

```bash
# Daily backup at 3am, retain 30 days
0 3 * * * cd /opt/eibo && docker-compose exec -T postgres pg_dump -U eibo_user eibo_db | gzip > backups/eibo_$(date +\%Y\%m\%d).sql.gz && find backups/ -name "*.sql.gz" -mtime +30 -delete
```

---

## Scaling

For high-concurrency deployments:

1. **Enable Redis**: Set `REDIS_HOST` and `REDIS_PORT`. Redis caches model predictions per unique input set, reducing compute on repeated queries.
2. **Increase Streamlit workers**: Adjust `server.maxUploadSize` and `server.maxMessageSize` in `.streamlit/config.toml`.
3. **Separate PostgreSQL**: Move PostgreSQL to a dedicated host or managed service (AWS RDS, Azure Database, etc.).
4. **Load balancer**: Place multiple Streamlit instances behind a load balancer with sticky sessions.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Dashboard won't load | DuckDB file not found | Check `DUCKDB_PATH` and disk space |
| Simulation times out | Large org + strict constraints | Increase `SIMULATION_TIMEOUT_SECONDS` or relax constraints |
| Login fails | OAuth misconfiguration | Check `OAUTH_*` vars; try `OAUTH_PROVIDER=local` |
| Missing salary data | Role permissions | User role < Manager; expected behavior |
| Audit log full | Low disk space | Reduce `AUDIT_LOG_RETENTION_DAYS` or expand disk |
| "Secrets validation failed" | Missing env vars | Run `assert_production_secrets()` to see which vars are missing |

---

*EIBO — Employee Impact & Budget Optimizer · OPB AI Mastery Lab*
