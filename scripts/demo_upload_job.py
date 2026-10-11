"""
Demo Spreadsheet Upload Client Script
Demonstrates end-to-end client interaction with POST /api/v1/jobs/upload:
1. Verifies API health.
2. Uploads recipients.xlsx with event metadata form fields.
3. Polls the job status endpoint until generation completes.
4. Downloads the resulting ZIP archive of all certificates.
Usage:
    python scripts/demo_upload_job.py
"""

import sys
import time
from pathlib import Path

import httpx

API_BASE = "http://127.0.0.1:8000/api/v1"
SPREADSHEET_PATH = Path("recipients.xlsx")

FORM_DATA = {
    "event_name": "Executive Cloud & Backend Engineering Summit 2026",
    "issuer_name": "Global Tech Institute",
    "issue_date": "2026-10-11",
    "certificate_title": "Certificate of Excellence",
}


def main():
    print("==================================================================")
    print("  Bulk Certificate Generator — Spreadsheet Upload Demo Workflow")
    print("==================================================================")

    if not SPREADSHEET_PATH.exists():
        print(f"ERROR: {SPREADSHEET_PATH} does not exist. Generating a sample file...")
        from app.services.spreadsheet_parser import spreadsheet_parser
        SPREADSHEET_PATH.write_bytes(spreadsheet_parser.generate_sample_recipients_excel())

    with httpx.Client(base_url=API_BASE, timeout=15.0) as client:
        # Step 1: Health Check Probe
        print("\n[1/4] Checking API Health Probe...")
        try:
            health_resp = client.get("/health")
            if health_resp.status_code != 200:
                print(f"ERROR: API returned unexpected status {health_resp.status_code}")
                sys.exit(1)
            print(f"      API is healthy: {health_resp.json()['status']} (env: {health_resp.json()['environment']})")
        except httpx.ConnectError:
            print("ERROR: Unable to connect to API at http://127.0.0.1:8000. Is Uvicorn running?")
            print("      Start the server with: uvicorn app.main:app --reload")
            sys.exit(1)

        # Step 2: Upload Spreadsheet
        print(f"\n[2/4] Uploading '{SPREADSHEET_PATH.name}' via POST /jobs/upload...")
        with open(SPREADSHEET_PATH, "rb") as f:
            files = {
                "file": (
                    SPREADSHEET_PATH.name,
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            post_resp = client.post("/jobs/upload", data=FORM_DATA, files=files)

        if post_resp.status_code != 202:
            print(f"ERROR: Spreadsheet upload failed with {post_resp.status_code}: {post_resp.text}")
            sys.exit(1)

        data = post_resp.json()
        job_id = data["job_id"]
        status_url = data["status_url"]
        print(f"      Job Accepted! ID: {job_id}")
        print(f"      Total recipients queued: {data['total_recipients']}")
        print(f"      Status URL: {status_url}")

        # Step 3: Poll Job Status
        print("\n[3/4] Polling job status until generation completes...")
        max_attempts = 30
        completed = False
        final_status = {}

        for attempt in range(1, max_attempts + 1):
            time.sleep(1.0)
            status_resp = client.get(f"/jobs/{job_id}")
            if status_resp.status_code != 200:
                print(f"      Poll attempt {attempt} failed with status {status_resp.status_code}")
                continue

            final_status = status_resp.json()
            st = final_status["status"]
            prog = final_status["progress_percentage"]
            succ = final_status["successful_count"]
            tot = final_status["total_recipients"]
            print(f"      [{attempt:02d}s] Status: {st:<22} | Progress: {prog:>5.1f}% | Completed: {succ}/{tot}")

            if st in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                completed = True
                break

        if not completed:
            print("\nWARNING: Job did not complete within the timeout window.")
            sys.exit(1)

        # Step 4: Download ZIP Archive
        print("\n[4/4] Downloading generated certificate ZIP archive...")
        zip_resp = client.get(f"/jobs/{job_id}/download")
        if zip_resp.status_code != 200:
            print(f"ERROR: ZIP download failed with {zip_resp.status_code}: {zip_resp.text}")
            sys.exit(1)

        output_zip = Path(f"uploaded_job_{job_id[:8]}_certificates.zip")
        output_zip.write_bytes(zip_resp.content)
        print(f"      Successfully saved ZIP archive to: {output_zip.resolve()} ({len(zip_resp.content)} bytes)")
        print("\nSpreadsheet upload workflow completed successfully!")


if __name__ == "__main__":
    main()
