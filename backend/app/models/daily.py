from app.extensions import db
from app.models.types import BIGINT


class DailyRecord(db.Model):
    __tablename__ = "daily_records"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    completion_rate = db.Column(db.Integer, default=0)
    health_score = db.Column(db.Integer)
    summary = db.Column(db.Text)
    note = db.Column(db.Text)
    mood = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "record_date", name="uk_daily_user_date"),
    )


class VitalRecord(db.Model):
    __tablename__ = "vital_records"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    daily_record_id = db.Column(BIGINT, db.ForeignKey("daily_records.id"), nullable=False)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    systolic_pressure = db.Column(db.Integer)
    diastolic_pressure = db.Column(db.Integer)
    fasting_glucose = db.Column(db.Numeric(4, 1))
    postprandial_glucose = db.Column(db.Numeric(4, 1))
    weight_kg = db.Column(db.Numeric(5, 2))
    measured_at = db.Column(db.DateTime)
    remark = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("daily_record_id", name="uk_vital_daily_record"),
    )


class MealRecord(db.Model):
    __tablename__ = "meal_records"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    daily_record_id = db.Column(BIGINT, db.ForeignKey("daily_records.id"), nullable=False)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    meal_type = db.Column(db.Enum("breakfast", "lunch", "dinner", "extra"), nullable=False)
    meal_name = db.Column(db.String(30), nullable=False, default="加餐", server_default="加餐")
    food_text = db.Column(db.Text, nullable=False)
    calories = db.Column(db.Numeric(8, 2))
    sugar_g = db.Column(db.Numeric(8, 2))
    fat_g = db.Column(db.Numeric(8, 2))
    salt_g = db.Column(db.Numeric(8, 2))
    advice = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class FoodItem(db.Model):
    __tablename__ = "food_items"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(30), nullable=False, default="100g", server_default="100g")
    calories_per_100g = db.Column(db.Numeric(8, 2))
    sugar_per_100g = db.Column(db.Numeric(8, 2))
    fat_per_100g = db.Column(db.Numeric(8, 2))
    salt_per_100g = db.Column(db.Numeric(8, 2))
    suitable_tags = db.Column(db.String(255))
    avoid_tags = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class HealthAlert(db.Model):
    __tablename__ = "health_alerts"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    alert_type = db.Column(db.String(30), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    source_type = db.Column(db.Enum("vital", "diet", "report", "prediction"), nullable=False)
    source_id = db.Column(BIGINT)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.Enum("low", "medium", "high"), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False)


class DailyTaskTemplate(db.Model):
    __tablename__ = "daily_task_templates"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    version_no = db.Column(db.Integer, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "version_no", name="uk_task_template_user_version"),
    )


class DailyTaskTemplateItem(db.Model):
    __tablename__ = "daily_task_template_items"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    template_id = db.Column(BIGINT, db.ForeignKey("daily_task_templates.id"), nullable=False)
    task_name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False)


class DailyTask(db.Model):
    __tablename__ = "daily_tasks"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    daily_record_id = db.Column(BIGINT, db.ForeignKey("daily_records.id"), nullable=False)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    template_id = db.Column(BIGINT, db.ForeignKey("daily_task_templates.id"), nullable=False)
    template_item_id = db.Column(BIGINT, db.ForeignKey("daily_task_template_items.id"), nullable=False)
    task_name_snapshot = db.Column(db.String(100), nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("daily_record_id", "template_item_id", name="uk_daily_task_item"),
    )
