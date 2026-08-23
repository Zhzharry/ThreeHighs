"""add user consent records

Revision ID: a47c12e6d901
Revises: 9c2f7e8a1b34
Create Date: 2026-08-23 15:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "a47c12e6d901"
down_revision = "9c2f7e8a1b34"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "user_consents",
        sa.Column("id", BIGINT, autoincrement=True, nullable=False),
        sa.Column("user_id", BIGINT, nullable=False),
        sa.Column("privacy_policy_version", sa.String(length=20), nullable=False),
        sa.Column("user_agreement_version", sa.String(length=20), nullable=False),
        sa.Column("health_data_consent_version", sa.String(length=20), nullable=False),
        sa.Column("health_data_consent", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_consents_user"),
    )


def downgrade():
    op.drop_table("user_consents")
