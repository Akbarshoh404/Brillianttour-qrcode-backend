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

There's no login and no user accounts — it's an internal tool run by one
team, not a public product.

## How a document's life cycle works

1. **Upload** — a PDF comes in, gets a random UUID, is pushed to Supabase
   Storage, and a database row is created. A QR code encoding
   `{PUBLIC_BASE_URL}/p/{uuid}` is generated **on the fly** whenever
   requested — it is never saved as a file anywhere.
2. **Scan** — someone scans the printed QR code, which hits
   `GET /p/{uuid}`. The backend logs the scan (time, approximate location,
   browser, OS, device — all best-effort, all optional), bumps the
   document's scan counter, and redirects the phone straight to the current
   PDF via a freshly-signed, short-lived Supabase Storage URL.
3. **Replace** — if the brochure gets a price update, someone uploads the
   new PDF through `PUT /documents/{uuid}`. The UUID doesn't change, so
   every QR code already printed keeps working — it now just serves the new
   file. The old file is deleted from storage after the new one is
   confirmed uploaded, so a failed upload can never corrupt a live QR code.
4. **Delete** — removes the database row, its scan/download history, and
   the storage object. Anyone who scans that QR code afterward sees a
   (deliberately not-ugly) 404 page instead of a broken link.

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
| `APP_ENV` | `local` \| `staging` \| `production` |
| `PORT` | Optional — most hosting platforms inject this automatically |

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

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents` | Upload a PDF (multipart: `file`, optional `title`) |
| `GET` | `/documents` | List documents (optional `?search=`) |
| `GET` | `/documents/{uuid}` | Fetch a single document |
| `PUT` | `/documents/{uuid}` | Replace the PDF, keeping the same UUID/QR |
| `DELETE` | `/documents/{uuid}` | Delete a document, its files, and its analytics |
| `GET` | `/documents/{uuid}/qr` | Stream the QR code as a PNG (generated fresh every time) |
| `GET` | `/p/{uuid}` | The permanent QR entry point — logs a scan, redirects to the PDF |
| `GET` | `/download/{uuid}` | Logs a download, redirects to the PDF |
| `GET` | `/health` | Health check |

## A note on security

Treat `SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` like passwords — they
bypass Row Level Security entirely. Never commit a real `.env` file (it's
git-ignored already; keep it that way), and if either value is ever
accidentally exposed (public repo, shared screenshot, etc.), rotate it
immediately from the Supabase dashboard rather than trying to "undo" the
exposure.
