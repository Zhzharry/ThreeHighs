"""add consent withdrawal timestamp

Revision ID: c69d2f4a8e10
Revises: b58e1a4c7d22
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "c69d2f4a8e10"
down_revision = "b58e1a4c7d22"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_consents") as batch_op:
        batch_op.add_column(sa.Column("withdrawn_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("user_consents") as batch_op:
        batch_op.drop_column("withdrawn_at")
