
from django.urls import path
from task.views import client_views as views


urlpatterns = [
	path('api/v1/client/all/', views.getAllClient),

	path('api/v1/client/without_pagination/all/', views.getAllClientWithoutPagination),

	path('api/v1/client/<int:pk>', views.getAClient),

	path('api/v1/client/search/', views.searchClient),

	path('api/v1/client/create/', views.createClient),

	path('api/v1/client/update/<int:pk>', views.updateClient),

	path('api/v1/client/delete/<int:pk>', views.deleteClient),



]