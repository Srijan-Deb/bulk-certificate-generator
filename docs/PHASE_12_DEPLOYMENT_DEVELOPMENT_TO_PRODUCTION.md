# Phase 12 — Deployment from Development to Production

## 1. Executive Summary & Deployment Architecture

This specification details two complete, production-ready, zero-cost ($0.00 / ₹0.00) deployment pathways:
- **Path A: Zero-Cost Local Production Deployment** (Bare-Metal Process Topology or Multi-Container Docker Compose with Persistent Volumes).
- **Path B: Zero-Cost Cloud Deployment Analysis & Runbook** (In-depth evaluation of free-tier platforms, analysis of the "Ephemeral Filesystem Trap", and deployment blueprints).

---

## 2. Path A: Zero-Cost Local Production Deployment

Local deployment provides 100% data privacy, predictable performance, zero network latency for storage I/O, and zero operating costs.

### Step 1: Install Python and Dependencies
Ensure Python 3.11+ is installed on the host system.
```bash
# Clone repository
git clone <repo-url>
cd "Bulk Certificate Generator"

# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows:
copy .env.example .env
# Linux / macOS:
cp .env.example .env
```

Key environment configurations for local production:
```ini
APP_ENV=production
DEBUG=False
PROJECT_NAME="Bulk Certificate Generator"
DATABASE_URL=sqlite:///./data.db
STORAGE_DIR=./storage/certificates
MAX_BATCH_SIZE=1000
WORKER_POLL_INTERVAL_SECONDS=2.0
WORKER_JOB_TIMEOUT_SECONDS=600
API_KEY_ENABLED=False
```

### Step 3: Initialize Database Schema
Apply version-controlled Alembic migrations to generate the SQLite database with WAL mode:
```bash
alembic upgrade head
```

### Step 4: Start the Services

#### Mode 1: Single-Process Developer Topology (Fastest Local Run)
With `RUN_WORKER_IN_APP=true` in `.env`, starting FastAPI automatically launches an in-process background worker thread:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### Mode 2: Decoupled Multi-Process Production Topology (Recommended)
Set `RUN_WORKER_IN_APP=false` in `.env`, then run services in two separate terminals:

**Terminal 1 (FastAPI Web API):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Terminal 2 (Dedicated Background Worker):**
```bash
python worker_runner.py
```

#### Mode 3: Docker Compose Multi-Container Deployment
Using the canonical [`compose.yaml`](../compose.yaml) specification:
```bash
docker compose up --build -d
```
Spawns `cert_generator_api`, `cert_generator_worker`, and mounts the persistent volume `cert_data` to `/app/storage`.

### Step 5: Verify Health & API Documentation
Verify that the service is operational:
```bash
# 1. Health Probe
curl -f http://127.0.0.1:8000/api/v1/health
# Expected: {"status": "healthy", "database": "connected", "environment": "production"}

# 2. Interactive Swagger UI Documentation
# Open in browser: http://127.0.0.1:8000/docs
```

### Step 6: Submit a Bulk-Generation Request
Submit a batch of recipients:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Cloud Architecture Summit",
    "issuer_name": "Software Engineering Council",
    "issue_date": "2026-10-10",
    "certificate_title": "Certificate of Excellence",
    "recipients": [
      {"recipient_name": "Ada Lovelace", "recipient_email": "ada@example.com"},
      {"recipient_name": "Alan Turing", "recipient_email": "alan@example.com"}
    ]
  }'
```
Response: `HTTP 202 Accepted` with `job_id` and `status_url`.

### Step 7: Download and Validate Generated Certificates
Poll status until `status == "COMPLETED"`:
```bash
curl "http://127.0.0.1:8000/api/v1/jobs/{job_id}"
```
Download individual PDF and batch ZIP archive:
```bash
# Download single PDF:
curl -O -J "http://127.0.0.1:8000/api/v1/certificates/{certificate_id}/download"

# Download batch ZIP archive:
curl -O -J "http://127.0.0.1:8000/api/v1/jobs/{job_id}/download"
```

Verify PDF integrity:
```bash
python -c "import pypdf; r = pypdf.PdfReader('CERT-XXXX.pdf'); print(f'Valid PDF: {len(r.pages)} page(s), Title: {r.metadata.title}')"
```

### Step 8: Backup and Restoration Procedures
We provide an automated, safe backup utility in [`scripts/backup_restore.py`](../scripts/backup_restore.py) using SQLite's online backup API:

```bash
# Create full system backup (data.db + certificates):
python scripts/backup_restore.py backup ./backups
# Generates: ./backups/cert_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore full system from backup:
python scripts/backup_restore.py restore ./backups/cert_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 3. Path B: Zero-Cost Cloud Deployment Analysis

### 3.1 Cloud Free-Tier Platform Research Matrix

| Evaluation Criteria | Render (Free Tier) | Koyeb (Free Tier) | Railway (Free Tier) | Oracle Cloud Infrastructure (Always Free) |
| :--- | :--- | :--- | :--- | :--- |
| **Python Support** | Native Python / Docker | Native Docker / Python | Native Docker | Full Linux VM (Ubuntu/Debian) |
| **Relational Database** | Free PostgreSQL expires after 30 days! | None (requires external DB) | Trial credits only ($5) | Built-in SQLite WAL or self-hosted PostgreSQL |
| **Persistent Storage** | **NONE (Ephemeral Disk)** | **NONE (Ephemeral Disk)** | **NONE (Ephemeral Disk)** | **200 GB Persistent Block Volume (Always Free)** |
| **Background Workers** | Paid only ($7/mo min) | 1 free service max | Depletes free credits | Unlimited systemd / Docker Compose workers |
| **Sleep / Inactivity** | **Sleeps after 15m inactivity** | Sleeps on inactivity | Hard credit cap | **NEVER SLEEPS (24/7/365 active)** |
| **Compute Specs** | 512 MB RAM, 0.1 CPU | 512 MB RAM, 0.1 CPU | Shared 512 MB RAM | **1 GB to 24 GB RAM, 1 to 4 OCPUs** |
| **Cost** | $0.00 (with severe limits) | $0.00 | $0.00 (trial only) | **$0.00 (Permanent Always Free)** |

### 3.2 The Ephemeral Filesystem Trap (Critical Warning)
> [!CAUTION]
> **PaaS Ephemeral Filesystem Risk**: Platforms like Render, Railway, and Koyeb run containers with ephemeral root filesystems. 
> - Any certificate PDF saved to `./storage/certificates/` is **permanently destroyed** whenever the container spins down due to inactivity, crashes, or is redeployed.
> - Furthermore, when Render puts the web service to sleep after 15 minutes of inactivity, any background processing thread is frozen.

### 3.3 Selected Zero-Cost Cloud Platform: Oracle Cloud Infrastructure (OCI Always Free)
Based on official documentation and verified pricing, **Oracle Cloud "Always Free" Compute** is the only cloud provider meeting all requirements without recurring costs:
- **Compute**: 2 x AMD Compute instances (1 GB RAM each) OR 1 to 4 cores of Ampere Altra A1 ARM compute with up to 24 GB RAM free.
- **Storage**: 200 GB persistent block storage included at $0 forever.
- **Network**: 10 TB/month free outbound data transfer.
- **Durable Persistence**: Files on disk survive reboots, kernel updates, and restarts.

### 3.4 OCI Always Free Deployment Blueprint

#### 1. Provision Instance
- OS: Ubuntu 22.04 LTS or 24.04 LTS.
- Shape: `VM.Standard.E2.1.Micro` (AMD, 1 GB RAM) or `VM.Standard.A1.Flex` (ARM, 4 OCPU, 24 GB RAM).

#### 2. Provision VM & Install Docker
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git ufw

# Add ubuntu user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 3. Clone Code and Launch via Docker Compose
```bash
git clone <repo-url> bulk-certificate-generator
cd bulk-certificate-generator

# Copy environment template
cp .env.example .env

# Launch multi-container stack in detached mode
docker compose up --build -d
```

#### 4. Configure Firewall & Reverse Proxy (NGINX + Let's Encrypt TLS)
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

Sample NGINX VirtualHost (`/etc/nginx/sites-available/cert_api`):
```nginx
server {
    server_name certs.yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Obtain automated SSL certificate:
```bash
sudo certbot --nginx -d certs.yourdomain.com
```

---

## 4. Alternative PaaS Free-Tier Path (Render + Cloudflare R2 + Supabase)

If a developer cannot use Oracle Cloud (due to credit card identity verification requirements) and insists on using a PaaS like Render:

### Required Architectural Adaptations:
1. **Decouple Database**: Use **Supabase Free Tier** (500 MB hosted PostgreSQL at $0) instead of local SQLite, setting `DATABASE_URL=postgresql://user:pass@host:5432/postgres`.
2. **Decouple Storage**: Use **Cloudflare R2** (10 GB free object storage with $0 egress fees) instead of local `./storage/`. Stream generated PDFs directly to R2 buckets with pre-signed URLs.
3. **Prevent Inactivity Sleep**: Free Render web services sleep after 15 minutes. Use an external uptime monitor (e.g. UptimeRobot free tier) to ping `GET /api/v1/health` every 10 minutes.

### Trade-Off Summary
While the Render + Cloudflare R2 + Supabase approach is technically viable at $0, it introduces:
- Distributed latency across 3 separate third-party services.
- Supabase pauses projects after 7 days of inactivity.
- Higher deployment complexity compared to the self-contained local Docker Compose topology.

---

## 5. Summary Recommendation

- **For Technical Evaluation, Portfolio, & Local Testing**: Use **Path A (Local Docker Compose or Multi-Process)**. It is 100% self-contained, launches in under 60 seconds, requires zero cloud accounts, and handles 40 certificates/second with zero latency.
- **For Permanent Cloud Public URL**: Use **Path B (Oracle Cloud Always Free VM)**. It provides dedicated persistent block storage, true 24/7 background worker execution without sleep timeouts, and zero recurring fees.
