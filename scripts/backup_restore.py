"""
Database and Certificate Storage Backup & Restore Utility
Uses SQLite's online backup API (safe for active WAL transactions)
and archives generated certificate files.
Usage:
    python scripts/backup_restore.py backup [output_dir]
    python scripts/backup_restore.py restore <backup_tar_path>
"""

import shutil
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings


def backup_system(output_dir: Path | None = None) -> Path:
    target_dir = output_dir or Path("./backups")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_archive = target_dir / f"cert_backup_{timestamp}.tar.gz"

    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:////", "")).resolve()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Online Safe SQLite Backup (WAL-compatible, locks writer safely)
        if db_path.exists():
            backup_db_path = tmp_path / "data.db"
            print(f"[1/3] Performing safe online SQLite backup from '{db_path}'...")
            src_conn = sqlite3.connect(str(db_path))
            dst_conn = sqlite3.connect(str(backup_db_path))
            with dst_conn:
                src_conn.backup(dst_conn, pages=100)
            dst_conn.close()
            src_conn.close()
            print("      SQLite online backup completed.")
        else:
            print(f"[1/3] Database file '{db_path}' not found. Skipping DB backup.")

        # 2. Copy Certificate Storage
        storage_path = settings.STORAGE_DIR.resolve()
        backup_storage_path = tmp_path / "certificates"
        if storage_path.exists():
            print(f"[2/3] Copying certificate storage from '{storage_path}'...")
            shutil.copytree(str(storage_path), str(backup_storage_path), dirs_exist_ok=True)
            print("      Certificate storage copied.")

        # 3. Create Compressed Tarball Archive
        print(f"[3/3] Creating compressed archive: '{backup_archive}'...")
        with tarfile.open(backup_archive, "w:gz") as tar:
            if (tmp_path / "data.db").exists():
                tar.add(str(tmp_path / "data.db"), arcname="data.db")
            if backup_storage_path.exists():
                tar.add(str(backup_storage_path), arcname="certificates")

    print(f"\nSUCCESS: Backup archive created at: {backup_archive.resolve()} ({backup_archive.stat().st_size} bytes)")
    return backup_archive


def restore_system(backup_archive_path: Path):
    if not backup_archive_path.exists() or not backup_archive_path.is_file():
        print(f"ERROR: Backup archive '{backup_archive_path}' does not exist.")
        sys.exit(1)

    print(f"Restoring system state from archive: '{backup_archive_path}'...")
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:////", "")).resolve()
    storage_path = settings.STORAGE_DIR.resolve()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with tarfile.open(backup_archive_path, "r:gz") as tar:
            tar.extractall(path=tmp_path)

        # 1. Restore Database
        extracted_db = tmp_path / "data.db"
        if extracted_db.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # Remove any active WAL/SHM files to avoid stale locks
            wal_file = Path(f"{db_path}-wal")
            shm_file = Path(f"{db_path}-shm")
            if wal_file.exists():
                wal_file.unlink()
            if shm_file.exists():
                shm_file.unlink()

            shutil.copy2(str(extracted_db), str(db_path))
            print(f"      Restored SQLite database to '{db_path}'.")

        # 2. Restore Certificates
        extracted_storage = tmp_path / "certificates"
        if extracted_storage.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(extracted_storage), str(storage_path), dirs_exist_ok=True)
            print(f"      Restored certificates to '{storage_path}'.")

    print("\nSUCCESS: Restore completed successfully.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/backup_restore.py backup [output_dir]")
        print("  python scripts/backup_restore.py restore <backup_tar_path>")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "backup":
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        backup_system(out)
    elif action == "restore":
        if len(sys.argv) < 3:
            print("ERROR: Must provide archive path to restore.")
            sys.exit(1)
        restore_system(Path(sys.argv[2]))
    else:
        print(f"Unknown action: '{action}'. Use 'backup' or 'restore'.")
        sys.exit(1)
