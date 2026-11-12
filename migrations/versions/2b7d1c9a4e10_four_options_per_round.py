"""four options per round (A-D)

Revision ID: 2b7d1c9a4e10
Revises: 1260c70462bc
"""
from alembic import op

revision = "2b7d1c9a4e10"
down_revision = "1260c70462bc"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vote", recreate="always") as batch:
        batch.drop_constraint("ck_vote_option", type_="check")
        batch.create_check_constraint("ck_vote_option", "option IN ('A','B','C','D')")
    with op.batch_alter_table("round_option", recreate="always") as batch:
        batch.create_check_constraint("ck_round_option_key", "option IN ('A','B','C','D')")


def downgrade():
    with op.batch_alter_table("round_option", recreate="always") as batch:
        batch.drop_constraint("ck_round_option_key", type_="check")
    with op.batch_alter_table("vote", recreate="always") as batch:
        batch.drop_constraint("ck_vote_option", type_="check")
        batch.create_check_constraint("ck_vote_option", "option IN ('A','B','C')")
