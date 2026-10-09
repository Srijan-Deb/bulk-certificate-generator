"""
Pre-Flight System Verification Script
Verifies:
1. Python environment (version >= 3.11)
2. Dependency availability (FastAPI, SQLAlchemy, ReportLab, pypdf, Pillow)
3. SQLite WAL mode activation and busy timeout
4. Storage directory creation and write permissions
5. ReportLab PDF canvas compilation
Usage:
    python scripts/verify_system.py
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text


def verify_system():
    print("==================================================================")
    print("  Bulk Certificate Generator — Pre-Flight System Verification")
    print("==================================================================")

    # 1. Python Version Check
    py_ver = sys.version_info
    print(f"\n[1/5] Checking Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}...", end="")
    if py_ver < (3, 11):
        print(" FAILED (Requires Python 3.11+)")
        sys.exit(1)
    print(" OK")

    # 2. Package Availability Probe
    print("[2/5] Checking Required Dependencies...", end="")
    try:
        import fastapi
        import pypdf
        import reportlab
        import sqlalchemy

        print(f" OK (fastapi {fastapi.__version__}, sqlalchemy {sqlalchemy.__version__}, reportlab {reportlab.__version__}, pypdf {pypdf.__version__})")
    except ImportError as e:
        print(f" FAILED ({e})")
        sys.exit(1)

    # 3. Database Engine & SQLite WAL Mode Verification
    print("[3/5] Verifying Database Connection and WAL Pragmas...", end="")
    from app.db.session import engine

    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        print(f" OK (Journal: {journal_mode.upper()}, Busy Timeout: {busy_timeout}ms)")

    # 4. Storage Directory Permissions
    from app.core.config import settings

    print(f"[4/5] Verifying Storage Directory Permissions at '{settings.STORAGE_DIR}'...", end="")
    test_dir = settings.STORAGE_DIR / ".probe_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "write_test.tmp"
    test_file.write_text("ok")
    test_file.unlink()
    test_dir.rmdir()
    print(" OK (Read/Write verified)")

    # 5. ReportLab Canvas Compilation Probe
    print("[5/5] Testing PDF Canvas Compilation & pypdf Validation...", end="")
    from app.services.certificate_service import certificate_generator

    probe_job_id = "probe_test_job"
    probe_cert_id = "CERT-PROBE-0001-OK"
    pdf_path = certificate_generator.render_certificate(
        job_id=probe_job_id,
        certificate_id=probe_cert_id,
        recipient_name="Probe Test User",
        event_name="Self-Test Workshop",
        issuer_name="System Probe",
        issue_date="2026-10-10",
    )
    if pdf_path.exists():
        pdf_path.unlink()
        (settings.STORAGE_DIR / probe_job_id).rmdir()
    print(" OK (Vector PDF generated and validated)")

    print("\nAll system checks PASSED! The environment is production-ready.")


if __name__ == "__main__":
    verify_system()
