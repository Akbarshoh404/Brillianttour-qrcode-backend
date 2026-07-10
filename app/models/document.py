import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
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
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    total_scans: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_downloads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_scan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_download: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    downloads: Mapped[list["Download"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
