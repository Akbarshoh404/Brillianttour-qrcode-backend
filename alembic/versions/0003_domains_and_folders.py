"""domains + folders (multi-domain QR routing, per-folder storage buckets)

Revision ID: 0003_domains_and_folders
Revises: 0002_auth_lifecycle_analytics
Create Date: 2025-03-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_domains_and_folders"
down_revision: Union[str, None] = "0002_auth_lifecycle_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domains",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_domains_base_url", "domains", ["base_url"], unique=True)

    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_bucket", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_folders_storage_bucket", "folders", ["storage_bucket"], unique=True)

    op.add_column("documents", sa.Column("storage_bucket", sa.String(length=255), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "domain_id",
            sa.Integer(),
            sa.ForeignKey("domains.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "folder_id",
            sa.Integer(),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_documents_domain_id", "documents", ["domain_id"])
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_folder_id", table_name="documents")
    op.drop_index("ix_documents_domain_id", table_name="documents")
    op.drop_column("documents", "folder_id")
    op.drop_column("documents", "domain_id")
    op.drop_column("documents", "storage_bucket")

    op.drop_index("ix_folders_storage_bucket", table_name="folders")
    op.drop_table("folders")

    op.drop_index("ix_domains_base_url", table_name="domains")
    op.drop_table("domains")
