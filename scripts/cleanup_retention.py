"""
Storage Retention Policy & Cleanup Utility
Scans the certificate storage directory and removes job directories
older than the configured retention threshold (MAX_FILE_RETENTION_HOURS).
Can be scheduled via cron or run as a periodic maintenance task.
Usage:
    python scripts/cleanup_retention.py [--dry-run]
"""

import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings


def cleanup_expired_jobs(dry_run: bool = False) -> int:
    storage_dir = settings.STORAGE_DIR.resolve()
    if not storage_dir.exists():
        print(f"Storage directory '{storage_dir}' does not exist. Nothing to clean.")
        return 0

    max_age_seconds = settings.MAX_FILE_RETENTION_HOURS * 3600
    cutoff_timestamp = time.time() - max_age_seconds
    cutoff_dt = datetime.fromtimestamp(cutoff_timestamp, tz=timezone.utc)

    print("==================================================================")
    print("  Bulk Certificate Generator — Storage Retention Cleanup")
    print("==================================================================")
    print(f"Storage Path:       {storage_dir}")
    print(f"Retention Limit:    {settings.MAX_FILE_RETENTION_HOURS} hours")
    print(f"Expiration Cutoff:  {cutoff_dt.isoformat()}")
    print(f"Mode:               {'DRY RUN (no deletions)' if dry_run else 'ACTIVE (purging expired)'}\n")

    pruned_count = 0
    total_bytes_freed = 0

    for item in storage_dir.iterdir():
        # Only process job subdirectories (UUID format or alphanumeric)
        if item.is_dir() and item.name != ".gitkeep":
            dir_stat = item.stat()
            # Check modification time
            if dir_stat.st_mtime < cutoff_timestamp:
                dir_size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                age_hours = round((time.time() - dir_stat.st_mtime) / 3600, 1)
                print(f"  [EXPIRED] Job '{item.name}' (Age: {age_hours}h, Size: {round(dir_size / 1024, 1)} KB)")

                if not dry_run:
                    shutil.rmtree(item)
                    print(f"            Purged directory '{item}'.")

                pruned_count += 1
                total_bytes_freed += dir_size

    print("-" * 66)
    print(f"Summary: {pruned_count} job directorie(s) identified. Total freed: {round(total_bytes_freed / 1024, 1)} KB.")
    return pruned_count


if __name__ == "__main__":
    is_dry_run = "--dry-run" in sys.argv
    cleanup_expired_jobs(dry_run=is_dry_run)
