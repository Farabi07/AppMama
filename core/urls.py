# urls.py in the 'ocr' app
from django.urls import path
from .views import ReceiptUploadView, TaskMamaAPI

urlpatterns = [
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
    path('api/chat/', TaskMamaAPI.as_view(), name='task_mama_chat'),
]
