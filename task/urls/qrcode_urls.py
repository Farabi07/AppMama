
from django.urls import path
from task.views import qrcode_views as views


urlpatterns = [
	# Simplified, user-friendly URLs
	path('create/', views.createQRTaskData, name='create_qr_task'),
    path('view/<int:pk>/', views.qr_task_view, name='qr_task_view'),
    path('update/<int:pk>/', views.update_qr_task_metadata, name='update_qr_task_metadata'),
    
    # Legacy URL support (backwards compatibility)
	path('api/v1/qrcode_image_generate/create/', views.createQRTaskData),
    path('api/v1/qrcode/update/<int:pk>/', views.update_qr_task_metadata),

	# path('api/v1/client/delete/<int:pk>', views.deleteQRTaskData),



]