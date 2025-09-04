
from django.urls import path
from task.views import qrcode_views as views


urlpatterns = [
	# path('api/v1/client/all/', views.getAllQRTaskData),

	# path('api/v1/client/without_pagination/all/', views.getAllQRTaskDataWithoutPagination),

	# path('api/v1/client/<int:pk>', views.getAQRTaskData),

	# path('api/v1/client/search/', views.searchQRTaskData),

	path('api/v1/qrcode_image_generate/create/', views.createQRTaskData),

	# path('api/v1/client/update/<int:pk>', views.updateQRTaskData),

	# path('api/v1/client/delete/<int:pk>', views.deleteQRTaskData),



]