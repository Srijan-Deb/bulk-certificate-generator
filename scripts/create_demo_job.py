"""
Demo Bulk Job Submission Script
Demonstrates end-to-end client interaction with the Bulk Certificate Generator API:
1. Submits a bulk job with 5 sample recipients (including a long name and custom honors).
2. Polls the job status URL until completion.
3. Downloads the combined ZIP archive of all generated certificates.
Usage:
    python scripts/create_demo_job.py
"""

import sys
import time
from pathlib import Path

import httpx

API_BASE = "http://127.0.0.1:8000/api/v1"

SAMPLE_PAYLOAD = {
    "event_name": "Executive Backend Architecture Masterclass",
    "issuer_name": "Global Software Engineering Institute",
    "issue_date": "2026-10-10",
    "certificate_title": "Certificate of Excellence",
    "recipients": [
        {"recipient_name": "Ada Lovelace", "recipient_email": "ada@example.com", "custom_remarks": "First Programmer"},
        {"recipient_name": "Alan Turing", "recipient_email": "alan@example.com", "custom_remarks": "Father of Computing"},
        {"recipient_name": "Grace Hopper", "recipient_email": "grace@example.com", "custom_remarks": "Compiler Pioneer"},
        {"recipient_name": "Margaret Hamilton", "recipient_email": "margaret@example.com", "custom_remarks": "Apollo Lead Software Engineer"},
        {"recipient_name": "Dr. Alexander Montgomery Bartholomew-Fitzgerald III", "recipient_email": "alex@example.com", "custom_remarks": "Distinguished Scholar"},
    ],
}


def main():
    print("==================================================================")
    print("  Bulk Certificate Generator — Demo End-to-End Client Workflow")
    print("==================================================================")

    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        # Step 1: Health Check Probe
        print("\n[1/4] Checking API Health Probes...")
        try:
            health_resp = client.get("/health")
            if health_resp.status_code != 200:
                print(f"ERROR: API returned unexpected status {health_resp.status_code}")
                sys.exit(1)
            print(f"      API is healthy: {health_resp.json()['status']} (env: {health_resp.json()['environment']})")
        except httpx.ConnectError:
            print("ERROR: Unable to connect to API at http://127.0.0.1:8000. Is Uvicorn running?")
            sys.exit(1)

        # Step 2: Submit Bulk Job
        print(f"\n[2/4] Submitting bulk job with {len(SAMPLE_PAYLOAD['recipients'])} recipients...")
        post_resp = client.post("/jobs", json=SAMPLE_PAYLOAD)
        if post_resp.status_code != 202:
            print(f"ERROR: Job submission failed with {post_resp.status_code}: {post_resp.text}")
            sys.exit(1)

        data = post_resp.json()
        job_id = data["job_id"]
        status_url = data["status_url"]
        print(f"      Job Accepted! ID: {job_id}")
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

        output_zip = Path(f"demo_job_{job_id[:8]}_certificates.zip")
        output_zip.write_bytes(zip_resp.content)
        print(f"      Successfully saved ZIP archive to: {output_zip.resolve()} ({len(zip_resp.content)} bytes)")
        print("\nDemo workflow completed successfully!")


if __name__ == "__main__":
    main()
