"""
Generate Comprehensive Project Documentation PDF for Bulk Certificate Generator.
Covers all 14 phases, architectural designs, empirical benchmarks, observations, and interview defense.
"""

import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y' on all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        # Suppress header and footer on cover page
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#6B7280"))
            self.drawString(40, letter[1] - 30, "Bulk Certificate Generator — Complete Project Engineering Documentation")
            self.drawRightString(letter[0] - 40, letter[1] - 30, "Zero-Cost Production Architecture")
            self.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.setLineWidth(0.5)
            self.line(40, letter[1] - 34, letter[0] - 40, letter[1] - 34)

            # Footer
            self.line(40, 36, letter[0] - 40, 36)
            self.setFont("Helvetica", 8)
            self.drawString(40, 24, "Confidential & Proprietary — Engineering Portfolio & Architecture Manual")
            page_text = f"Page {self._pageNumber} of {total_pages}"
            self.drawRightString(letter[0] - 40, 24, page_text)
        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=44,
        bottomMargin=44
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1E3A8A")     # Deep Blue
    SECONDARY = colors.HexColor("#0D9488")   # Teal
    DARK_TEXT = colors.HexColor("#1F2937")   # Charcoal
    MUTED_TEXT = colors.HexColor("#4B5563")  # Gray
    BG_LIGHT = colors.HexColor("#F9FAFB")    # Very light gray
    BORDER_COLOR = colors.HexColor("#E5E7EB")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        alignment=1, # Center
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=MUTED_TEXT,
        alignment=1,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=DARK_TEXT,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=DARK_TEXT,
        leftIndent=15,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
        backColor=BG_LIGHT,
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=4,
        spaceAfter=6
    )

    obs_style = ParagraphStyle(
        'Obs_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#78350F"),
        backColor=colors.HexColor("#FEF3C7"),
        borderColor=colors.HexColor("#FDE68A"),
        borderWidth=1,
        borderPadding=5,
        spaceAfter=6
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=DARK_TEXT
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # COVER / TITLE BLOCK
    # =========================================================================
    story.append(Spacer(1, 15))
    story.append(Paragraph("BULK CERTIFICATE GENERATOR", title_style))
    story.append(Paragraph("Complete Engineering Architecture, Implementation Lifecycle & Production Specification", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=4, spaceAfter=12))

    meta_data = [
        [Paragraph("<b>Document Type:</b> Full Lifecycle Engineering Specification", table_cell),
         Paragraph("<b>Project Version:</b> 1.0.0 (Production-Ready)", table_cell)],
        [Paragraph("<b>Core Stack:</b> Python 3.11+, FastAPI, SQLAlchemy 2.0, ReportLab", table_cell),
         Paragraph("<b>Database:</b> SQLite WAL Mode / PostgreSQL Ready", table_cell)],
        [Paragraph("<b>Total Cost Model:</b> $0.00 / ₹0.00 (Zero-Cost Verified)", table_cell),
         Paragraph("<b>Test Coverage:</b> 90% Statement Coverage (31 Tests Passing)", table_cell)],
        [Paragraph("<b>Author / Engineer:</b> Backend Systems Engineering", table_cell),
         Paragraph(f"<b>Generated Date:</b> {datetime.now().strftime('%B %d, %Y')}", table_cell)]
    ]
    t_meta = Table(meta_data, colWidths=[270, 260])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # =========================================================================
    # EXECUTIVE SUMMARY & CORE OBSERVATIONS
    # =========================================================================
    story.append(Paragraph("Executive Summary & Core Engineering Observations", h1_style))
    story.append(Paragraph(
        "The Bulk Certificate Generator Backend API is a high-throughput, fault-isolated asynchronous system designed "
        "to ingest bulk batches of certificate recipients, render high-resolution vector PDF certificates, track granular job "
        "progress, and serve single and batched ZIP downloads under a strict <b>$0.00 / ₹0.00 Zero-Cost Constraint</b>. "
        "Rather than relying on heavy headless browsers or expensive paid cloud APIs, the system uses a pure programmatic "
        "ReportLab vector engine and a database-backed worker architecture.",
        body_style
    ))

    story.append(Paragraph("Key Engineering Discoveries & Observations", h2_style))

    obs1 = (
        "<b>Observation 1: The Vector Engine vs. Headless Browser Paradigm</b><br/>"
        "Headless Chromium (Puppeteer/Playwright) incurs ~300 MB RAM per browser process and 1,000–2,000ms per certificate, "
        "producing rasterized bitmap PDFs of 500 KB–2 MB. In contrast, ReportLab compiles vector PostScript primitives in "
        "<b>~25 milliseconds</b> with <b>~1 MB peak RAM</b>, producing <b>~3.23 KB PDFs</b>. This represents a 60x throughput "
        "gain and 150x storage density improvement, allowing over 309,000 certificates per gigabyte."
    )
    story.append(Paragraph(obs1, obs_style))

    obs2 = (
        "<b>Observation 2: The PaaS Ephemeral Filesystem Trap</b><br/>"
        "Free cloud PaaS hosts (Render, Koyeb, Railway) execute containers on ephemeral root filesystems. Any certificate "
        "persisted to local disk is permanently destroyed upon container reboot, sleep, or redeploy. Furthermore, Render "
        "freezes free web containers after 15 minutes of inactivity, terminating background threads. True zero-cost cloud "
        "requires either <b>Oracle Cloud Infrastructure (OCI) Always Free VM</b> (200 GB permanent block storage, 0 sleep timeouts) "
        "or decoupling storage to an S3-compatible zero-egress bucket (Cloudflare R2)."
    )
    story.append(Paragraph(obs2, obs_style))

    obs3 = (
        "<b>Observation 3: SQLite WAL Concurrency Mechanics</b><br/>"
        "Default SQLite locks the entire database file during write transactions, causing 'database is locked' errors during "
        "concurrent API reads. Applying connection-level pragmas (<code>PRAGMA journal_mode = WAL;</code> and "
        "<code>PRAGMA busy_timeout = 5000;</code>) separates the write-ahead log from the database file, allowing continuous "
        "non-blocking reads while the worker writes batch updates."
    )
    story.append(Paragraph(obs3, obs_style))

    obs4 = (
        "<b>Observation 4: Eliminating the Dual-Write Hazard</b><br/>"
        "Using Celery with Redis creates a dual-write vulnerability: writing to SQL and pushing to Redis are separate "
        "operations that can desynchronize if one fails. The database-backed worker inserts parent <code>GenerationJob</code> "
        "and all child <code>CertificateRecord</code> rows in a single atomic ACID transaction, eliminating orphaned tasks."
    )
    story.append(Paragraph(obs4, obs_style))

    story.append(PageBreak())

    # =========================================================================
    # PHASE 1 & 2: REQUIREMENTS & SYSTEM ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("Phase 1 & 2: Requirement Analysis & System Architecture", h1_style))
    story.append(Paragraph(
        "<b>Functional Scope:</b> The system ingests up to 1,000 recipients per bulk request, performs Pydantic validation, "
        "enforces uniqueness within the payload, records individual recipient outcomes, dynamically scales font sizes to prevent "
        "text overflow, generates cryptographic verification codes (<code>V-XXXX-XXXX-XXXX</code>), and packages completed "
        "certificates into streaming ZIP archives.",
        body_style
    ))
    story.append(Paragraph(
        "<b>System Architecture:</b> Structured as a Layered Modular Monolith with an asynchronous database-backed background worker:",
        body_style
    ))

    arch_layers = [
        [Paragraph("<b>Layer</b>", table_header), Paragraph("<b>Component</b>", table_header), Paragraph("<b>Responsibility</b>", table_header)],
        [Paragraph("Presentation / API", table_cell), Paragraph("FastAPI (ASGI) + Uvicorn", table_cell), Paragraph("Request validation, JSON serialization, HTTP 202 Accepted, rate & payload limiting.", table_cell)],
        [Paragraph("Persistence", table_cell), Paragraph("SQLAlchemy 2.0 + SQLite WAL", table_cell), Paragraph("ACID transaction management, multi-counter state machine, job querying.", table_cell)],
        [Paragraph("Execution / Worker", table_cell), Paragraph("Database-Backed Background Worker", table_cell), Paragraph("Compare-and-Swap atomic claiming, per-recipient failure isolation, heartbeat tracking.", table_cell)],
        [Paragraph("Rendering Engine", table_cell), Paragraph("ReportLab Vector Compiler", table_cell), Paragraph("A4 landscape vector PDF generation, dynamic font auto-scaling, pypdf integrity check.", table_cell)],
        [Paragraph("Storage", table_cell), Paragraph("Local FS / Persistent Named Volume", table_cell), Paragraph("Secure storage hierarchy: <code>./storage/certificates/{job_id}/{cert_id}.pdf</code>.", table_cell)]
    ]
    t_arch = Table(arch_layers, colWidths=[95, 140, 295])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Comparison of Concurrency & Queue Strategies", h2_style))
    comp_data = [
        [Paragraph("<b>Strategy</b>", table_header), Paragraph("<b>Crash Durability</b>", table_header), Paragraph("<b>Memory (RAM)</b>", table_header), Paragraph("<b>Infra Cost</b>", table_header), Paragraph("<b>Verdict</b>", table_header)],
        [Paragraph("Synchronous HTTP", table_cell), Paragraph("None (Lost if client disconnects)", table_cell), Paragraph("Low", table_cell), Paragraph("₹0", table_cell), Paragraph("Rejected: Gateway timeouts on >50 certs", table_cell)],
        [Paragraph("FastAPI BackgroundTasks", table_cell), Paragraph("Zero (Destroyed on server restart)", table_cell), Paragraph("Low", table_cell), Paragraph("₹0", table_cell), Paragraph("Rejected: Unsafe for durable production", table_cell)],
        [Paragraph("Celery + Redis", table_cell), Paragraph("High (Persisted in Redis queue)", table_cell), Paragraph("High (>250 MB)", table_cell), Paragraph("High (Needs Redis)", table_cell), Paragraph("Rejected: OOM risk in 512MB free tiers", table_cell)],
        [Paragraph("Database Worker (Chosen)", table_cell), Paragraph("Full (Persisted in ACID SQL)", table_cell), Paragraph("Very Low (<60 MB)", table_cell), Paragraph("₹0 (Zero Cost)", table_cell), Paragraph("Optimal: Fault-tolerant, self-healing, ₹0", table_cell)]
    ]
    t_comp = Table(comp_data, colWidths=[110, 110, 85, 65, 160])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 10))

    # =========================================================================
    # PHASE 3 & 4: DATABASE & API DESIGN
    # =========================================================================
    story.append(Paragraph("Phase 3 & 4: Database Design & RESTful API Specification", h1_style))
    story.append(Paragraph(
        "The relational schema decouples parent job tracking from recipient certificate instances. "
        "Job progression is maintained via 5 synchronized counters: <code>total_recipients</code>, "
        "<code>successful_count</code>, <code>failed_count</code>, <code>pending_count</code>, and <code>processing_count</code>.",
        body_style
    ))

    schema_data = [
        [Paragraph("<b>Table</b>", table_header), Paragraph("<b>Key Columns</b>", table_header), Paragraph("<b>Types & Constraints</b>", table_header), Paragraph("<b>Purpose</b>", table_header)],
        [Paragraph("<code>generation_jobs</code>", table_cell), Paragraph("id (PK)<br/>event_name<br/>issuer_name<br/>status<br/>total_recipients<br/>successful_count<br/>failed_count", table_cell), Paragraph("VARCHAR(36)<br/>VARCHAR(255)<br/>VARCHAR(255)<br/>VARCHAR(50), Indexed<br/>INTEGER<br/>INTEGER<br/>INTEGER", table_cell), Paragraph("Tracks batch lifecycle, status transitions (PENDING -> PROCESSING -> COMPLETED / COMPLETED_WITH_ERRORS), and metrics.", table_cell)],
        [Paragraph("<code>certificate_records</code>", table_cell), Paragraph("id (PK)<br/>job_id (FK)<br/>recipient_name<br/>recipient_email<br/>certificate_code<br/>verification_code<br/>status, file_path", table_cell), Paragraph("VARCHAR(36)<br/>VARCHAR(36), Indexed<br/>VARCHAR(255)<br/>VARCHAR(255)<br/>VARCHAR(100), Unique<br/>VARCHAR(100)<br/>VARCHAR(50), VARCHAR(500)", table_cell), Paragraph("Holds per-recipient outputs. Records granular errors (INVALID_RECIPIENT_DATA, RENDER_ERROR) on individual failures.", table_cell)]
    ]
    t_schema = Table(schema_data, colWidths=[100, 110, 120, 200])
    t_schema.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_schema)
    story.append(Spacer(1, 8))

    story.append(Paragraph("RESTful Endpoint Specifications", h2_style))
    api_data = [
        [Paragraph("<b>Method</b>", table_header), Paragraph("<b>Endpoint</b>", table_header), Paragraph("<b>Status</b>", table_header), Paragraph("<b>Description</b>", table_header)],
        [Paragraph("POST", table_cell), Paragraph("<code>/api/v1/jobs</code>", table_cell), Paragraph("202 Accepted", table_cell), Paragraph("Accepts bulk recipients, validates payload, inserts records, enqueues job.", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("<code>/api/v1/jobs/{job_id}</code>", table_cell), Paragraph("200 OK", table_cell), Paragraph("Returns real-time multi-counter status, percentage, and download URL.", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("<code>/api/v1/jobs/{job_id}/certificates</code>", table_cell), Paragraph("200 OK", table_cell), Paragraph("Lists recipient certificate rows with optional <code>?status=</code> filtering.", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("<code>/api/v1/jobs/{job_id}/download</code>", table_cell), Paragraph("200 OK", table_cell), Paragraph("Streams all successful PDFs packaged into a ZIP archive.", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("<code>/api/v1/certificates/{id}/download</code>", table_cell), Paragraph("200 OK", table_cell), Paragraph("Downloads an individual certificate PDF file.", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("<code>/api/v1/health</code>", table_cell), Paragraph("200 OK", table_cell), Paragraph("Service liveness and database connectivity health probe.", table_cell)]
    ]
    t_api = Table(api_data, colWidths=[55, 160, 75, 240])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_api)

    story.append(PageBreak())

    # =========================================================================
    # PHASE 5 & 6: CERTIFICATE GENERATION & BULK PROCESSING
    # =========================================================================
    story.append(Paragraph("Phase 5 & 6: Vector Certificate Engine & Worker Processing", h1_style))
    story.append(Paragraph(
        "<b>Certificate Rendering Architecture:</b> ReportLab draws A4 landscape vector graphics (841.89 x 595.27 points). "
        "It features geometric borders, decorative corner florets, gold rosettes, dynamic text placement, and a cryptographic "
        "verification badge. To prevent long recipient names (e.g. 70 characters) from colliding with borders, the engine "
        "implements <b>Dynamic Font Auto-Scaling</b>:",
        body_style
    ))

    code_scaling = (
        "# Dynamic Font Auto-Scaling Algorithm\n"
        "max_width = page_width - 2 * (margin + 60)\n"
        "font_size = 30\n"
        "while font_size > 14:\n"
        "    if canvas.stringWidth(recipient_name, 'Helvetica-Bold', font_size) <= max_width:\n"
        "        break\n"
        "    font_size -= 2\n"
        "# Text is rendered at the dynamically calculated point size"
    )
    story.append(Paragraph(code_scaling.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style))

    story.append(Paragraph(
        "<b>Post-Generation Integrity Check:</b> Every generated file is immediately opened with <code>pypdf.PdfReader</code>. "
        "If the page tree is corrupt or unreadable, the file is unlinked, and the record transitions to <code>FAILED</code>.",
        body_style
    ))

    story.append(Paragraph("Worker Claiming & Concurrency Protection", h2_style))
    story.append(Paragraph(
        "To allow multiple worker processes to safely poll the same database without duplicate work, we use an "
        "<b>Atomic Compare-and-Swap SQL Update</b>:",
        body_style
    ))

    code_claim = (
        "claim_stmt = (\n"
        "    update(GenerationJob)\n"
        "    .where(GenerationJob.id == candidate_id, GenerationJob.status == 'PENDING')  # Guard condition\n"
        "    .values(status='PROCESSING', started_at=now, updated_at=now)\n"
        ")\n"
        "result = db.execute(claim_stmt)\n"
        "if result.rowcount == 0:\n"
        "    return None  # Another worker claimed the job; back off safely"
    )
    story.append(Paragraph(code_claim.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style))

    story.append(Paragraph("Per-Recipient Fault Isolation & Stale Recovery", h2_style))
    story.append(Paragraph(
        "The worker processes recipients in a loop where each recipient is wrapped in its own <code>try...except</code> block. "
        "If recipient #42 encounters a failure, its record is marked <code>FAILED</code>, the parent's <code>failed_count</code> "
        "is incremented, and the worker seamlessly proceeds to recipient #43. The batch concludes as <code>COMPLETED_WITH_ERRORS</code>.<br/>"
        "<b>Crash Recovery:</b> If the worker process is terminated mid-batch, <code>recover_stale_jobs()</code> identifies "
        "jobs stuck in <code>PROCESSING</code> whose heartbeat (<code>updated_at</code>) is older than 300 seconds, resets in-flight "
        "records to <code>PENDING</code>, and preserves already generated certificates, enabling seamless resumption.",
        body_style
    ))

    # =========================================================================
    # PHASE 7 & 8: SECURITY, ERRORS & STRUCTURE
    # =========================================================================
    story.append(Paragraph("Phase 7 & 8: Defensive Security, Error Handling & Packaging", h1_style))
    sec_points = [
        "<b>OWASP Security Headers:</b> Enforces <code>X-Content-Type-Options: nosniff</code>, <code>X-Frame-Options: DENY</code>, and <code>X-XSS-Protection: 1; mode=block</code>.",
        "<b>10 MB Payload Guard:</b> Custom middleware inspects <code>Content-Length</code> before reading the body, returning <code>HTTP 413 Content Too Large</code> on oversized payloads.",
        "<b>Path Traversal Shield:</b> Validates certificate IDs against <code>^[a-zA-Z0-9_-]+$</code> and verifies canonical paths via <code>Path.resolve().relative_to(base_dir)</code>.",
        "<b>Non-Root Container:</b> Production Dockerfile executes under a dedicated non-privileged user (<code>appuser</code>, UID 1001)."
    ]
    for pt in sec_points:
        story.append(Paragraph(f"• {pt}", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PHASE 10 & 11: TESTING & BENCHMARKS
    # =========================================================================
    story.append(Paragraph("Phase 10 & 11: Automated Testing & Empirical Benchmarks", h1_style))
    story.append(Paragraph(
        "<b>Automated Test Suite:</b> Built with Pytest, using isolated SQLite database fixtures, mock storage folders, "
        "and FastAPI's TestClient. Testing achieved <b>90% statement coverage</b> across 31 tests in 5.34 seconds:",
        body_style
    ))

    test_modules = [
        [Paragraph("<b>Test Module</b>", table_header), Paragraph("<b>Tests</b>", table_header), Paragraph("<b>Key Behaviors Verified</b>", table_header)],
        [Paragraph("<code>test_validation.py</code>", table_cell), Paragraph("5 passed", table_cell), Paragraph("Missing fields, empty recipient lists, whitespace trimming, duplicate emails.", table_cell)],
        [Paragraph("<code>test_pdf_generation.py</code>", table_cell), Paragraph("7 passed", table_cell), Paragraph("Vector layout, long name font scaling, verification codes, pypdf integrity.", table_cell)],
        [Paragraph("<code>test_job_lifecycle.py</code>", table_cell), Paragraph("1 passed", table_cell), Paragraph("End-to-end flow: Ingestion -> Enqueued -> Completed -> ZIP download.", table_cell)],
        [Paragraph("<code>test_failure_isolation.py</code>", table_cell), Paragraph("1 passed", table_cell), Paragraph("Fault containment: corrupt recipient produces COMPLETED_WITH_ERRORS.", table_cell)],
        [Paragraph("<code>test_worker_recovery.py</code>", table_cell), Paragraph("2 passed", table_cell), Paragraph("Worker crash detection, stale job reset, idempotent re-execution.", table_cell)],
        [Paragraph("<code>test_retrieval.py</code>", table_cell), Paragraph("3 passed", table_cell), Paragraph("Single PDF retrieval, batch ZIP streaming, non-existent 404 responses.", table_cell)],
        [Paragraph("<code>test_security.py</code>", table_cell), Paragraph("6 passed", table_cell), Paragraph("Path traversal attempts, incomplete download blocks, 10MB payload limits.", table_cell)],
        [Paragraph("<code>test_database_persistence.py</code>", table_cell), Paragraph("3 passed", table_cell), Paragraph("SQLite WAL persistence across engine restarts and multi-counter updates.", table_cell)],
        [Paragraph("<code>test_health.py</code>", table_cell), Paragraph("3 passed", table_cell), Paragraph("Liveness probes, database connection checks, readiness state.", table_cell)]
    ]
    t_test = Table(test_modules, colWidths=[130, 60, 340])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_test)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Empirical Performance Benchmarks", h2_style))
    story.append(Paragraph(
        "Measurements captured via <code>scripts/benchmark_performance.py</code> across varying batch sizes:",
        body_style
    ))

    bench_data = [
        [Paragraph("<b>Batch Size</b>", table_header), Paragraph("<b>Final Status</b>", table_header), Paragraph("<b>Total Time</b>", table_header), Paragraph("<b>Avg Time / Cert</b>", table_header), Paragraph("<b>Throughput</b>", table_header), Paragraph("<b>Peak RAM</b>", table_header), Paragraph("<b>Storage / PDF</b>", table_header)],
        [Paragraph("N = 10", table_cell), Paragraph("COMPLETED", table_cell), Paragraph("0.286 s", table_cell), Paragraph("28.64 ms", table_cell), Paragraph("34.9 certs/s", table_cell), Paragraph("1.08 MB", table_cell), Paragraph("3.23 KB", table_cell)],
        [Paragraph("N = 50", table_cell), Paragraph("COMPLETED", table_cell), Paragraph("1.289 s", table_cell), Paragraph("25.78 ms", table_cell), Paragraph("38.8 certs/s", table_cell), Paragraph("0.82 MB", table_cell), Paragraph("3.23 KB", table_cell)],
        [Paragraph("N = 100", table_cell), Paragraph("COMPLETED", table_cell), Paragraph("2.490 s", table_cell), Paragraph("24.90 ms", table_cell), Paragraph("40.2 certs/s", table_cell), Paragraph("0.94 MB", table_cell), Paragraph("3.23 KB", table_cell)],
        [Paragraph("N = 250", table_cell), Paragraph("COMPLETED_WITH_ERRORS", table_cell), Paragraph("6.332 s", table_cell), Paragraph("25.33 ms", table_cell), Paragraph("39.5 certs/s", table_cell), Paragraph("1.34 MB", table_cell), Paragraph("3.23 KB", table_cell)]
    ]
    t_bench = Table(bench_data, colWidths=[65, 120, 65, 75, 75, 65, 65])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 8))

    # =========================================================================
    # PHASE 12 & 13: DEPLOYMENT, BACKUPS & READINESS
    # =========================================================================
    story.append(Paragraph("Phase 12 & 13: Deployment, Backups & Production Readiness", h1_style))
    story.append(Paragraph(
        "<b>Deployment Strategies:</b><br/>"
        "• <b>Path A: Local Docker Compose:</b> Canonical multi-container setup (`cert_generator_api` and `cert_generator_worker`) "
        "sharing a named persistent Docker volume (`cert_data`).<br/>"
        "• <b>Path B: Verified Cloud Tier (Oracle Cloud Always Free):</b> 2 AMD Compute VMs or 4 ARM Ampere cores with "
        "<b>200 GB permanent block storage at $0 forever</b>. Does not sleep after 15 minutes, avoiding the PaaS ephemeral storage trap.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Operations & Maintenance:</b><br/>"
        "• <b>Online SQLite WAL Backup:</b> <code>python scripts/backup_restore.py backup ./backups</code> (safely backs up active database without blocking writers).<br/>"
        "• <b>72-Hour Storage Retention Pruning:</b> <code>python scripts/cleanup_retention.py</code> (automatically removes job directories older than 72 hours).",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PHASE 14: INTERVIEW DEFENSE & SYSTEM QUESTIONS
    # =========================================================================
    story.append(Paragraph("Phase 14: Senior Engineering Interview Defense", h1_style))
    story.append(Paragraph(
        "Concise technical answers for architectural and systems design interviews:",
        body_style
    ))

    interview_qa = [
        ("Q1: Why choose a database-backed worker over Celery + Redis?",
         "Eliminates the dual-write hazard between SQL and Redis by using a single atomic ACID transaction. "
         "Reduces infrastructure overhead and memory consumption to <60 MB, avoiding kernel OOM kills in free cloud containers."),

        ("Q2: Why not use FastAPI's built-in BackgroundTasks?",
         "BackgroundTasks runs in process heap memory. If the server crashes, restarts, or redeploys, all queued work is permanently "
         "lost. A database-backed worker guarantees full disk persistence before returning HTTP 202 Accepted."),

        ("Q3: How do you prevent race conditions across multiple workers?",
         "Using an Atomic Conditional SQL Update: UPDATE generation_jobs SET status='PROCESSING' WHERE id=:id AND status='PENDING'. "
         "Relational database engines serialize single-row updates. Exactly one worker receives rowcount == 1, while others receive 0 and back off."),

        ("Q4: How does SQLite support concurrency without locking up?",
         "By configuring Write-Ahead Logging (PRAGMA journal_mode = WAL;) and a 5,000ms busy timeout. Readers query the database "
         "without blocking writers, and writers append to the -wal log without blocking readers."),

        ("Q5: What happens when 1 recipient out of 500 fails?",
         "The worker isolates each recipient in an individual try/except block. Failed records are marked FAILED with an error code, "
         "the failed_count is incremented, and the worker continues. The job completes as COMPLETED_WITH_ERRORS."),

        ("Q6: How does the system recover from unexpected worker crashes?",
         "The worker records an updated_at heartbeat on each certificate. On polling, recover_stale_jobs() resets jobs stuck in "
         "PROCESSING older than 300 seconds to PENDING. In-flight records revert to PENDING, while completed certificates remain intact."),

        ("Q7: Why ReportLab instead of Puppeteer / Headless Chrome?",
         "ReportLab compiles vector PostScript graphics in ~25ms using ~1 MB RAM, producing crisp ~3.23 KB PDFs. "
         "Puppeteer uses ~300 MB RAM, takes ~1,500ms, and produces large 1 MB rasterized files."),

        ("Q8: How did you solve long recipient names overflowing certificates?",
         "Dynamic Font Auto-Scaling: The engine measures name width in points using canvas.stringWidth() and iteratively decrements "
         "the font size from 30pt down to 14pt until it fits comfortably within layout boundaries.")
    ]

    for q, a in interview_qa:
        q_box = [
            [Paragraph(f"<b>{q}</b>", table_header)],
            [Paragraph(a, table_cell)]
        ]
        t_q = Table(q_box, colWidths=[530])
        t_q.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY),
            ('BACKGROUND', (0,1), (-1,1), BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_q)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=4, spaceAfter=6))
    story.append(Paragraph(
        "<b>Conclusion:</b> The Bulk Certificate Generator demonstrates that production-grade durability, high throughput, "
        "and security do not require expensive cloud infrastructure. Through careful systems architecture, "
        "programmatic vector compilation, and transactional SQL state machines, enterprise-level performance can be achieved at $0 cost.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated documentation PDF: {filename}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "Bulk_Certificate_Generator_Complete_Project_Documentation.pdf"
    build_pdf(out_file)
