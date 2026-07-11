import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, domains, download, folders, redirect
from app.config import settings
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware

logging.basicConfig(
    level=logging.INFO if not settings.is_production else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Internal tool for uploading PDFs and generating permanent QR codes.",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(documents.router)
app.include_router(domains.router)
app.include_router(folders.router)
app.include_router(redirect.router)
app.include_router(download.router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "environment": settings.APP_ENV}
