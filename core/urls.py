# urls.py in the 'ocr' app
from django.urls import path
from .views import *

urlpatterns = [
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path("receipt/preview/",receipt_preview, name="receipt_preview"),
    path("receipt/save/", save_final_receipt, name="save_final_receipt"),
    path('api/chat-boot/', handle_task_mama_request, name='handle_task_mama_request'),
]
