
from django.urls import path
from notification.views import contacts_views as views


urlpatterns = [
	path('api/v1/contacts/all/', views.getAllContact),

	path('api/v1/contacts/without_pagination/all/', views.getAllContactWithoutPagination),

	path('api/v1/contacts/<int:pk>', views.getAContact),

	path('api/v1/contacts/search/', views.searchContact),

	path('api/v1/contacts/create/', views.createContact),

	path('api/v1/contacts/update/<int:pk>', views.updateContact),

	path('api/v1/contacts/delete/<int:pk>', views.deleteContact),



]