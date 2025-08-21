# urls.py in the 'ocr' app
from django.urls import path
from .views import ReceiptUploadView

urlpatterns = [
    path('upload_receipt/', ReceiptUploadView.as_view(), name='upload_receipt'),
]
