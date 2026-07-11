from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Domain(Base):
    """A public-facing domain a document's QR code can be deployed under.

    Documents with no domain_id fall back to the global PUBLIC_BASE_URL env
    var — so the "default" domain is never hardcoded here, it's whatever
    the backend is configured with. This table only holds *additional*
    domains an owner has added (e.g. a second client's branded domain).
    """

    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
