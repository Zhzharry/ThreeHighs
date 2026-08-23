"""repair corrupted legacy demo profile encoding

Revision ID: b58e1a4c7d22
Revises: a47c12e6d901
Create Date: 2026-08-23 15:48:00
"""
from alembic import op
import sqlalchemy as sa


revision = "b58e1a4c7d22"
down_revision = "a47c12e6d901"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    corrupted = "(username LIKE '%?%' OR username LIKE '%�%')"
    connection.execute(sa.text(
        f"UPDATE users SET username = :username "
        f"WHERE openid = 'demo-openid' AND {corrupted}"
    ), {"username": "李明"})

    profile_corrupted = "(gender LIKE '%?%' OR gender LIKE '%�%')"
    connection.execute(sa.text(
        "UPDATE health_profiles SET gender = :gender, disease_type = :disease_type, "
        "medical_history = :medical_history, medication = :medication "
        "WHERE user_id IN (SELECT id FROM users WHERE openid = 'demo-openid') "
        f"AND {profile_corrupted}"
    ), {
        "gender": "男",
        "disease_type": "高血压 + 高血糖",
        "medical_history": "轻度脂肪肝",
        "medication": "二甲双胍、氨氯地平",
    })


def downgrade():
    # 数据修复不可逆；降级结构版本时保留已经恢复的可读文本。
    pass
