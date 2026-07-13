"""documents: add notes field

Revision ID: 0004_document_notes
Revises: 0003_domains_and_folders
Create Date: 2025-04-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_document_notes"
down_revision: Union[str, None] = "0003_domains_and_folders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "notes")
