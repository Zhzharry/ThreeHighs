"""add wechat identity and login audit

Revision ID: 9c2f7e8a1b34
Revises: 645d5533beda
Create Date: 2026-08-23 10:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "9c2f7e8a1b34"
down_revision = "645d5533beda"
branch_labels = None
depends_on = None


BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unionid", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("token_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("login_count", sa.Integer(), nullable=True))

    op.execute(sa.text("UPDATE users SET token_version = 1 WHERE token_version IS NULL"))
    op.execute(sa.text("UPDATE users SET login_count = 0 WHERE login_count IS NULL"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("token_version", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("login_count", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint("uq_users_unionid", ["unionid"])

    op.create_table(
        "user_login_events",
        sa.Column("id", BIGINT, autoincrement=True, nullable=False),
        sa.Column("user_id", BIGINT, nullable=True),
        sa.Column("login_method", sa.String(length=20), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_code", sa.String(length=32), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("client_ip_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_login_events_user_created",
        "user_login_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_login_events_request_id",
        "user_login_events",
        ["request_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_user_login_events_request_id", table_name="user_login_events")
    op.drop_index("ix_user_login_events_user_created", table_name="user_login_events")
    op.drop_table("user_login_events")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_users_unionid", type_="unique")
        batch_op.drop_column("login_count")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("token_version")
        batch_op.drop_column("unionid")
