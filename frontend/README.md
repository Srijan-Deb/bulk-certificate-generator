# CertFlow Frontend — Bulk Certificate Generator

Premium, responsive React + TypeScript frontend tailored to the FastAPI backend in the supplied `Bulk Certificate Generator` repository. It does not replace or modify backend behavior.

## Implemented backend integration

The API client uses the routes found in `app/api/v1/jobs.py`, `certificates.py`, `health.py`, and `observability.py`:

- `GET /api/v1/health`
- `GET /api/v1/observability/stats`
- `POST /api/v1/jobs/upload` (`multipart/form-data`: `file`, `event_name`, `issuer_name`, `issue_date`, `certificate_title`)
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/certificates?status_filter=&limit=100&offset=0`
- `GET /api/v1/jobs/{job_id}/download-zip`
- `GET /api/v1/certificates/{certificate_id}/download?as_attachment=true`
- `GET /api/v1/jobs/upload/template`

The dashboard polls operational stats and health; an open job refreshes job status and up to 100 recipient records. Recent job IDs are saved in the current browser's local storage; the backend currently has no list-all-jobs route, so history is browser-local and is not presented as a server-wide list.

## Requirements

- Node.js 20+ recommended
- Existing FastAPI backend running on `http://127.0.0.1:8000`

## Local setup (Windows PowerShell)

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). Vite proxies `/api` to `http://127.0.0.1:8000` for local development. Change the proxy in `vite.config.ts` if your backend uses a different host or port.

Run the backend from the repository root in another terminal, using the environment and startup commands already documented by the project. For a typical local FastAPI setup, after activating the project's Python environment:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If using the project's Docker Compose setup, bring up its API and worker services as described in the repository README; the worker must be running for queued jobs to finish when `RUN_WORKER_IN_APP=false`.

## Environment variables

Copy `.env.example` to `.env`.

- `VITE_API_BASE_URL=`: leave blank for Vite's local `/api` proxy. For a separately hosted production UI, set this to the backend origin, e.g. `https://api.example.com` (no trailing slash).
- `VITE_API_KEY=`: optional. Set only if the backend has `API_KEY_ENABLED=True`; do not commit secrets or expose a privileged key in a public client bundle. For public production deployments, prefer server-side authentication or a narrowly scoped user key.
- `VITE_POLL_INTERVAL_MS=4000`: polling interval, with a 2-second minimum enforced by the client.

For a cross-origin deployment, configure backend `ALLOWED_ORIGINS` with the exact frontend origin. Do not use wildcard origins with credentialed authentication.

## Screens

- **Overview:** live backend health and metrics, generation outcome chart, quick actions, and recent browser-tracked jobs.
- **Generate certificates:** batch metadata form, drag/drop spreadsheet selection, sample-template download, and real multipart upload to the existing API.
- **Generation jobs:** tracked job list, job-ID lookup, live progress, success/failure/pending counts, recipient status filtering, individual PDF downloads, and ZIP download.

## Tests and production build

```powershell
npm test
npm run build
npm run preview
```

`npm test` exercises the API client's success, API-error, and network-error paths. `npm run build` creates the static production site in `dist/`. This package was prepared from static source inspection; run the commands above in your environment to confirm the installed dependency versions and build.

## Deployment

1. Set `VITE_API_BASE_URL` to the public API origin at build time (or configure a reverse proxy so the UI and API share an origin).
2. Run `npm ci` (after generating and committing a lockfile in your environment) and `npm run build`.
3. Deploy `dist/` to a static host such as Cloudflare Pages, GitHub Pages with SPA routing configured, or an Nginx static container.
4. Configure FastAPI CORS `ALLOWED_ORIGINS` to the deployed frontend origin if cross-origin.
5. Keep API keys and other secrets out of source control. `VITE_*` values are embedded in client assets and are public to users.
6. Verify `/api/v1/health`, upload a small test spreadsheet, watch status progress, check failed recipient details, and test both ZIP and individual PDF downloads.

## Known backend boundaries

- The current API exposes per-job status and recipients but no endpoint for a complete server-side job history. This frontend therefore tracks IDs in browser local storage and supports opening a known job ID.
- The current backend stats endpoint reports process-local counters. Metrics may reset when the API process restarts and may not aggregate across multiple API workers.
- No authentication screen was added because the supplied API does not expose a user-login/session contract. The optional API key is only a simple integration hook; do not embed a production secret in a public SPA.
