from flask import Blueprint
from flask_restful import Api

from .admin.resources import (
    AdminAnnouncementResource,
    AdminAnnouncementsBatchPublishResource,
    AdminAnnouncementsResource,
    AdminDashboardResource,
    AdminFoodResource,
    AdminFoodsBatchDeleteResource,
    AdminFoodsResource,
    AdminReportReviewResource,
    AdminReportsBatchReviewResource,
    AdminReportsResource,
    AdminUserResource,
    AdminUsersResource,
)
from .ai.resources import (
    AiContextTodayResource,
    AiConversationMessagesResource,
    AiConversationResource,
    AiConversationsResource,
    AiQuickQuestionsResource,
)
from .auth.resources import AdminLoginResource, LogoutResource, WechatLoginResource
from .daily.resources import (
    AlertReadResource,
    AlertsResource,
    DailyCalendarResource,
    DailyMealsResource,
    DailyRecordResource,
    DailyRecordsResource,
    DailyTaskResource,
    DailyTaskTemplateCurrentResource,
    DailyTasksGenerateResource,
    DailyTasksResource,
    DailyTodayResource,
    DailyVitalsResource,
    MealResource,
    VitalsPredictionResource,
    VitalsTrendResource,
)
from .health.resources import HealthResource
from .mine.resources import (
    MeAvatarFileResource,
    MeAvatarResource,
    MeConsentsResource,
    MeConsentWithdrawalResource,
    MeDataExportResource,
    MeHealthProfileResource,
    MeProfileResource,
    MeSettingsResource,
)
from .reports.resources import (
    ReportDetailResource,
    ReportHistoryResource,
    ReportIndicatorsResource,
    ReportProgressResource,
    ReportRecognizeResource,
    ReportUploadResource,
)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api = Api(api_bp)

api.add_resource(HealthResource, "/health")

api.add_resource(WechatLoginResource, "/auth/wechat-login")
api.add_resource(AdminLoginResource, "/auth/admin-login")
api.add_resource(LogoutResource, "/auth/logout")

api.add_resource(DailyTodayResource, "/daily-records/today")
api.add_resource(DailyCalendarResource, "/daily-records/calendar")
api.add_resource(DailyRecordsResource, "/daily-records")
api.add_resource(DailyRecordResource, "/daily-records/<int:record_id>")
api.add_resource(DailyVitalsResource, "/daily-records/<int:record_id>/vitals")
api.add_resource(DailyTasksResource, "/daily-records/<int:record_id>/tasks")
api.add_resource(DailyTasksGenerateResource, "/daily-records/<int:record_id>/tasks/generate")
api.add_resource(DailyTaskResource, "/daily-tasks/<int:task_id>")
api.add_resource(DailyTaskTemplateCurrentResource, "/daily-task-templates/current")
api.add_resource(DailyMealsResource, "/daily-records/<int:record_id>/meals")
api.add_resource(MealResource, "/meals/<int:meal_id>")
api.add_resource(VitalsTrendResource, "/trends/vitals")
api.add_resource(VitalsPredictionResource, "/predictions/vitals")
api.add_resource(AlertsResource, "/alerts")
api.add_resource(AlertReadResource, "/alerts/<int:alert_id>/read")

api.add_resource(ReportUploadResource, "/reports/upload")
api.add_resource(ReportRecognizeResource, "/reports/<int:report_id>/recognize")
api.add_resource(ReportProgressResource, "/reports/<int:report_id>/progress")
api.add_resource(ReportHistoryResource, "/reports/history")
api.add_resource(ReportIndicatorsResource, "/reports/<int:report_id>/indicators")
api.add_resource(ReportDetailResource, "/reports/<int:report_id>")

api.add_resource(AiQuickQuestionsResource, "/ai/quick-questions")
api.add_resource(AiContextTodayResource, "/ai/context/today")
api.add_resource(AiConversationsResource, "/ai/conversations")
api.add_resource(AiConversationMessagesResource, "/ai/conversations/<int:conversation_id>/messages")
api.add_resource(AiConversationResource, "/ai/conversations/<int:conversation_id>")

api.add_resource(MeProfileResource, "/me/profile")
api.add_resource(MeAvatarResource, "/me/avatar")
api.add_resource(MeAvatarFileResource, "/me/avatar/files/<string:filename>")
api.add_resource(MeHealthProfileResource, "/me/health-profile")
api.add_resource(MeSettingsResource, "/me/settings")
api.add_resource(MeConsentsResource, "/me/consents")
api.add_resource(MeConsentWithdrawalResource, "/me/consents/withdraw")
api.add_resource(MeDataExportResource, "/me/data-export")

api.add_resource(AdminDashboardResource, "/admin/dashboard")
api.add_resource(AdminUsersResource, "/admin/users")
api.add_resource(AdminUserResource, "/admin/users/<int:user_id>")
api.add_resource(AdminReportsResource, "/admin/reports")
api.add_resource(AdminReportReviewResource, "/admin/reports/<int:report_id>/review")
api.add_resource(AdminReportsBatchReviewResource, "/admin/reports/batch-review")
api.add_resource(AdminFoodsResource, "/admin/foods")
api.add_resource(AdminFoodResource, "/admin/foods/<int:food_id>")
api.add_resource(AdminFoodsBatchDeleteResource, "/admin/foods/batch-delete")
api.add_resource(AdminAnnouncementsResource, "/admin/announcements")
api.add_resource(AdminAnnouncementResource, "/admin/announcements/<int:announcement_id>")
api.add_resource(AdminAnnouncementsBatchPublishResource, "/admin/announcements/batch-publish")
