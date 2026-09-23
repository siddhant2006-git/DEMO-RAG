"""add users for authentication

Revision ID: 8f2e7c1a4b9d
Revises: 06b186e54f3b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8f2e7c1a4b9d"
down_revision: Union[str, Sequence[str], None] = "06b186e54f3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_users_email", "users", ["email"], unique=False, if_not_exists=True
    )
    op.create_index(
        "ix_users_username", "users", ["username"], unique=False, if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
