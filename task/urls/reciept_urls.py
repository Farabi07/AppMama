
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

	path('api/v1/reciept/list/', views.listReceipts, name='list-receipts'),

	path('api/v1/reciept/pantry_items/', views.pantry_items, name='pantry-items'),

	path('api/v1/reciept/pantry_update/', views.pantry_update, name='pantry_update'),

	path('api/v1/reciept/pantry_items_delete/', views.delete_pantry_item, name='pantry_delete'),

	path('api/v1/reciept/monthly_report/', views.monthly_report, name='receipt-dashboard'),
    
	path('api/v1/reciept/monthly_statistics/', views.monthly_statistics, name='monthly-statistics'),

	path('api/v1/reciept/add-item/<int:receipt_id>', views.addItemtoReceipt, name='add-item-to-receipt'),

	# path('receipt/<int:receipt_id>/<str:type_str>/<int:index>/update/', views.updateItemOrService, name='update-item-service'),
    # path('receipt/<int:receipt_id>/<str:type_str>/<int:index>/delete/', views.deleteItemOrService, name='delete-item-service'),





]