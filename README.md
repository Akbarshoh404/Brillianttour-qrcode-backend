# PDF Manager — Backend

## What this actually is

Brilliant Tour hands out a lot of PDFs — menus, brochures, itineraries,
price sheets. The old way was: print a QR code, and the moment the file
needs updating, the QR code is dead — reprint everything.

This service fixes that. Every PDF gets one **permanent** QR code the day
it's uploaded. Scan it next year and it still works, even if the file
behind it has been replaced five times since. Internally, a document's
identity (its UUID) is completely decoupled from the actual PDF file sitting
in storage — replacing a file just swaps what the UUID points to.

This is the API and business logic behind that: upload handling, QR
generation, the permanent `/p/{uuid}` redirect that every printed QR code
points to, and the scan/download analytics collected along the way (so you
can eventually answer "is anyone actually scanning this brochure?").

It also gives the team a lever over each QR code after it's printed: turn
one off without deleting it (say, a client stops paying and you want to
pause access, not destroy the file), and a trash bin that gives a week's
grace period before a deletion is truly permanent.

There are no user accounts — just one shared dashboard login (see
[Auth](#auth)). Anyone with a printed QR code or a PDF link never needs to
authenticate; the login only gates the management side (viewing the
dashboard, uploading, replacing, disabling, deleting).

## How a document's life cycle works

1. **Upload** — a PDF comes in, gets a random UUID, is pushed to Supabase
   Storage, and a database row is created. A QR code encoding
   `{PUBLIC_BASE_URL}/p/{uuid}` is generated **on the fly** whenever
   requested — it is never saved as a file anywhere.
2. **Scan** — someone scans the printed QR code, which hits
   `GET /p/{uuid}`. The backend logs the scan and redirects the phone
   straight to the current PDF via a freshly-signed, short-lived Supabase
   Storage URL. See [Analytics](#analytics--what-gets-tracked) for exactly
   what's collected.
3. **Replace** — if the brochure gets a price update, someone uploads the
   new PDF through `PUT /documents/{uuid}`. The UUID doesn't change, so
   every QR code already printed keeps working — it now just serves the new
   file. The old file is deleted from storage after the new one is
   confirmed uploaded, so a failed upload can never corrupt a live QR code.
4. **Disable / enable** — `POST /documents/{uuid}/disable` turns a QR code
   off without touching the file or its history. Scanning it while disabled
   still gets logged (as an attempted scan) but shows a "currently
   unavailable" page instead of the PDF. `POST /documents/{uuid}/enable`
   turns it back on, instantly, with nothing lost.
5. **Delete → trash → purge** — `DELETE /documents/{uuid}` moves a document
   to the trash (`deleted_at` is set); its QR code immediately starts
   showing a 404. It stays recoverable via `POST /documents/{uuid}/restore`
   for `TRASH_RETENTION_DAYS` (7 by default), after which it's purged
   automatically — permanently deleting the database row and the storage
   object. `DELETE /documents/trash/{uuid}` skips the waiting period and
   deletes immediately. Purging happens lazily (checked whenever the
   document list or trash list is fetched) rather than via a background
   scheduler, so there's no long-running worker process to keep alive.

## Auth

One shared credential (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) gates the
dashboard. `POST /auth/login` verifies it and returns a JWT; every
`/documents/*` route requires that JWT as a Bearer token. Nothing else does
— `/p/{uuid}`, `/download/{uuid}`, and `/health` stay open to anyone,
because the people scanning a QR code or clicking a shared link are never
the same audience as whoever manages the dashboard.

There's no registration, no password reset flow, no multi-user support —
it's one password for one small team, deliberately simple. If this ever
needs more than that, the JWT dependency (`get_current_admin` in
`app/api/deps.py`) is the one seam to extend.

## Analytics — what gets tracked

Every field collected on a scan is **passive**: pulled from the IP address
and HTTP headers already present on the incoming request, or from a geo-IP
lookup keyed on that IP. Nothing here requests a browser permission (there
is no way to get precise GPS-level location without one, and this
deliberately doesn't try to work around that) — this is the same class of
data every server access log and analytics tool on the web already
collects.

Per scan: approximate country/city/region (from geo-IP), ISP, lat/long,
timezone, browser/OS/device (parsed from the User-Agent, preferring
Client Hints headers like `Sec-CH-UA-Platform` when the browser sends them
— more reliable than string-sniffing), the referring page, and the
browser's primary language (`Accept-Language`). `GET
/documents/{uuid}/scans/summary` aggregates all of this into
country/device/browser breakdowns plus a recent-scans feed, which backs the
expandable detail view on each document card in the dashboard.

## Tech stack

FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Supabase (Postgres +
Storage), and the `qrcode` library for on-demand PNG generation.

## Project structure

```
app/
├── api/routes/       # documents CRUD, /p/{uuid} redirect, /download/{uuid}
├── config/           # settings.py — every bit of config comes from env vars
├── database/         # SQLAlchemy engine/session/declarative base
├── middleware/        # global error handling, request logging
├── models/             # Document, Scan, Download (SQLAlchemy ORM)
├── schemas/             # Pydantic request/response shapes
├── services/              # storage, qr, document, analytics, geolocation
├── utils/                   # file validation, UA parsing, HTML error pages
└── main.py                    # FastAPI app assembly
alembic/                        # database migrations
```

Routes stay thin — all real logic lives in `services/`.

## Environment variables

Copy `.env.example` to `.env` and fill in real values. Nothing is
hardcoded anywhere in the code — the same Docker image works in any
environment purely by changing these:

| Variable | What it's for |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side only — never expose this to a browser |
| `SUPABASE_STORAGE_BUCKET` | Bucket PDFs are stored in (default `pdfs`) |
| `DATABASE_URL` | Postgres connection string |
| `PUBLIC_BASE_URL` | The domain this API is reachable at. Every QR code encodes `{PUBLIC_BASE_URL}/p/{uuid}` — get this wrong and every printed QR code points at the wrong place |
| `CORS_ORIGINS` | Comma-separated list of frontend origins allowed to call this API |
| `IP_GEOLOCATION_API_KEY` | Optional — powers country/city on scan analytics |
| `ADMIN_USERNAME` | Dashboard login username (default `admin`) |
| `ADMIN_PASSWORD` | Dashboard login password — **required**, pick something strong, this is the only thing gating document management |
| `JWT_SECRET_KEY` | **Required** — random secret signing the login token. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and never reuse it across environments |
| `JWT_EXPIRE_MINUTES` | Optional — how long a login stays valid (default 7 days) |
| `TRASH_RETENTION_DAYS` | Optional — how long deleted documents stay recoverable before permanent purge (default 7) |
| `APP_ENV` | `local` \| `staging` \| `production` |
| `PORT` | Optional — most hosting platforms inject this automatically |

Without `ADMIN_PASSWORD` and `JWT_SECRET_KEY` set, every login attempt
fails with a clear 500 ("Auth is not configured on the server") rather than
silently accepting anything — the app will not boot into an insecure state.

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env        # fill in real values
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI) are at `http://localhost:8000/docs` in non-production
environments.

## Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. **Database**: Project Settings → Database → copy the connection string
   into `DATABASE_URL`.
3. **API keys**: Project Settings → API → copy the Project URL into
   `SUPABASE_URL` and the `service_role` key into
   `SUPABASE_SERVICE_ROLE_KEY`.
4. **Storage**: Storage tab → create a bucket matching
   `SUPABASE_STORAGE_BUCKET` (default `pdfs`). It can be private — this
   backend never relies on public bucket URLs, it always mints short-lived
   signed URLs on demand.

## Deployment notes

- The Dockerfile binds to `$PORT` (falling back to `8000`), so it works
  unmodified on PaaS platforms that inject a dynamic port (Render, Railway,
  Coolify, etc.) as well as on a plain VPS.
- `alembic upgrade head` runs automatically on container start, so
  migrations are always applied on deploy.
- `PUBLIC_BASE_URL` and `CORS_ORIGINS` must be set to your real production
  domain(s) on whatever platform hosts this — the values in `.env.example`
  are placeholders/documentation only, they don't get read automatically by
  most hosting platforms.
- Redeploying after pulling auth/lifecycle changes still just works —
  `alembic upgrade head` runs automatically on every container start, so
  the `is_active`/`deleted_at`/richer-scan-fields migration applies itself.
  Just make sure `ADMIN_PASSWORD` and `JWT_SECRET_KEY` are set on the
  platform before the first request, or logins will fail with a 500.

## API reference

Everything under `/documents` requires `Authorization: Bearer <token>` from
`POST /auth/login`. `/p/{uuid}`, `/download/{uuid}`, `/auth/login`, and
`/health` do not.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | `{username, password}` → `{access_token}` |
| `GET` | `/auth/me` | Returns the current username — used by the frontend to validate a stored token |
| `POST` | `/documents` | Upload a PDF (multipart: `file`, optional `title`) |
| `GET` | `/documents` | List active + disabled documents (optional `?search=`) — excludes trash |
| `GET` | `/documents/trash` | List documents in the trash, with `purge_at` |
| `GET` | `/documents/{uuid}` | Fetch a single document |
| `PUT` | `/documents/{uuid}` | Replace the PDF, keeping the same UUID/QR |
| `DELETE` | `/documents/{uuid}` | Move to trash (recoverable for `TRASH_RETENTION_DAYS`) |
| `DELETE` | `/documents/trash/{uuid}` | Permanently delete a trashed document immediately |
| `POST` | `/documents/{uuid}/restore` | Restore a document out of the trash |
| `POST` | `/documents/{uuid}/disable` | Turn a QR code off without deleting anything |
| `POST` | `/documents/{uuid}/enable` | Turn a disabled QR code back on |
| `GET` | `/documents/{uuid}/scans/summary` | Country/device/browser breakdown + recent scans |
| `GET` | `/documents/{uuid}/qr` | Stream the QR code as a PNG (generated fresh every time) |
| `GET` | `/p/{uuid}` | The permanent QR entry point — logs a scan, redirects to the PDF (or shows an unavailable page if disabled, or 404 if deleted) |
| `GET` | `/download/{uuid}` | Logs a download, redirects to the PDF (same disabled/deleted handling) |
| `GET` | `/health` | Health check |

## A note on security

Treat `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `ADMIN_PASSWORD`, and
`JWT_SECRET_KEY` like passwords — the first two bypass Row Level Security
entirely, and the last two are the only thing standing between the public
internet and your document management actions. Never commit a real `.env`
file (it's git-ignored already; keep it that way), and if any of these are
ever accidentally exposed (public repo, shared screenshot, etc.), rotate
them immediately rather than trying to "undo" the exposure — Supabase keys
from the dashboard, `ADMIN_PASSWORD`/`JWT_SECRET_KEY` by just changing the
env var and redeploying (this instantly invalidates every existing login
token, since they're all signed with the old secret).
