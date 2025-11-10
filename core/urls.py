# urls.py in the 'core' app - Task Mama AI Integration - SEPARATED VIEWS
from django.urls import path

# Import self-contained feature view modules
from .recipe_views import (
    # step endpoints removed in favor of single combined
    api_recipe_combined,
)
from .task_planning_views import (
    # step endpoints removed in favor of single combined
    api_task_plan_combined,
)
from .task_progress_views import (
    api_task_progress,
    api_task_query,
)
from .peptalk_views import (
    api_peptalk,
)
from .chat_views import (
    api_chat,
    api_detect_intent,
    handle_task_mama_request,
)

# Receipt endpoints still rely on legacy class/functions in views.py (not yet refactored)
from .views import ReceiptUploadView, receipt_preview, save_receipt_by_type

urlpatterns = [
    # ==================== NEW PER-FEATURE ENDPOINTS ====================
    # 🍳 RECIPE VIEW (single two-step-in-one)
    path('api/recipe/', api_recipe_combined, name='api_recipe_combined'),

    # 📋 TASK PLANNING VIEW (single two-step-in-one)
    path('api/task-planning/', api_task_plan_combined, name='api_task_plan_combined'),

    # 📊 TASK PROGRESS & QUERY VIEWS
    path('api/task-progress/', api_task_progress, name='api_task_progress'),
    path('api/task-query/', api_task_query, name='api_task_query'),

    # 🎭 PEPTALK VIEW
    path('api/peptalk/', api_peptalk, name='api_peptalk'),

    # 💬 GENERAL CHAT + INTENT
    path('api/chat/', api_chat, name='api_chat'),
    path('api/intent-detection/', api_detect_intent, name='api_detect_intent'),

    # ==================== LEGACY ENDPOINTS (Backward Compatibility) ====================
    # Map legacy chat routes to the single combined endpoints
    path('api/chat/recipe/', api_recipe_combined, name='legacy_recipe_request'),
    path('api/chat/plan/', api_task_plan_combined, name='legacy_task_plan'),
    path('api/chat/progress/', api_task_progress, name='legacy_task_progress'),
    path('api/chat/peptalk/', api_peptalk, name='legacy_peptalk'),
    path('api/detect-intent/', api_detect_intent, name='legacy_detect_intent'),

    # Combined legacy multi-intent conversation handler (simplified)
    path('api/chat-boot/', handle_task_mama_request, name='legacy_combined_endpoint'),

    # ==================== RECEIPT PROCESSING (still legacy implementation) ====================
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path('receipt/preview/', receipt_preview, name='receipt_preview'),
    path('receipt/save/<str:receipt_type>/', save_receipt_by_type, name='save_receipt_by_type'),
]