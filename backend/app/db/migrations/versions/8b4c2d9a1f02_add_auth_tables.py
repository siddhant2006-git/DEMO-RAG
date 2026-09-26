"""add authentication tables"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app import models  # noqa: F401 - registers auth models
from app.models.auth import PasswordResetToken, RefreshSession, User, VerificationToken

revision: str = "8b4c2d9a1f02"
down_revision: Union[str, Sequence[str], None] = "624379438e5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    for model in (User, RefreshSession, VerificationToken, PasswordResetToken):
        model.__table__.create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    additions = {
        "company_name": sa.String(512),
        "vendor_id": sa.String(128),
        "authorized_person_name": sa.String(256),
        "mobile_number": sa.String(32),
        "gstin": sa.String(15),
        "pan": sa.String(10),
        "udyam_number": sa.String(32),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("users", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    for model in (PasswordResetToken, VerificationToken, RefreshSession, User):
        model.__table__.drop(bind=bind, checkfirst=True)
