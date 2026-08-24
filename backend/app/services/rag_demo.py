from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.models import (
    Announcement,
    DailyRecord,
    FoodItem,
    HealthAlert,
    HealthProfile,
    ReportIndicator,
    VitalRecord,
)


@dataclass(frozen=True)
class RagChunk:
    position: str
    source: str
    source_id: str
    content: str


FALLBACK_CHUNKS = [
    RagChunk(
        position="fallback",
        source="health_knowledge",
        source_id="diet_001",
        content="空腹血糖偏高人群晚餐应减少精制主食，优先选择全谷物、豆制品和深色蔬菜。",
    ),
    RagChunk(
        position="fallback",
        source="health_knowledge",
        source_id="pressure_001",
        content="血压偏高时应连续记录早晚血压，控制盐分摄入，并关注睡眠和情绪变化。",
    ),
    RagChunk(
        position="fallback",
        source="health_knowledge",
        source_id="report_001",
        content="体检报告异常指标需要结合参考范围、既往病史和复查结果综合判断。",
    ),
]


def _text(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(float(value)).rstrip("0").rstrip(".")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _shorten(value, limit=220):
    text = " ".join(_text(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def _append(chunks, source, source_id, content):
    text = _shorten(content)
    if text:
        chunks.append(RagChunk("", source, _text(source_id), text))


def _collect_user_chunks(user_id):
    chunks = []

    profile = HealthProfile.query.filter_by(user_id=user_id).order_by(HealthProfile.id.asc()).first()
    if profile:
        chronic_types = "、".join(profile.chronic_types or []) or "未填写"
        _append(
            chunks,
            "health_profiles",
            profile.id,
            (
                f"健康档案：性别{profile.gender or '未填写'}，年龄{profile.age or '未填写'}，"
                f"BMI {_text(profile.bmi) or '未填写'}，慢病类型{chronic_types}，"
                f"既往病史{profile.medical_history or '未填写'}，用药{profile.medication or '未填写'}。"
            ),
        )

    for row in DailyRecord.query.filter_by(user_id=user_id).order_by(DailyRecord.record_date.asc(), DailyRecord.id.asc()).all():
        _append(
            chunks,
            "daily_records",
            row.id,
            f"每日记录：{_text(row.record_date)}，完成度{row.completion_rate or 0}%，健康评分{row.health_score or '未填写'}，小结{row.summary or '暂无'}。",
        )

    for row in VitalRecord.query.filter_by(user_id=user_id).order_by(VitalRecord.measured_at.asc(), VitalRecord.id.asc()).all():
        _append(
            chunks,
            "vital_records",
            row.id,
            (
                f"血压血糖：收缩压{row.systolic_pressure or '未填写'}mmHg，"
                f"舒张压{row.diastolic_pressure or '未填写'}mmHg，"
                f"空腹血糖{_text(row.fasting_glucose) or '未填写'}mmol/L，"
                f"餐后血糖{_text(row.postprandial_glucose) or '未填写'}mmol/L。"
            ),
        )

    for row in ReportIndicator.query.filter_by(user_id=user_id).order_by(ReportIndicator.id.asc()).all():
        _append(
            chunks,
            "report_indicators",
            row.id,
            (
                f"体检指标：{row.indicator_name}={row.value}{row.unit or ''}，"
                f"参考范围{row.reference_range or '未填写'}，状态{row.result_status}，风险{row.risk_level}。"
            ),
        )

    for row in HealthAlert.query.filter_by(user_id=user_id).order_by(HealthAlert.created_at.asc(), HealthAlert.id.asc()).all():
        _append(
            chunks,
            "health_alerts",
            row.id,
            f"异常提醒：{row.title}，风险{row.risk_level}，说明{row.description or row.content}。",
        )

    return chunks


def _collect_global_chunks():
    chunks = []
    for row in FoodItem.query.order_by(FoodItem.id.asc()).all():
        _append(
            chunks,
            "food_items",
            row.id,
            (
                f"食物库：{row.name}，分类{row.category or '未分类'}，"
                f"每{row.unit or '100g'}约{_text(row.calories_per_100g)}kcal，"
                f"糖{_text(row.sugar_per_100g)}g，脂肪{_text(row.fat_per_100g)}g，盐{_text(row.salt_per_100g)}g。"
            ),
        )

    for row in Announcement.query.order_by(Announcement.created_at.asc(), Announcement.id.asc()).all():
        _append(
            chunks,
            "announcements",
            row.id,
            f"系统公告：{row.title}。{row.content}",
        )

    return chunks


class RagDemoService:
    """Temporary no-LLM RAG facade for demo testing.

    It returns the first, last and one deterministic-random chunk from the
    database so the AI page can prove that retrieval and message persistence
    are wired before a real model provider is configured.
    """

    @staticmethod
    def retrieve(user_id, question=""):
        chunks = _collect_user_chunks(user_id) + _collect_global_chunks()
        if not chunks:
            chunks = FALLBACK_CHUNKS

        random_pool = chunks[1:-1] if len(chunks) > 2 else chunks
        seed = f"{user_id}:{question}:{len(chunks)}"
        random_chunk = random.Random(seed).choice(random_pool)

        selected = [
            RagChunk("first", chunks[0].source, chunks[0].source_id, chunks[0].content),
            RagChunk("last", chunks[-1].source, chunks[-1].source_id, chunks[-1].content),
            RagChunk("random", random_chunk.source, random_chunk.source_id, random_chunk.content),
        ]
        return selected

    @classmethod
    def answer(cls, user_id, question=""):
        selected = cls.retrieve(user_id, question)
        content = "\n".join(
            f"{index}. {item.position} | {item.source}#{item.source_id} | {item.content}"
            for index, item in enumerate(selected, start=1)
        )
        return {
            "content": content,
            "collection": "database_demo_rag",
            "mode": "no_llm_first_last_random",
            "items": [
                {
                    "position": item.position,
                    "source": item.source,
                    "source_id": item.source_id,
                    "content": item.content,
                }
                for item in selected
            ],
        }
