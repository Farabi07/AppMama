
from django.urls import path
from task.views import reciept_views as views


urlpatterns = [
	path('api/v1/reciept/all/', views.getAllReceipt),

	path('api/v1/reciept/without_pagination/all/', views.getAllReceiptWithoutPagination),

	path('api/v1/reciept/<int:pk>', views.getAReceipt),

	path('api/v1/reciept/search/', views.searchReceipt),

	path('api/v1/reciept/create/', views.createReceipt),

	path('api/v1/reciept/update/<int:pk>', views.updateReceipt),

	path('api/v1/reciept/delete/<int:pk>', views.deleteReceipt),
    
	path('receipt/<int:receipt_id>/add-item/', views.addItemtoReceipt, name='add-item-to-receipt'),

	path('receipt/<int:receipt_id>/<str:type_str>/<int:index>/update/', views.updateItemOrService, name='update-item-service'),
    path('receipt/<int:receipt_id>/<str:type_str>/<int:index>/delete/', views.deleteItemOrService, name='delete-item-service'),





]