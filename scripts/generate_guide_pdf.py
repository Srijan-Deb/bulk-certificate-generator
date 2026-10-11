"""
PDF Generator for Bulk Certificate Generator: Start-to-Stop User Guide & Demo
Uses ReportLab to generate a clean, publication-grade multi-page PDF user manual.
"""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colors
PRIMARY = colors.HexColor("#1A365D")    # Deep Navy
SECONDARY = colors.HexColor("#2B6CB0")  # Royal Blue
ACCENT = colors.HexColor("#D69E2E")     # Muted Gold / Amber
DARK = colors.HexColor("#2D3748")       # Slate Charcoal
LIGHT_BG = colors.HexColor("#F7FAFC")   # Cool off-white
BORDER_COLOR = colors.HexColor("#E2E8F0")
SUCCESS_COLOR = colors.HexColor("#276749")
CODE_BG = colors.HexColor("#EDF2F7")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' footers and top headers."""
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Don't draw header on page 1 (cover header)
        if self._pageNumber > 1:
            self.drawString(54, 842 - 36, "Bulk Certificate Generator — Start-to-Stop User Guide & Demo")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(54, 842 - 42, 595 - 54, 842 - 42)

        # Footer on all pages
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(595 - 54, 30, footer_text)
        self.drawString(54, 30, "Confidential & Practical Developer Operations Manual • Local / Cloud Ready")
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 40, 595 - 54, 40)
        self.restoreState()


def build_guide_pdf(output_filename="Bulk_Certificate_Generator_Start_to_Stop_Guide.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        spaceAfter=15,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="SubsectionHeader",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="BodyTextCustom",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=DARK,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BulletText",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=DARK,
        leftIndent=15,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="CodeBlock",
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1A202C"),
        backColor=CODE_BG,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Callout",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=PRIMARY,
        backColor=LIGHT_BG,
        borderColor=SECONDARY,
        borderWidth=1,
        borderPadding=8,
        spaceBefore=6,
        spaceAfter=8,
    ))

    story = []

    # Title Banner
    story.append(Paragraph("🎓 Bulk Certificate Generator", styles["DocTitle"]))
    story.append(Paragraph("Complete Start-to-Stop Operations Manual & End-to-End Demo Walkthrough", styles["DocSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=12))

    # Executive Overview
    story.append(Paragraph("1. Executive Overview & System Architecture", styles["SectionHeader"]))
    story.append(Paragraph(
        "The Bulk Certificate Generator is a production-grade, asynchronous backend system built with "
        "<b>FastAPI</b>, <b>SQLAlchemy 2.0</b>, <b>SQLite (WAL mode)</b>, and <b>ReportLab vector graphics</b>. "
        "It generates high-throughput, tamper-evident certificates with cryptographic verification codes "
        "at zero cloud infrastructure cost (₹0 / $0).",
        styles["BodyTextCustom"]
    ))

    # Architecture Overview Table
    arch_data = [
        [Paragraph("<b>Component</b>", styles["BodyTextCustom"]), Paragraph("<b>Technology</b>", styles["BodyTextCustom"]), Paragraph("<b>Role / Purpose</b>", styles["BodyTextCustom"])],
        [Paragraph("API Web Layer", styles["BodyTextCustom"]), Paragraph("FastAPI + Uvicorn", styles["BodyTextCustom"]), Paragraph("Handles async ingestion, validations, and file downloads", styles["BodyTextCustom"])],
        [Paragraph("Database", styles["BodyTextCustom"]), Paragraph("SQLite in WAL Mode", styles["BodyTextCustom"]), Paragraph("Stores jobs, recipients, and real-time processing counters", styles["BodyTextCustom"])],
        [Paragraph("Job Worker", styles["BodyTextCustom"]), Paragraph("Background Thread / Runner", styles["BodyTextCustom"]), Paragraph("Pulls pending jobs, isolates failures, renders PDFs", styles["BodyTextCustom"])],
        [Paragraph("PDF Vector Engine", styles["BodyTextCustom"]), Paragraph("ReportLab Open-Source", styles["BodyTextCustom"]), Paragraph("Vector rendering (~25ms per certificate) with auto-scaling text", styles["BodyTextCustom"])],
        [Paragraph("Storage", styles["BodyTextCustom"]), Paragraph("Local Filesystem (storage/)", styles["BodyTextCustom"]), Paragraph("Stores organized per-job PDFs and zipped download archives", styles["BodyTextCustom"])],
    ]
    t_arch = Table(arch_data, colWidths=[110, 130, 240])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    # Section 2: What Goes Where
    story.append(Paragraph("2. Where What Goes: Directory & Input Mapping", styles["SectionHeader"]))
    story.append(Paragraph("A quick roadmap of files and directories you will interact with:", styles["BodyTextCustom"]))

    mapping_data = [
        [Paragraph("<b>Purpose</b>", styles["BodyTextCustom"]), Paragraph("<b>File / Folder Path</b>", styles["BodyTextCustom"]), Paragraph("<b>Action / Instructions</b>", styles["BodyTextCustom"])],
        [Paragraph("Configuration", styles["BodyTextCustom"]), Paragraph("<code>.env</code>", styles["BodyTextCustom"]), Paragraph("Edit database location, worker batch size, and storage retention.", styles["BodyTextCustom"])],
        [Paragraph("Recipient Input", styles["BodyTextCustom"]), Paragraph("<code>POST /api/v1/jobs</code>", styles["BodyTextCustom"]), Paragraph("Submit recipient names, email addresses, and event metadata.", styles["BodyTextCustom"])],
        [Paragraph("Output PDFs", styles["BodyTextCustom"]), Paragraph("<code>storage/certificates/{job_id}/</code>", styles["BodyTextCustom"]), Paragraph("Contains generated, validated vector PDF files.", styles["BodyTextCustom"])],
        [Paragraph("ZIP Downloads", styles["BodyTextCustom"]), Paragraph("<code>GET /api/v1/jobs/{id}/download</code>", styles["BodyTextCustom"]), Paragraph("Bundles all generated certificates in a single compressed file.", styles["BodyTextCustom"])],
        [Paragraph("Design & Styling", styles["BodyTextCustom"]), Paragraph("<code>app/services/certificate_service.py</code>", styles["BodyTextCustom"]), Paragraph("Adjust border styles, coordinates, fonts, and gold seal layout.", styles["BodyTextCustom"])],
    ]
    t_map = Table(mapping_data, colWidths=[90, 170, 220])
    t_map.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_map)
    story.append(Spacer(1, 10))

    # Section 3: Understanding the API Key
    story.append(Paragraph("3. Understanding the API Key (Do You Need One?)", styles["SectionHeader"]))
    story.append(Paragraph(
        "<b>Important Clarification:</b> You do <u>not</u> get this API key from any external website, cloud account, "
        "or third-party vendor. This is not a paid API key like OpenAI or Google Cloud. It is an internal security mechanism "
        "that prevents unauthorized users from calling your server if it is exposed online.",
        styles["BodyTextCustom"]
    ))
    story.append(Paragraph(
        "• <b>Default Local Setup:</b> <code>API_KEY_ENABLED=false</code> in <code>.env</code>. You leave the <code>X-API-Key</code> "
        "box completely <b>empty</b> in Swagger UI or API requests.<br/>"
        "• <b>To Enable Security:</b> Generate your own secure token in PowerShell:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>python -c \"import secrets; print(secrets.token_urlsafe(32))\"</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Then update <code>.env</code> with: <code>API_KEY_ENABLED=true</code> and <code>API_KEY=\"your_token\"</code>.",
        styles["Callout"]
    ))

    story.append(PageBreak())

    # Section 4: How to Start the System
    story.append(Paragraph("4. How to Start the System", styles["SectionHeader"]))
    story.append(Paragraph("Follow these exact steps in your Windows PowerShell terminal:", styles["BodyTextCustom"]))

    story.append(Paragraph("<b>Step 1: Open Terminal & Activate the Virtual Environment</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "cd \"c:\\Users\\dell\\Downloads\\Bulk Certificate Generator\"<br/>"
        ".\\.venv\\Scripts\\Activate.ps1",
        styles["CodeBlock"]
    ))
    story.append(Paragraph("<i>(You will see <code>(.venv)</code> appear at the start of your terminal prompt).</i>", styles["BodyTextCustom"]))

    story.append(Paragraph("<b>Step 2: Start the Web API & Integrated Background Worker</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000",
        styles["CodeBlock"]
    ))
    story.append(Paragraph(
        "By default, <code>RUN_WORKER_IN_APP=true</code> in <code>app/core/config.py</code>. This means launching Uvicorn "
        "automatically boots both the <b>REST API server</b> AND the <b>background worker thread</b> in a single command.",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph("<b>Step 3: Verify the Running System in Your Browser</b>", styles["SubsectionHeader"]))
    story.append(Paragraph("• <b>Swagger Interactive UI:</b> <font color='#2B6CB0'>http://127.0.0.1:8000/docs</font><br/>"
                           "• <b>ReDoc Technical Spec:</b> <font color='#2B6CB0'>http://127.0.0.1:8000/redoc</font><br/>"
                           "• <b>System Health Check:</b> <font color='#2B6CB0'>http://127.0.0.1:8000/api/v1/health</font>",
                           styles["BulletText"]))

    story.append(Spacer(1, 10))

    # Section 5: How to Run a Live Demo Batch
    story.append(Paragraph("5. Step-by-Step Live Demo Walkthrough", styles["SectionHeader"]))
    story.append(Paragraph(
        "Here is the complete walkthrough of submitting a job, watching it process, and downloading the finished files:",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph("<b>Option A: Quick Automated Demo (Via Python Script)</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "Open a second PowerShell terminal and run:<br/>"
        "<code>python scripts\\create_demo_job.py</code>",
        styles["CodeBlock"]
    ))
    story.append(Paragraph(
        "This script submits 5 diverse recipients, tracks progress to 100%, and downloads "
        "<code>demo_job_xxxx_certificates.zip</code> to your root folder automatically.",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph("<b>Option B: Interactive Demo (Via Swagger UI in Browser)</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "<b>1. Open Swagger:</b> Go to <code>http://127.0.0.1:8000/docs</code>.<br/>"
        "<b>2. Submit Job:</b> Expand <code>POST /api/v1/jobs</code> → Click <b>'Try it out'</b>.<br/>"
        "<b>3. Leave <code>X-API-Key</code> blank.</b><br/>"
        "<b>4. Paste your JSON payload into Request Body:</b>",
        styles["BodyTextCustom"]
    ))

    sample_json = (
        '{\n'
        '  "event_name": "Full Stack AI Bootcamp 2026",\n'
        '  "issuer_name": "Tech Architecture Academy",\n'
        '  "issue_date": "2026-10-11",\n'
        '  "certificate_title": "Certificate of Completion",\n'
        '  "recipients": [\n'
        '    {\n'
        '      "recipient_name": "Ada Lovelace",\n'
        '      "recipient_email": "ada@example.com",\n'
        '      "custom_remarks": "First Programmer"\n'
        '    },\n'
        '    {\n'
        '      "recipient_name": "Alan Turing",\n'
        '      "recipient_email": "alan@example.com",\n'
        '      "custom_remarks": "Distinguished Scholar"\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    story.append(Paragraph(sample_json.replace('\n', '<br/>').replace(' ', '&nbsp;'), styles["CodeBlock"]))

    story.append(Paragraph(
        "<b>5. Click Execute:</b> You will receive HTTP <code>202 Accepted</code> containing a unique <code>job_id</code>.<br/>"
        "<b>6. Check Status:</b> Expand <code>GET /api/v1/jobs/{job_id}</code>, enter your <code>job_id</code>, and click <b>Execute</b>.<br/>"
        "<b>7. Download ZIP:</b> Expand <code>GET /api/v1/jobs/{job_id}/download</code>, enter the <code>job_id</code>, click <b>Execute</b>, and click <b>'Download file'</b>.",
        styles["BodyTextCustom"]
    ))

    story.append(PageBreak())

    # Section 6: How to Stop the Project
    story.append(Paragraph("6. How to Stop the Project Gracefully", styles["SectionHeader"]))
    story.append(Paragraph(
        "To stop the running application cleanly without database corruption or interrupted jobs:",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph("<b>Standard Method: Keyboard Interrupt</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "1. Click into the PowerShell terminal window where Uvicorn is currently running.<br/>"
        "2. Press <b>Ctrl + C</b> on your keyboard.<br/>"
        "3. Uvicorn will cleanly trigger its shutdown lifespan handlers:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• Shuts down the in-app background worker.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• Commits open SQLite transactions.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• Closes all database connections safely.",
        styles["BodyTextCustom"]
    ))

    story.append(Paragraph("<b>Forcing a Stuck Process to Close (If Port 8000 Remains Occupied)</b>", styles["SubsectionHeader"]))
    story.append(Paragraph(
        "If you ever see <code>[WinError 10013]</code> or <code>address already in use</code>, close the lingering process using PowerShell:",
        styles["BodyTextCustom"]
    ))
    story.append(Paragraph(
        "# Find process listening on port 8000:\n"
        "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess\n\n"
        "# Terminate any lingering Uvicorn or Python processes:\n"
        "Stop-Process -Name python -Force",
        styles["CodeBlock"]
    ))

    story.append(Spacer(1, 10))

    # Section 7: Verification & Security Features
    story.append(Paragraph("7. Certificate Verification & Security Architecture", styles["SectionHeader"]))
    story.append(Paragraph(
        "Every certificate produced by this system incorporates zero-cost enterprise security measures:",
        styles["BodyTextCustom"]
    ))

    features_data = [
        [Paragraph("<b>Feature</b>", styles["BodyTextCustom"]), Paragraph("<b>Mechanism</b>", styles["BodyTextCustom"]), Paragraph("<b>Protection Provided</b>", styles["BodyTextCustom"])],
        [Paragraph("Tamper Verification", styles["BodyTextCustom"]), Paragraph("Deterministic SHA-256 Code (<code>V-XXXX-XXXX-XXXX</code>)", styles["BodyTextCustom"]), Paragraph("Cryptographically binds recipient, job ID, and issue date.", styles["BodyTextCustom"])],
        [Paragraph("Post-Generation Validation", styles["BodyTextCustom"]), Paragraph("<code>pypdf.PdfReader</code> structural inspection", styles["BodyTextCustom"]), Paragraph("Guarantees that corrupted PDFs are never delivered.", styles["BodyTextCustom"])],
        [Paragraph("Crash Recovery", styles["BodyTextCustom"]), Paragraph("Stale Job Lease Timeout (<code>recover_stale_jobs</code>)", styles["BodyTextCustom"]), Paragraph("Recovers jobs stranded if the server dies unexpectedly.", styles["BodyTextCustom"])],
        [Paragraph("Fault Isolation", styles["BodyTextCustom"]), Paragraph("Per-recipient try/catch boundary", styles["BodyTextCustom"]), Paragraph("Single corrupt name does not fail the other recipients.", styles["BodyTextCustom"])],
    ]
    t_feat = Table(features_data, colWidths=[120, 170, 190])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_feat)

    story.append(Spacer(1, 14))
    story.append(Paragraph("8. Summary Quick-Reference Card", styles["SectionHeader"]))

    card_data = [
        [Paragraph("<b>Action</b>", styles["BodyTextCustom"]), Paragraph("<b>Command / URL</b>", styles["BodyTextCustom"])],
        [Paragraph("Activate Environment", styles["BodyTextCustom"]), Paragraph("<code>.\\.venv\\Scripts\\Activate.ps1</code>", styles["BodyTextCustom"])],
        [Paragraph("Start Server", styles["BodyTextCustom"]), Paragraph("<code>uvicorn app.main:app --reload --host 127.0.0.1 --port 8000</code>", styles["BodyTextCustom"])],
        [Paragraph("Stop Server", styles["BodyTextCustom"]), Paragraph("<b>Ctrl + C</b> in terminal", styles["BodyTextCustom"])],
        [Paragraph("API Documentation", styles["BodyTextCustom"]), Paragraph("<b>http://127.0.0.1:8000/docs</b>", styles["BodyTextCustom"])],
        [Paragraph("Run Client Demo", styles["BodyTextCustom"]), Paragraph("<code>python scripts\\create_demo_job.py</code>", styles["BodyTextCustom"])],
        [Paragraph("Run All Automated Tests", styles["BodyTextCustom"]), Paragraph("<code>pytest</code>", styles["BodyTextCustom"])],
        [Paragraph("PDF Storage Folder", styles["BodyTextCustom"]), Paragraph("<code>storage/certificates/</code>", styles["BodyTextCustom"])],
    ]
    t_card = Table(card_data, colWidths=[140, 340])
    t_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_card)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated User Guide PDF at: {Path(output_filename).resolve()}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "Bulk_Certificate_Generator_Start_to_Stop_Guide.pdf"
    build_guide_pdf(out)
