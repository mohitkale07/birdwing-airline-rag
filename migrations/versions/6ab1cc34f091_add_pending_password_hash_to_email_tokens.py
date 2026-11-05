"""store pending email credentials until verification

Revision ID: 6ab1cc34f091
Revises: 2d33c9e1e19b
Create Date: 2026-11-05 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6ab1cc34f091"
down_revision: Union[str, Sequence[str], None] = "2d33c9e1e19b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_verification_tokens",
        sa.Column("pending_password_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_verification_tokens", "pending_password_hash")
