"""Database repositories for domain-owned persistence."""

from .reference_repository import AnnouncementRepository, FoodRepository, bootstrap_reference_data
from .user_repository import UserRepository, bootstrap_user_data
from .daily_repository import DailyRepository, bootstrap_daily_data
from .task_alert_repository import AlertRepository, TaskRepository, bootstrap_task_alert_data
from .report_repository import ReportRepository, bootstrap_report_data
from .ai_repository import AiRepository, bootstrap_ai_data

__all__ = [
    "AnnouncementRepository",
    "FoodRepository",
    "DailyRepository",
    "TaskRepository",
    "AlertRepository",
    "ReportRepository",
    "AiRepository",
    "UserRepository",
    "bootstrap_reference_data",
    "bootstrap_daily_data",
    "bootstrap_task_alert_data",
    "bootstrap_report_data",
    "bootstrap_ai_data",
    "bootstrap_user_data",
]
