# urls.py in the 'ocr' app
from django.urls import path
from .views import ReceiptUploadView, handle_task_mama_request

urlpatterns = [
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path('api/chat-boot/', handle_task_mama_request, name='handle_task_mama_request'),
]
