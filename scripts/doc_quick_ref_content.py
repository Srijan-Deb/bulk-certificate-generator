"""
Quick Reference Runbook Content Module for Project_Operations_Quick_Reference.pdf.
A concise, structured operational runbook for developers, operators, and on-call engineers.
"""

from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, HRFlowable, PageBreak, KeepTogether, Table, TableStyle

from scripts.build_complete_documentation_suite import DocStyles, make_table


def build_quick_reference_story(styles: DocStyles):
    story = []

    # =========================================================================
    # PAGE 1: TITLE, PORTS & SERVICE TOPOLOGY, STARTUP & SHUTDOWN
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("BULK CERTIFICATE GENERATOR — OPERATIONS RUNBOOK", styles.title))
    story.append(Paragraph("Rapid Operational Reference: Service Directory, Startup, Shutdown, APIs & 60-Second Fixes", styles.subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=styles.ACCENT, spaceBefore=4, spaceAfter=10))

    meta = [
        [Paragraph("<b>Document Reference:</b> Operations Quick Reference", styles.td),
         Paragraph("<b>System Version:</b> 1.0.0 (Production Ready)", styles.td)],
        [Paragraph("<b>Target Audience:</b> DevOps, SysAdmins, On-Call Engineers", styles.td),
         Paragraph("<b>Verification:</b> 50/50 Tests Passing | WAL Concurrency", styles.td)],
    ]
    t_meta = Table(meta, colWidths=[265, 255])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), styles.BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, styles.BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, styles.BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Service Port Mapping & Web Portals Directory", styles.h1))
    port_header = ["Service Name", "Host Port", "Container Port", "Access URL / Portal", "Health Probe"]
    port_rows = [
        ["API Gateway", "8000", "8000", "http://localhost:8000/docs (Swagger UI)", "GET /api/v1/health"],
        ["Background Worker", "N/A", "N/A", "Decoupled process running worker_runner.py", "Heartbeat in DB"],
        ["Prometheus", "9090", "9090", "http://localhost:9090 (Targets & PromQL)", "GET /-/healthy"],
        ["Grafana Portal", "3000", "3000", "http://localhost:3000 (Admin / Admin)", "GET /api/health"],
    ]
    story.append(make_table(port_header, port_rows, [95, 55, 75, 195, 100], styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Rapid Startup & Shutdown Commands", styles.h1))
    cmd_text = (
        "<b>A. Full Multi-Service Stack via Docker Compose (Production):</b>\n"
        "docker compose up -d          # Starts API, Worker, Prometheus, and Grafana\n"
        "docker compose ps             # Inspect health status of all 4 containers\n"
        "docker compose logs -f api    # Stream live API access & structured log events\n"
        "docker compose stop           # Graceful freeze (preserves containers & storage)\n"
        "docker compose down           # Stop & remove containers (NEVER pass -v in prod!)\n\n"
        "<b>B. Native Python Local Execution (Development):</b>\n"
        ".\\.venv\\Scripts\\Activate.ps1                                          # Activate virtualenv\n"
        "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000             # Start FastAPI + In-App Worker\n"
        "python worker_runner.py                                               # Start standalone worker\n"
    )
    story.append(Paragraph(f"<pre>{cmd_text}</pre>", styles.code))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: ESSENTIAL API CALLS & WORKFLOWS
    # =========================================================================
    story.append(Paragraph("3. Core API Operations via cURL & HTTP", styles.h1))
    story.append(HRFlowable(width="100%", thickness=1, color=styles.ACCENT, spaceBefore=2, spaceAfter=8))

    curl_text = (
        "# 1. Download Standard Recipient Spreadsheet Template (.xlsx)\n"
        "curl -O http://localhost:8000/api/v1/jobs/upload/template\n\n"
        "# 2. Enqueue Bulk Generation via Spreadsheet Upload (Multipart)\n"
        "curl -X POST http://localhost:8000/api/v1/jobs/upload \\\n"
        "  -F \"file=@recipients.xlsx\" \\\n"
        "  -F \"event_name=Cloud Engineering Summit 2026\" \\\n"
        "  -F \"issuer_name=NIT Rourkela\" \\\n"
        "  -F \"issue_date=October 12, 2026\" \\\n"
        "  -F \"certificate_title=Certificate of Excellence\"\n\n"
        "# 3. Enqueue Bulk Generation via Direct JSON Payload\n"
        "curl -X POST http://localhost:8000/api/v1/jobs \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\"event_name\":\"Hackathon\",\"issuer_name\":\"TechCorp\",\"issue_date\":\"2026-10-12\",\"certificate_title\":\"Winner\",\"recipients\":[{\"name\":\"Ada Lovelace\",\"email\":\"ada@example.com\"}]}'\n\n"
        "# 4. Poll Batch Progress & Completion Status\n"
        "curl http://localhost:8000/api/v1/jobs/<JOB_ID>\n\n"
        "# 5. Download Complete ZIP Archive of Generated Certificates\n"
        "curl -O -J http://localhost:8000/api/v1/jobs/<JOB_ID>/download\n\n"
        "# 6. Stream Single PDF Certificate Directly\n"
        "curl -O http://localhost:8000/api/v1/certificates/<CERTIFICATE_ID>/download\n\n"
        "# 7. Query Real-Time Telemetry Stats (JSON)\n"
        "curl http://localhost:8000/api/v1/observability/stats\n"
    )
    story.append(Paragraph(f"<pre>{curl_text}</pre>", styles.code))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Observability Endpoints Reference", styles.h1))
    obs_header = ["Endpoint URL", "Format", "Telemetry Function"]
    obs_rows = [
        ["http://localhost:8000/metrics", "Text (0.0.4)", "Prometheus scrape endpoint: HTTP latencies, CPU/RAM, cert counts"],
        ["http://localhost:8000/api/v1/observability/stats", "JSON", "Real-time summary: process CPU %, RSS RAM, storage bytes, throughput"],
        ["http://localhost:8000/api/v1/observability/health/detailed", "JSON", "Deep active probe testing SQLite write and storage write/unlink"],
        ["http://localhost:3000/d/bulk-cert-gen-main", "Grafana Web", "Visual dashboard with 17 charts and real-time refresh"],
    ]
    story.append(make_table(obs_header, obs_rows, [160, 80, 280], styles))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: 60-SECOND DIAGNOSTICS & RECOVERY
    # =========================================================================
    story.append(Paragraph("5. 60-Second Operational Diagnostics & Troubleshooting", styles.h1))
    story.append(HRFlowable(width="100%", thickness=1, color=styles.ACCENT, spaceBefore=2, spaceAfter=8))

    tb_header = ["Symptom / Error", "Root Cause", "Immediate One-Liner Mitigation"]
    tb_rows = [
        ["Port 8000 Conflict",
         "Existing Uvicorn or container bound to 8000.",
         "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force"],
        ["Worker Idle / Pending",
         "Worker process halted or not started.",
         "docker compose restart worker  (or python worker_runner.py)"],
        ["SQLite Locked Error",
         "Concurrent process held lock > 30s.",
         "Verify WAL mode is active: PRAGMA journal_mode=WAL; in data.db"],
        ["Stale Jobs in PROCESSING",
         "Worker crashed mid-batch.",
         "Worker auto-recovers after 15m; force check: python scripts/verify_system.py"],
        ["Storage Permission Denied",
         "appuser (1001) cannot write to storage.",
         "docker compose exec api chown -R 1001:1001 /app/storage"],
        ["Missing Signature File",
         "templates/signature.png missing.",
         "System automatically falls back to vector signature line without failing."],
        ["Prometheus Target Down",
         "host.docker.internal unresolved in Docker.",
         "Add extra_hosts: host.docker.internal:host-gateway in compose.yaml"],
    ]
    story.append(make_table(tb_header, tb_rows, [110, 150, 260], styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Disaster Recovery & Emergency Backup", styles.h1))
    rec_text = (
        "# Trigger instant online WAL backup (zero downtime, transactionally consistent)\n"
        "python scripts/backup_restore.py --backup\n\n"
        "# Restore database and certificate storage from timestamped archive\n"
        "python scripts/backup_restore.py --restore --backup-file backups/backup_YYYYMMDD_HHMMSS.tar.gz\n\n"
        "# Check complete system integrity\n"
        "python scripts/verify_system.py\n"
    )
    story.append(Paragraph(f"<pre>{rec_text}</pre>", styles.code))

    return story
