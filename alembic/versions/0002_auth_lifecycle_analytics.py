"""documents: is_active/deleted_at; scans: richer passive analytics fields

Revision ID: 0002_auth_lifecycle_analytics
Revises: 0001_initial
Create Date: 2025-02-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_lifecycle_analytics"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])

    op.add_column("scans", sa.Column("region", sa.String(length=100), nullable=True))
    op.add_column("scans", sa.Column("isp", sa.String(length=255), nullable=True))
    op.add_column("scans", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("scans", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("scans", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column("scans", sa.Column("referrer", sa.String(length=512), nullable=True))
    op.add_column("scans", sa.Column("language", sa.String(length=35), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "language")
    op.drop_column("scans", "referrer")
    op.drop_column("scans", "timezone")
    op.drop_column("scans", "longitude")
    op.drop_column("scans", "latitude")
    op.drop_column("scans", "isp")
    op.drop_column("scans", "region")

    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "is_active")
