import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Document(Base):
    """A single uploaded PDF and its permanent QR identity.

    `uuid` is the public, permanent identifier encoded into the QR code.
    It never changes, even when the underlying PDF is replaced.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, nullable=False, default=uuid_lib.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Which Supabase Storage bucket storage_path lives in. Null means the
    # globally configured SUPABASE_STORAGE_BUCKET (the default, unfoldered
    # bucket) — same fallback pattern as domain_id below.
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Which public domain this document's QR code is built against. Null
    # falls back to the global PUBLIC_BASE_URL env var — deleting a domain
    # just reverts its documents to that default rather than orphaning them.
    domain_id: Mapped[int | None] = mapped_column(
        ForeignKey("domains.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Which folder this document is filed under, for organization. Null
    # means "unfiled" (lives in the default storage_bucket).
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    total_scans: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_downloads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_scan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_download: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Lets an owner turn a QR code off without destroying it (e.g. a client
    # stops paying). Disabled documents keep their history and can be
    # re-enabled at any time. Distinct from deleted_at (trash).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Soft-delete timestamp. Set on DELETE, cleared on restore. A document
    # with deleted_at set is in the trash and is purged permanently ~7 days
    # later (see document_service.purge_expired_trash).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    downloads: Mapped[list["Download"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )

    domain: Mapped["Domain | None"] = relationship()
    folder: Mapped["Folder | None"] = relationship()
