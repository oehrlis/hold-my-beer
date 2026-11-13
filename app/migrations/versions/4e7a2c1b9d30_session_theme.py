"""session theme (layout chosen by the admin, NULL = APP_THEME)

Revision ID: 4e7a2c1b9d30
Revises: 2b7d1c9a4e10
"""
import sqlalchemy as sa
from alembic import op

revision = "4e7a2c1b9d30"
down_revision = "2b7d1c9a4e10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("session_state") as batch:
        batch.add_column(sa.Column("theme", sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table("session_state") as batch:
        batch.drop_column("theme")
