# urls.py in the 'ocr' app
from django.urls import path
from .views import *

urlpatterns = [
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path("receipt/preview/",receipt_preview, name="receipt_preview"),## final preview of receipt
    path("receipt/save/", save_final_receipt, name="save_final_receipt"),## save final receipt to db
    path('api/chat-boot/', handle_task_mama_request, name='handle_task_mama_request'),
]
