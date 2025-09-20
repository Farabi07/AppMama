# urls.py in the 'core' app - Task Mama AI Integration
from django.urls import path
from .views import *

urlpatterns = [
   
    path('api/chat-boot/', handle_task_mama_request, name='handle_task_mama_request'),  # Legacy support
    
    # Receipt Processing (separate functionality)
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path("receipt/preview/", receipt_preview, name="receipt_preview"),
    path('receipt/save/<str:receipt_type>/', save_receipt_by_type, name='save_receipt_by_type'),
]